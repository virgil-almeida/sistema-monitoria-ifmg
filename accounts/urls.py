from django.urls import path

from accounts.views import MyLoginView, MyLogoutView, RegisterUserView

app_name = "accounts"

urlpatterns = [
    path("login/", MyLoginView.as_view(), name="login"),
    path("logout/", MyLogoutView.as_view(), name="logout"),
    path("register/", RegisterUserView.as_view(), name="register"),
]

