from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(DjangoUserAdmin):
    model = Usuario
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Perfil",
            {
                "fields": ("perfil",),
            },
        ),
    )

    list_display = ("username", "email", "perfil", "is_staff", "is_active")
    list_filter = ("perfil", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")

