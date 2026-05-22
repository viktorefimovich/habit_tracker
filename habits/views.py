"""
Эндпоинты привычек.
"""

from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, viewsets

from habits.models import Habit
from habits.paginators import HabitPaginator
from habits.permissions import IsOwner
from habits.serializers import HabitSerializer


class HabitViewSet(viewsets.ModelViewSet):
    """
    CRUD по привычкам текущего пользователя
    """

    serializer_class = HabitSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwner)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Habit.objects.none()
        return Habit.objects.filter(user=self.request.user)

    def perform_create(self, serializer: HabitSerializer):
        """Автоматически проставляем текущего пользователя как владельца."""
        serializer.save(user=self.request.user)

    @swagger_auto_schema(operation_summary="Список своих привычек")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Создать привычку")
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Получить привычку")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Обновить привычку")
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Частичное обновление привычки")
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_summary="Удалить привычку")
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class PublicHabitListView(generics.ListAPIView):
    """
    Список публичных привычек.
    """

    serializer_class = HabitSerializer
    pagination_class = HabitPaginator
    permission_classes = (permissions.IsAuthenticated,)
    queryset = Habit.objects.filter(is_public=True)

    @swagger_auto_schema(operation_summary="Список публичных привычек")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
