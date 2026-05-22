"""
Celery-задачи для рассылки напоминаний о привычках в Telegram.
"""
from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone

from habits.models import Habit
from habits.services import TelegramService, build_reminder_text


def _is_time_to_remind(habit: Habit, now: datetime) -> bool:
    """Проверяет надо ли прямо сейчас слать напоминание."""

    if habit.time.hour != now.hour or habit.time.minute != now.minute:
        return False

    if habit.last_notified_at is None:
        return True

    next_due = habit.last_notified_at + timedelta(days=habit.periodicity)
    return now >= next_due


@shared_task
def send_habit_reminders() -> int:
    """
    Раз в минуту пройтись по всем привычкам и разослать уведомления тем,
    у кого настало время. Возвращает количество отправленных сообщений.
    """
    now = timezone.localtime()
    service = TelegramService()
    sent = 0

    # select_related — чтобы не делать N+1 запросов за user-ом
    qs = (
        Habit.objects.select_related("user")
        .filter(user__telegram_chat_id__isnull=False)
        .exclude(user__telegram_chat_id="")
    )

    for habit in qs:
        if not _is_time_to_remind(habit, now):
            continue

        text = build_reminder_text(habit)
        ok = service.send_message(habit.user.telegram_chat_id, text)
        if ok:
            habit.last_notified_at = now
            habit.save(update_fields=["last_notified_at"])
            sent += 1
    return sent
