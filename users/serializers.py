"""
Сериализаторы пользователей: регистрация и публичное представление.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации нового пользователя."""

    password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    class Meta:
        model = User
        fields = ("id", "email", "username", "password", "telegram_chat_id")
        extra_kwargs = {
            "username": {"required": False, "allow_blank": True},
            "telegram_chat_id": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data: dict) -> User:
        """
        Хэшируем пароль через `set_password` — без него в БД попадёт plain text,
        и любая аутентификация сломается.
        """
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Безопасное представление пользователя (без пароля)."""

    class Meta:
        model = User
        fields = ("id", "email", "username", "telegram_chat_id")
        read_only_fields = ("id",)
