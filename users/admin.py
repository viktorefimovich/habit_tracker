from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Админка для пользователя."""

    list_display = ("id", "email", "telegram_chat_id", "is_staff")
    search_fields = ("email", "telegram_chat_id")
    ordering = ("id",)

    fieldsets = UserAdmin.fieldsets + (
        ("Telegram", {"fields": ("telegram_chat_id",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Telegram", {"fields": ("telegram_chat_id",)}),
    )
