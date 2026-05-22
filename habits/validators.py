from typing import Optional

from rest_framework.exceptions import ValidationError


def validate_reward_xor_related(reward: Optional[str], related_habit) -> None:
    """Запрещаем заполнять и `reward`, и `related_habit` одновременно."""
    if reward and related_habit is not None:
        raise ValidationError(
            "Нельзя одновременно указывать вознаграждение и связанную (приятную) привычку. Выберите что-то одно."
        )


def validate_duration(duration: Optional[int]) -> None:
    """Привычка не должна занимать больше 120 секунд."""
    if duration is None:
        return
    if duration > 120:
        raise ValidationError(
            "Время выполнения привычки не может превышать 120 секунд."
        )
    if duration <= 0:
        raise ValidationError(
            "Время выполнения должно быть положительным числом секунд."
        )


def validate_related_habit_is_pleasant(related_habit) -> None:
    """`related_habit` должна быть приятной привычкой."""
    if related_habit is None:
        return
    if not getattr(related_habit, "is_pleasant", False):
        raise ValidationError(
            "В качестве связанной привычки можно указывать только "
            "привычку с признаком «Приятная»."
        )


def validate_pleasant_has_no_reward_or_relation(
    is_pleasant: bool,
    reward: Optional[str],
    related_habit,
) -> None:
    """У приятной привычки не может быть ни reward, ни related_habit."""
    if not is_pleasant:
        return
    if reward:
        raise ValidationError("У приятной привычки не может быть вознаграждения.")
    if related_habit is not None:
        raise ValidationError("У приятной привычки не может быть связанной привычки.")


def validate_periodicity(periodicity: Optional[int]) -> None:
    """Периодичность — от 1 до 7 дней включительно."""
    if periodicity is None:
        return
    if periodicity < 1:
        raise ValidationError("Периодичность должна быть не менее 1 дня.")
    if periodicity > 7:
        raise ValidationError("Нельзя выполнять привычку реже, чем 1 раз в 7 дней.")


def run_habit_validators(
    *,
    is_pleasant: bool,
    reward: Optional[str],
    related_habit,
    periodicity: Optional[int],
    duration: Optional[int],
) -> None:
    """
    Общая точка входа для валидации привычки.

    Порядок имеет значение: сначала проверяем «приятная без бонусов» —
    это даёт пользователю более понятную ошибку, чем «нельзя оба поля сразу».
    """
    validate_pleasant_has_no_reward_or_relation(is_pleasant, reward, related_habit)
    validate_reward_xor_related(reward, related_habit)
    validate_related_habit_is_pleasant(related_habit)
    validate_periodicity(periodicity)
    validate_duration(duration)
