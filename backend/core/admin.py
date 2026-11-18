from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario
from .models import (Moneda, Pais, IndicadorEconomico, TipoCambio, Portafolio,
                     Posicion, IndiceRiesgo, Alerta, LecturaAlerta, LogActividad)

for model in [Moneda, Pais, IndicadorEconomico, TipoCambio, Portafolio,
              Posicion, IndiceRiesgo, Alerta, LecturaAlerta]:
    admin.site.register(model)


@admin.register(LogActividad)
class AuditAdmin(admin.ModelAdmin):
    readonly_fields = [field.name for field in LogActividad._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ['email']
    list_display = ['email', 'nombre_completo', 'rol', 'activo', 'is_staff']
    search_fields = ['email', 'nombre_completo']
    fieldsets = (
        (None, {'fields': ('email', 'password', 'nombre_completo', 'rol', 'activo')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = ((None, {'fields': ('email', 'nombre_completo', 'password1', 'password2', 'rol')}),)
