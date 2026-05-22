"""
Модель «Привычка».

Привычка соответствует формуле из книги Дж. Клира «Атомные привычки»:

    «Я буду [ДЕЙСТВИЕ] в [ВРЕМЯ] в [МЕСТО]».

Поля разделены на семантические группы:
* что/когда/где — обязательная триада (action, time, place);
* приятная/полезная — флаг `is_pleasant` определяет тип привычки;
* мотивация — `reward` ИЛИ `related_habit` (но не одновременно — см. валидаторы);
* расписание — `periodicity` в днях и `duration` в секундах.

Бизнес-правила проверяются в `habits.validators` и подключены в clean()
(для админки) и в сериализаторе (для API).
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from habits.validators import run_habit_validators
from users.models import User


class Habit(models.Model):
    """Привычка пользователя — полезная или приятная."""

    MIN_PERIODICITY_DAYS = 1
    MAX_PERIODICITY_DAYS = 7
    MAX_DURATION_SECONDS = 120

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="habits",
        verbose_name="Пользователь",
    )
    place = models.CharField(
        max_length=255,
        verbose_name="Место",
        help_text="Где выполнять привычку.",
    )
    time = models.TimeField(
        verbose_name="Время",
        help_text="Когда выполнять привычку.",
    )
    action = models.CharField(
        max_length=255,
        verbose_name="Действие",
        help_text="Что именно делает пользователь.",
    )
    is_pleasant = models.BooleanField(
        default=False,
        verbose_name="Приятная привычка",
        help_text="True — привычка-награда, False — полезная привычка.",
    )
    related_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="users_of_this_reward",
        verbose_name="Связанная привычка",
        help_text="Указывается только для полезных привычек. "
        "Может ссылаться только на приятную привычку.",
    )
    periodicity = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(MIN_PERIODICITY_DAYS),
            MaxValueValidator(MAX_PERIODICITY_DAYS),
        ],
        verbose_name="Периодичность, дней",
        help_text="Раз в сколько дней повторять. От 1 до 7.",
    )
    reward = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Вознаграждение",
        help_text="Чем себя поощрить. Нельзя задавать вместе со связанной привычкой.",
    )
    duration = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(MAX_DURATION_SECONDS)],
        verbose_name="Время выполнения, сек",
        help_text="Не более 120 секунд.",
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="Публичная",
        help_text="Если True — привычка отображается в списке публичных.",
    )
    last_notified_at = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
        verbose_name="Последнее напоминание",
        help_text="Время последнего напоминания.",
    )

    class Meta:
        verbose_name = "Привычка"
        verbose_name_plural = "Привычки"
        ordering = ("time", "id")

    def __str__(self) -> str:
        return f"{self.action} в {self.time} ({self.place})"

    def clean(self) -> None:
        """Прогоняем доменные валидаторы — для проверок в админке."""
        run_habit_validators(
            is_pleasant=self.is_pleasant,
            reward=self.reward,
            related_habit=self.related_habit,
            periodicity=self.periodicity,
            duration=self.duration,
        )
