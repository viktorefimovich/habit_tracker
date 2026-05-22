"""URL-маршруты приложения habits."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from habits.views import HabitViewSet, PublicHabitListView

app_name = "habits"

router = DefaultRouter()
router.register(r"", HabitViewSet, basename="habit")

urlpatterns = [
    path("public/", PublicHabitListView.as_view(), name="public-list"),
    path("", include(router.urls)),
]
