"""
Тесты приложения habits.
"""

from datetime import datetime, time, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from habits.models import Habit
from habits.services import TelegramService, build_reminder_text
from habits.tasks import _is_time_to_remind, send_habit_reminders
from habits.validators import (run_habit_validators, validate_duration, validate_periodicity,
                               validate_pleasant_has_no_reward_or_relation, validate_related_habit_is_pleasant,
                               validate_reward_xor_related)

User = get_user_model()


def _make_user(email: str = "u@example.com", chat_id: str = "") -> User:
    user = User.objects.create_user(
        email=email,
        password="strong-pwd-123",
    )
    if chat_id:
        user.telegram_chat_id = chat_id
        user.save(update_fields=["telegram_chat_id"])
    return user


def _auth(user) -> str:
    """Получить access-токен и заголовок Bearer для тестового клиента."""
    return f"Bearer {RefreshToken.for_user(user).access_token}"


class HabitModelTests(APITestCase):
    def test_str(self) -> None:
        user = _make_user()
        habit = Habit.objects.create(
            user=user,
            place="дом",
            time=time(7, 30),
            action="зарядка",
            duration=60,
        )
        self.assertIn("зарядка", str(habit))
        self.assertIn("07:30", str(habit))

    def test_clean_calls_validators(self) -> None:
        """Model.clean() пробрасывает доменные ошибки."""
        user = _make_user()
        habit = Habit(
            user=user,
            place="дом",
            time=time(7, 30),
            action="плохая",
            duration=200,
        )
        with self.assertRaises(ValidationError):
            habit.clean()


class ValidatorsTests(APITestCase):
    """Проверяем все семь правил отдельно."""

    def test_reward_xor_related(self) -> None:
        with self.assertRaises(ValidationError):
            validate_reward_xor_related("шоколадка", MagicMock())
        validate_reward_xor_related("шоколадка", None)
        validate_reward_xor_related(None, MagicMock())

    def test_duration_too_long(self) -> None:
        with self.assertRaises(ValidationError):
            validate_duration(121)

    def test_duration_must_be_positive(self) -> None:
        with self.assertRaises(ValidationError):
            validate_duration(0)
        validate_duration(None)
        validate_duration(60)

    def test_related_habit_must_be_pleasant(self) -> None:
        not_pleasant = MagicMock(is_pleasant=False)
        with self.assertRaises(ValidationError):
            validate_related_habit_is_pleasant(not_pleasant)
        pleasant = MagicMock(is_pleasant=True)
        validate_related_habit_is_pleasant(pleasant)
        validate_related_habit_is_pleasant(None)

    def test_pleasant_cannot_have_reward(self) -> None:
        with self.assertRaises(ValidationError):
            validate_pleasant_has_no_reward_or_relation(True, "конфета", None)

    def test_pleasant_cannot_have_related(self) -> None:
        with self.assertRaises(ValidationError):
            validate_pleasant_has_no_reward_or_relation(True, None, MagicMock())

    def test_pleasant_clean_passes(self) -> None:
        validate_pleasant_has_no_reward_or_relation(True, None, None)

    def test_periodicity_bounds(self) -> None:
        with self.assertRaises(ValidationError):
            validate_periodicity(0)
        with self.assertRaises(ValidationError):
            validate_periodicity(8)
        validate_periodicity(7)
        validate_periodicity(1)
        validate_periodicity(None)

    def test_run_habit_validators_happy_path(self) -> None:
        run_habit_validators(
            is_pleasant=False,
            reward="шоколад",
            related_habit=None,
            periodicity=3,
            duration=60,
        )


