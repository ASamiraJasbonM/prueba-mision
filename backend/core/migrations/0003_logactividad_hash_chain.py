import hashlib
import hmac
import json
from datetime import timezone
from django.conf import settings
from django.db import migrations, models


def backfill(apps, schema_editor):
    Log = apps.get_model('core', 'LogActividad')
    Head = apps.get_model('core', 'AuditHead')
    alias = schema_editor.connection.alias
    previous = None
    for row in Log.objects.using(alias).order_by('pk').iterator():
        fields = {'v': 1, 'id': row.pk, 'usuario_id': row.usuario_id, 'accion': row.accion,
                  'entidad_afectada': row.entidad_afectada, 'entidad_id': row.entidad_id,
                  'detalle': row.detalle, 'ip_address': row.ip_address,
                  'fecha': row.fecha.astimezone(timezone.utc).isoformat()}
        payload = json.dumps(fields, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        digest = hashlib.sha256(((previous or '') + payload).encode()).hexdigest()
        signature = hmac.new(settings.AUDIT_HMAC_KEY.encode(), digest.encode(), hashlib.sha256).hexdigest()
        Log.objects.using(alias).filter(pk=row.pk).update(hash_anterior=previous, hash_actual=digest, firma_hmac=signature)
        previous = digest
    Head.objects.using(alias).create(pk=1, hash_actual=previous or '')


def append_only(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    # REVOKE alone does not restrict a table owner (the default local role).
    # A trigger also blocks owners' UPDATE/DELETE; a separate non-owner role is
    # still required in production. Superusers can always bypass this control.
    schema_editor.execute('''
        CREATE FUNCTION datapulse_audit_append_only() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'audit log is append-only' USING ERRCODE = '42501'; END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER datapulse_audit_append_only BEFORE UPDATE OR DELETE
        ON core_logactividad FOR EACH ROW EXECUTE FUNCTION datapulse_audit_append_only();
        REVOKE UPDATE, DELETE ON core_logactividad FROM CURRENT_USER;
    ''')


def remove_guard(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('''DROP TRIGGER IF EXISTS datapulse_audit_append_only ON core_logactividad;
            DROP FUNCTION IF EXISTS datapulse_audit_append_only();
            GRANT UPDATE, DELETE ON core_logactividad TO CURRENT_USER;''')


class Migration(migrations.Migration):
    dependencies = [('core', '0002_dominio_economico')]
    operations = [
        migrations.CreateModel(name='AuditHead', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('hash_actual', models.CharField(blank=True, default='', max_length=64)),
        ]),
        migrations.AlterField(model_name='logactividad', name='accion', field=models.CharField(
            choices=[('CREAR', 'Crear'), ('EDITAR', 'Editar'), ('ELIMINAR', 'Eliminar'),
                     ('CONSULTAR', 'Consultar'), ('LOGIN', 'Login'), ('EXPORT', 'Exportar')], max_length=32)),
        migrations.AddField(model_name='logactividad', name='hash_anterior', field=models.CharField(blank=True, max_length=64, null=True)),
        migrations.AddField(model_name='logactividad', name='hash_actual', field=models.CharField(max_length=64, null=True)),
        migrations.AddField(model_name='logactividad', name='firma_hmac', field=models.CharField(max_length=64, default=''), preserve_default=False),
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.AlterField(model_name='logactividad', name='hash_actual', field=models.CharField(max_length=64, unique=True)),
        migrations.RunPython(append_only, remove_guard),
    ]
