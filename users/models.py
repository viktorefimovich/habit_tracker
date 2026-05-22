"""
Модель пользователя.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from users.managers import UserManager


class User(AbstractUser):
    """Пользователь приложения трекера привычек."""

    username = None
    email = models.EmailField(
        unique=True, verbose_name="Почта", help_text="Укажите почту"
    )
    telegram_chat_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="Telegram chat ID",
        help_text="Укажите telegram_chat_id",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email
