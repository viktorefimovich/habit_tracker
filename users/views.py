"""
Эндпоинты пользователей:
    * POST /api/users/register/      — регистрация (открытый доступ);
    * POST /api/users/login/         — получение пары access/refresh (SimpleJWT);
    * POST /api/users/token/refresh/ — обновление access-токена по refresh;
    * GET  /api/users/me/            — профиль текущего пользователя.

Авторизация на остальных эндпоинтах: заголовок `Authorization: Bearer <access>`.
"""
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.serializers import UserRegisterSerializer, UserSerializer


def _tokens_for_user(user) -> dict[str, str]:
    """
    Сгенерировать пару refresh/access для пользователя.

    Вынесено в утилиту, чтобы её можно было переиспользовать в RegisterView
    и в тестах (там же она используется без mock-ов, на реальной логике).
    """
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class RegisterView(generics.CreateAPIView):
    """
    Регистрация нового пользователя.
    """

    serializer_class = UserRegisterSerializer
    permission_classes = (permissions.AllowAny,)

    @swagger_auto_schema(
        operation_summary="Регистрация",
        operation_description="Создаёт нового пользователя и возвращает пару access/refresh.",
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = _tokens_for_user(user)
        return Response(
            {"user": UserSerializer(user).data, **tokens},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    Авторизация по email/паролю. Поскольку у нас `USERNAME_FIELD = "email"`,
    SimpleJWT ожидает в теле запроса ключ `email`, а не `username`.
    """

    permission_classes = (permissions.AllowAny,)

    @swagger_auto_schema(
        operation_summary="Авторизация",
        operation_description="Принимает email и password, возвращает access и refresh.",
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        return super().post(request, *args, **kwargs)


class RefreshView(TokenRefreshView):
    """Обновление access-токена по-действующему refresh-токену."""

    permission_classes = (permissions.AllowAny,)

    @swagger_auto_schema(
        operation_summary="Обновление access-токена",
        operation_description="Принимает refresh, возвращает новую пару access (и refresh при ротации).",
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        return super().post(request, *args, **kwargs)


class MeView(generics.RetrieveUpdateAPIView):
    """Получение и обновление профиля текущего пользователя."""

    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user
