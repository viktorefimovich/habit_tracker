"""
Модель пользователя.

Используем email как уникальный идентификатор и добавляем поле
`telegram_chat_id` — для отправки напоминания о привычках.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Пользователь приложения трекера привычек."""

    username = None
    email = models.EmailField(unique=True, verbose_name="Почта", help_text="Укажите почту")
    telegram_chat_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="Telegram chat ID",
        help_text="Укажите telegram_chat_id",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email
