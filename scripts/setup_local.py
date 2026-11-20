"""Create a local .env with independent random keys; preserve existing files."""
import argparse
import base64
from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parents[1]


def initialize(target):
    template = (ROOT / '.env.example').read_text(encoding='utf-8')
    values = {
        'SECRET_KEY': secrets.token_urlsafe(64),
        'AUDIT_HMAC_KEY': secrets.token_urlsafe(64),
        'MFA_KEY': secrets.token_urlsafe(64),
        'FIELD_ENCRYPTION_KEY': base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        'POSTGRES_PASSWORD': secrets.token_urlsafe(32),
    }
    lines = []
    for line in template.splitlines():
        key = line.split('=', 1)[0]
        lines.append(f'{key}={values[key]}' if key in values else line)
    try:
        # Exclusive creation also protects against two concurrent initializers.
        with Path(target).open('x', encoding='utf-8', newline='\n') as output:
            output.write('\n'.join(lines) + '\n')
    except FileExistsError:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    args = parser.parse_args()
    created = initialize(args.env_file)
    print('Configuración local creada con claves aleatorias.' if created else
          'El archivo ya existe; no se modificó ninguna configuración ni clave.')


if __name__ == '__main__':
    main()
