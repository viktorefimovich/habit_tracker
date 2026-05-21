from django.urls import path

from users.views import LoginView, MeView, RefreshView, RegisterView

app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]
