from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


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
