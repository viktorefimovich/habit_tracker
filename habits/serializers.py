"""
Сериализатор привычки.
"""
from rest_framework import serializers

from habits.models import Habit
from habits.validators import run_habit_validators


class HabitSerializer(serializers.ModelSerializer):
    """Основной сериализатор привычки."""

    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Habit
        fields = (
            "id",
            "user",
            "place",
            "time",
            "action",
            "is_pleasant",
            "related_habit",
            "periodicity",
            "reward",
            "duration",
            "is_public",
        )

    def validate_related_habit(self, value):
        """
        Запрещаем выбирать чужие привычки в качестве связанной —
        иначе можно «утащить» приятную привычку другого пользователя.
        """
        if value is None:
            return value
        request = self.context.get("request")
        if request is not None and value.user_id != request.user.id:
            raise serializers.ValidationError(
                "Связанная привычка должна принадлежать вам."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """
        Запускаем доменные валидаторы. На PATCH-запросах поля могут
        отсутствовать — тогда берём значения из текущей instance.
        """
        instance = getattr(self, "instance", None)

        def pick(field: str):
            if field in attrs:
                return attrs[field]
            return getattr(instance, field, None)

        run_habit_validators(
            is_pleasant=bool(pick("is_pleasant")),
            reward=pick("reward"),
            related_habit=pick("related_habit"),
            periodicity=pick("periodicity"),
            duration=pick("duration"),
        )
        return attrs
