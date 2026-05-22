"""
Права доступа: владелец может всё, остальные — только читать.
"""

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Разрешает доступ к объекту только его владельцу."""

    message = "Вы можете работать только со своими привычками."

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.user_id == request.user.id
