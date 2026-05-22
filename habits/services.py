"""
Сервисный слой для взаимодействия с Telegram Bot API.
"""
import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """Тонкая обёртка над методом sendMessage Telegram Bot API."""

    REQUEST_TIMEOUT = 10

    def __init__(
        self,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.api_url = api_url or settings.TELEGRAM_API_URL

    def _build_url(self, method: str) -> str:
        # Telegram API ожидает формат вида: https://api.telegram.org/bot<TOKEN>/<method>
        return f"{self.api_url}{self.token}/{method}"

    def send_message(self, chat_id: str, text: str) -> bool:
        """
        Отправить текстовое сообщение пользователю.
        """
        if not self.token or not chat_id:
            logger.warning(
                "Не отправлено: token=%s, chat_id=%s",
                bool(self.token),
                chat_id,
            )
            return False

        url = self._build_url("sendMessage")
        payload = {"chat_id": chat_id, "text": text}
        try:
            response = requests.post(url, json=payload, timeout=self.REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            logger.error("Ошибка запроса к Telegram: %s", exc)
            return False

        if not response.ok:
            logger.error(
                "Telegram вернул ошибку %s: %s", response.status_code, response.text,
            )
            return False
        return True


def build_reminder_text(habit) -> str:
    """Формирование текста напоминания в формате книги «Атомные привычки»."""
    return (
        f"Напоминание! Пора выполнить привычку:\n"
        f"Я буду «{habit.action}» в {habit.time.strftime('%H:%M')} "
        f"в «{habit.place}».\n"
        f"Займёт не больше {habit.duration} сек."
    )
