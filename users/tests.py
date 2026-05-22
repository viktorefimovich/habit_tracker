"""
Тесты приложения users: модель, регистрация, login, refresh, /me/.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def _access_for(user) -> str:
    """Получить валидный access-токен для пользователя."""
    return str(RefreshToken.for_user(user).access_token)


class UserModelTests(APITestCase):
    """Проверка кастомной модели пользователя."""

    def test_create_user(self) -> None:
        user = User.objects.create_user(
            email="alice@example.com",
            password="strongpass123",
        )
        self.assertEqual(user.email, "alice@example.com")
        self.assertTrue(user.check_password("strongpass123"))
        self.assertEqual(str(user), "alice@example.com")

    def test_email_is_unique(self) -> None:
        User.objects.create_user(email="bob@example.com", password="p1")
        with self.assertRaises(Exception):
            User.objects.create_user(email="bob@example.com", password="p2")


class RegisterEndpointTests(APITestCase):
    """POST /api/users/register/"""

    def setUp(self) -> None:
        self.url = reverse("users:register")

    def test_register_success(self) -> None:
        payload = {
            "email": "new@example.com",
            "username": "new",
            "password": "verysecret1",
            "telegram_chat_id": "12345",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "new@example.com")
        self.assertNotIn("password", response.data["user"])

    def test_register_invalid_password(self) -> None:
        payload = {"email": "x@example.com", "username": "x", "password": "short"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginEndpointTests(APITestCase):
    """POST /api/users/login/ — SimpleJWT TokenObtainPairView."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="user@example.com",
            password="strong-pwd-123",
        )
        self.url = reverse("users:login")

    def test_login_success(self) -> None:
        response = self.client.post(
            self.url,
            {"email": "user@example.com", "password": "strong-pwd-123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password(self) -> None:
        response = self.client.post(
            self.url,
            {"email": "user@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RefreshEndpointTests(APITestCase):
    """POST /api/users/token/refresh/"""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="ref@example.com",
            password="strong-pwd-123",
        )
        self.refresh = str(RefreshToken.for_user(self.user))
        self.url = reverse("users:token-refresh")

    def test_refresh_returns_new_access(self) -> None:
        response = self.client.post(self.url, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_invalid_token(self) -> None:
        response = self.client.post(self.url, {"refresh": "bogus"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeEndpointTests(APITestCase):
    """GET/PATCH /api/users/me/ — требует Bearer access-токен."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="me@example.com",
            password="strong-pwd-123",
        )
        self.access = _access_for(self.user)
        self.url = reverse("users:me")

    def test_me_requires_auth(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_profile(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@example.com")

    def test_me_patch_updates_telegram_chat_id(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        response = self.client.patch(
            self.url,
            {"telegram_chat_id": "999"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_chat_id, "999")