class HabitApiTests(APITestCase):
    """CRUD-эндпоинты для своих привычек."""

    def setUp(self) -> None:
        self.user = _make_user("owner@example.com")
        self.other = _make_user("other@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=_auth(self.user))
        self.list_url = reverse("habits:habit-list")

    def _create_habit(self, **overrides) -> Habit:
        defaults = dict(
            user=self.user,
            place="дом",
            time=time(7, 30),
            action="зарядка",
            duration=60,
            periodicity=1,
        )
        defaults.update(overrides)
        return Habit.objects.create(**defaults)

    def test_requires_authentication(self) -> None:
        self.client.credentials()  # сбрасываем токен
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_habit(self) -> None:
        payload = {
            "place": "парк",
            "time": "07:00",
            "action": "пробежка",
            "duration": 60,
            "periodicity": 1,
            "reward": "смузи",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Habit.objects.get().user, self.user)

    def test_create_habit_rejects_invalid_duration(self) -> None:
        payload = {
            "place": "парк",
            "time": "07:00",
            "action": "марафон",
            "duration": 130,
            "periodicity": 1,
            "reward": "смузи",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_habit_rejects_reward_and_related(self) -> None:
        pleasant = self._create_habit(is_pleasant=True, action="ванна", reward=None)
        payload = {
            "place": "парк",
            "time": "07:00",
            "action": "йога",
            "duration": 60,
            "periodicity": 1,
            "reward": "что-то",
            "related_habit": pleasant.id,
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_related_habit_must_belong_to_user(self) -> None:
        pleasant = Habit.objects.create(
            user=self.other,
            place="дом",
            time=time(20, 0),
            action="ванна",
            duration=60,
            periodicity=1,
            is_pleasant=True,
        )
        payload = {
            "place": "дом",
            "time": "08:00",
            "action": "уборка",
            "duration": 60,
            "periodicity": 1,
            "related_habit": pleasant.id,
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_returns_only_own_habits(self) -> None:
        self._create_habit(action="моя")
        Habit.objects.create(
            user=self.other,
            place="дом",
            time=time(9, 0),
            action="чужая",
            duration=60,
            periodicity=1,
        )
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["action"], "моя")

    def test_pagination_returns_5_per_page(self) -> None:
        for i in range(7):
            self._create_habit(action=f"привычка-{i}")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertEqual(response.data["count"], 7)
        self.assertIsNotNone(response.data["next"])

    def test_cannot_access_other_users_habit(self) -> None:
        other_habit = Habit.objects.create(
            user=self.other,
            place="дом",
            time=time(9, 0),
            action="чужая",
            duration=60,
            periodicity=1,
        )
        url = reverse("habits:habit-detail", args=[other_habit.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_habit(self) -> None:
        habit = self._create_habit()
        url = reverse("habits:habit-detail", args=[habit.id])
        response = self.client.patch(url, {"action": "новая"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        habit.refresh_from_db()
        self.assertEqual(habit.action, "новая")

    def test_delete_habit(self) -> None:
        habit = self._create_habit()
        url = reverse("habits:habit-detail", args=[habit.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.filter(id=habit.id).exists())


class PublicHabitListTests(APITestCase):
    def setUp(self) -> None:
        self.user = _make_user("viewer@example.com")
        self.author = _make_user("author@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=_auth(self.user))
        self.url = reverse("habits:public-list")

    def test_returns_only_public_habits(self) -> None:
        Habit.objects.create(
            user=self.author,
            place="дом",
            time=time(7, 0),
            action="публичная",
            duration=60,
            periodicity=1,
            is_public=True,
        )
        Habit.objects.create(
            user=self.author,
            place="дом",
            time=time(8, 0),
            action="приватная",
            duration=60,
            periodicity=1,
            is_public=False,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["action"], "публичная")


class TelegramServiceTests(APITestCase):
    def test_returns_false_when_no_token(self) -> None:
        service = TelegramService(token="", api_url="https://api.telegram.org/bot")
        self.assertFalse(service.send_message("123", "hi"))

    def test_returns_false_when_no_chat_id(self) -> None:
        service = TelegramService(token="t", api_url="https://api.telegram.org/bot")
        self.assertFalse(service.send_message("", "hi"))

    @patch("habits.services.requests.post")
    def test_send_message_success(self, mock_post) -> None:
        mock_post.return_value = MagicMock(ok=True, status_code=200)
        service = TelegramService(token="t", api_url="https://api.telegram.org/bot")
        self.assertTrue(service.send_message("123", "hi"))
        mock_post.assert_called_once()

    @patch("habits.services.requests.post")
    def test_send_message_http_error(self, mock_post) -> None:
        mock_post.return_value = MagicMock(ok=False, status_code=500, text="boom")
        service = TelegramService(token="t", api_url="https://api.telegram.org/bot")
        self.assertFalse(service.send_message("123", "hi"))

    @patch(
        "habits.services.requests.post",
        side_effect=__import__("requests").RequestException("net"),
    )
    def test_send_message_network_error(self, _mock_post) -> None:
        service = TelegramService(token="t", api_url="https://api.telegram.org/bot")
        self.assertFalse(service.send_message("123", "hi"))

    def test_build_reminder_text(self) -> None:
        user = _make_user()
        habit = Habit.objects.create(
            user=user,
            place="дом",
            time=time(7, 30),
            action="зарядка",
            duration=60,
            periodicity=1,
        )
        text = build_reminder_text(habit)
        self.assertIn("зарядка", text)
        self.assertIn("07:30", text)
        self.assertIn("дом", text)


class CeleryTaskTests(APITestCase):
    """Тестируем send_habit_reminders с замокированным TelegramService."""

    def _now_at(self, hour: int, minute: int):
        now = timezone.localtime()
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def test_is_time_to_remind_first_time(self) -> None:
        user = _make_user(chat_id="42")
        habit = Habit(
            user=user,
            place="дом",
            time=time(10, 0),
            action="чай",
            duration=60,
            periodicity=1,
            last_notified_at=None,
        )
        self.assertTrue(_is_time_to_remind(habit, self._now_at(10, 0)))
        self.assertFalse(_is_time_to_remind(habit, self._now_at(10, 1)))

    def test_is_time_to_remind_respects_periodicity(self) -> None:
        user = _make_user(chat_id="42")
        habit = Habit(
            user=user,
            place="дом",
            time=time(10, 0),
            action="чай",
            duration=60,
            periodicity=3,
            last_notified_at=self._now_at(10, 0) - timedelta(days=1),
        )
        self.assertFalse(_is_time_to_remind(habit, self._now_at(10, 0)))

        habit.last_notified_at = self._now_at(10, 0) - timedelta(days=3)
        self.assertTrue(_is_time_to_remind(habit, self._now_at(10, 0)))

    @patch("habits.tasks.TelegramService")
    def test_send_habit_reminders_sends_messages(self, mock_service_cls) -> None:
        mock_service = MagicMock()
        mock_service.send_message.return_value = True
        mock_service_cls.return_value = mock_service

        user = _make_user(chat_id="100")
        now = timezone.localtime()
        Habit.objects.create(
            user=user,
            place="дом",
            time=now.time().replace(second=0, microsecond=0),
            action="вода",
            duration=10,
            periodicity=1,
        )
        user2 = _make_user("nochat@example.com", chat_id="")
        Habit.objects.create(
            user=user2,
            place="дом",
            time=now.time().replace(second=0, microsecond=0),
            action="никому",
            duration=10,
            periodicity=1,
        )

        sent = send_habit_reminders()
        self.assertEqual(sent, 1)
        mock_service.send_message.assert_called_once()

    @patch("habits.tasks.TelegramService")
    def test_send_habit_reminders_skips_when_not_time(self, mock_service_cls) -> None:
        mock_service = MagicMock()
        mock_service.send_message.return_value = True
        mock_service_cls.return_value = mock_service

        user = _make_user(chat_id="100")
        Habit.objects.create(
            user=user,
            place="дом",
            time=time(0, 0),
            action="ночное",
            duration=10,
            periodicity=1,
            last_notified_at=timezone.now(),
        )
        with patch("habits.tasks.timezone") as mock_tz:
            fake_now = datetime(
                2026, 1, 1, 12, 0, 0, tzinfo=timezone.get_current_timezone()
            )
            mock_tz.localtime.return_value = fake_now
            mock_tz.now.return_value = fake_now
            sent = send_habit_reminders()
        self.assertEqual(sent, 0)
        mock_service.send_message.assert_not_called()
