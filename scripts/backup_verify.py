"""Encrypted PostgreSQL snapshot; restoration is restricted to a new disposable container."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.parse import parse_qs, unquote, urlsplit
from zipfile import ZipFile

from cryptography.fernet import Fernet
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'datapulse.backup-verification=true'


def database_env(url, development=False):
    parsed = urlsplit(url)
    mode = parse_qs(parsed.query).get('sslmode', [''])[0]
    local = parsed.hostname in ['localhost', '127.0.0.1', '::1']
    if parsed.scheme not in ['postgres', 'postgresql'] or not parsed.hostname or not parsed.path.strip('/'):
        raise ValueError('Se requiere una conexión PostgreSQL.')
    if mode not in ['require', 'verify-ca', 'verify-full']:
        if not development or not local:
            raise ValueError('La fuente remota debe usar TLS; la excepción de desarrollo solo admite loopback.')
        mode = 'disable'
    return {'PGHOST': parsed.hostname, 'PGPORT': str(parsed.port or 5432), 'PGCONNECT_TIMEOUT': '15',
        'PGDATABASE': unquote(parsed.path.lstrip('/')), 'PGUSER': unquote(parsed.username or ''),
        'PGPASSWORD': unquote(parsed.password or ''), 'PGSSLMODE': mode}


def seal_bundle(dump, manifest, key):
    archive = BytesIO()
    with ZipFile(archive, 'w') as bundle:
        bundle.writestr('database.dump', dump)
        bundle.writestr('manifest.json', json.dumps({'format': 1, **manifest}))
    return Fernet(key).encrypt(archive.getvalue())


def open_bundle(encrypted, key):
    with ZipFile(BytesIO(Fernet(key).decrypt(encrypted))) as bundle:
        if set(bundle.namelist()) != {'database.dump', 'manifest.json'}:
            raise ValueError('Contenido de respaldo no reconocido.')
        manifest = json.loads(bundle.read('manifest.json'))
        major = manifest.get('major')
        if manifest.get('format') != 1 or not isinstance(major, int) or not 10 <= major <= 99:
            raise ValueError('Versión de respaldo no reconocida.')
        return bundle.read('database.dump'), manifest


def run(command, environment=None, data=None):
    result = subprocess.run(command, env=environment, input=data, capture_output=True, cwd=ROOT, timeout=600)
    if result.returncode:
        # PostgreSQL errors may include connection details; never echo them.
        operation = ('pg_dump' if 'pg_dump' in command else 'pg_restore' if 'pg_restore' in command
            else command[-1] if 'backend/manage.py' in command else 'docker')
        if operation == 'verificar_auditoria':
            try:
                report = json.loads(result.stdout)
                print(json.dumps({name: report.get(name) for name in ['ok', 'cause', 'checked', 'broken_id']}), flush=True)
            except (ValueError, UnicodeError):
                pass
        raise RuntimeError(f'Falló la operación {operation}; no se imprimen credenciales.')
    return result.stdout


def counts(connection):
    tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
    return {name: connection.execute(sql.SQL('SELECT count(*) FROM {}.{}').format(
        sql.Identifier('public'), sql.Identifier(name))).fetchone()[0] for name, in tables}


def create_backup(url, key, development=False):
    pg = database_env(url, development)
    # Same exported snapshot for dump and expected row counts, even during writes.
    with psycopg.connect(url, connect_timeout=15) as connection:
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        major = connection.info.server_version // 10000
        snapshot = connection.execute('SELECT pg_export_snapshot()').fetchone()[0]
        expected = counts(connection)
        client = {**os.environ, **pg}
        if pg['PGHOST'] in ['localhost', '127.0.0.1', '::1']:
            client['PGHOST'] = 'host.docker.internal'
        command = ['docker', 'run', '--rm']
        for name in pg:
            command += ['-e', name]
        command += [f'postgres:{major}-alpine', 'pg_dump', '--format=custom', '--no-owner', '--no-privileges', '--snapshot', snapshot]
        dump = run(command, client)
    if len(dump) > 256 * 1024 * 1024:
        raise ValueError('El respaldo supera el límite de memoria de esta herramienta demo.')
    manifest = {'major': major, 'tables': expected, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'commit': os.environ.get('GITHUB_SHA', '')}
    return seal_bundle(dump, manifest, key)


@contextmanager
def isolated_database(major):
    name = 'datapulse-restore-' + secrets.token_hex(6)
    password = secrets.token_urlsafe(32)
    # No remote target argument exists. Restore always uses a new, labeled server.
    # The official image moved its declared data volume in PostgreSQL 18.
    directory = '/var/lib/postgresql' if major >= 18 else '/var/lib/postgresql/data'
    run(['docker', 'run', '-d', '--name', name, '--label', LABEL, '--tmpfs', directory,
        '-e', 'POSTGRES_DB=restored', '-e', 'POSTGRES_PASSWORD='+password,
        '-p', '127.0.0.1::5432', f'postgres:{major}-alpine'])
    try:
        for _ in range(60):
            result = subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'postgres'], capture_output=True)
            if result.returncode == 0:
                break
            if run(['docker', 'inspect', '--format', '{{.State.Running}}', name]).decode().strip() != 'true':
                raise RuntimeError('La base aislada terminó durante la inicialización.')
            time.sleep(1)
        else:
            raise RuntimeError('La base aislada no inició.')
        port = run(['docker', 'port', name, '5432/tcp']).decode().strip().rsplit(':', 1)[1]
        yield name, f'postgresql://postgres:{password}@127.0.0.1:{port}/restored'
    finally:
        label = run(['docker', 'inspect', '--format', '{{index .Config.Labels "datapulse.backup-verification"}}', name]).decode().strip()
        if label == 'true':
            run(['docker', 'rm', '-f', name])


def verify_backup(encrypted, key):
    dump, manifest = open_bundle(encrypted, key)
    print('Verification: authenticated archive opened.', flush=True)
    with isolated_database(manifest['major']) as (name, url):
        run(['docker', 'exec', '-i', name, 'pg_restore', '--exit-on-error', '--no-owner', '--no-privileges',
            '--username=postgres', '--dbname=restored'], data=dump)
        print('Verification: restored into disposable PostgreSQL.', flush=True)
        with psycopg.connect(url, connect_timeout=15) as connection:
            if counts(connection) != manifest['tables']:
                raise RuntimeError('Los conteos restaurados no coinciden con el snapshot.')
            assert connection.execute('SELECT 1').fetchone()[0] == 1
        print('Verification: snapshot row counts match.', flush=True)
        environment = {**os.environ, 'DATABASE_URL': url, 'SYNC_WORKER_REQUIRED': 'False'}
        for command in [['migrate', '--check'], ['check'], ['verificar_auditoria']]:
            run([sys.executable, 'backend/manage.py', *command], environment)
            print('Verification passed: '+command[0], flush=True)
    return {'ok': True, 'restored_in_isolation': True, 'tables_verified': len(manifest['tables']),
        'postgresql_major': manifest['major'], 'audit_verified': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='backups/encrypted')
    parser.add_argument('--archive', help='Verificar un respaldo existente; nunca recibe una base destino.')
    parser.add_argument('--development', action='store_true', help='Permitir fuente loopback sin TLS, solo para pruebas locales.')
    options = parser.parse_args()
    key = os.environ['DATAPULSE_BACKUP_KEY'].encode()
    Fernet(key)
    output = Path(options.output)
    output.mkdir(parents=True, exist_ok=True)
    if options.archive:
        encrypted = Path(options.archive).read_bytes()
    else:
        encrypted = create_backup(os.environ['DATABASE_URL'], key, options.development)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        archive = output / f'datapulse-{stamp}-{secrets.token_hex(3)}.dump.fernet'
        with archive.open('xb') as stream:
            stream.write(encrypted)
        archive.with_suffix(archive.suffix+'.sha256').write_text(hashlib.sha256(encrypted).hexdigest()+'\n')
    result = verify_backup(encrypted, key)
    result['duration_finished_utc'] = datetime.now(timezone.utc).isoformat()
    (output / 'verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Backup o restauración no verificado ({type(exc).__name__}); revisa configuración y conectividad. No se modificó la base fuente.', file=sys.stderr)
        if isinstance(exc, RuntimeError):
            print(str(exc), file=sys.stderr)
        sys.exit(1)
