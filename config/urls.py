"""
Корневой URL-конфиг.
"""

from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Habit tracker API",
        default_version="v0.1",
        description="API документация к проекту трекер привычек",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="viktorefimovich@bk.ru"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[
        permissions.AllowAny,
    ],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls", namespace="users")),
    path("api/habits/", include("habits.urls", namespace="habits")),
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
