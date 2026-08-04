from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView, MeView, CountryListView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    # Login: POST {"username": ..., "password": ...} -> {"access": ..., "refresh": ...}
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("login/refresh/", TokenRefreshView.as_view(), name="login-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("countries/", CountryListView.as_view(), name="countries"),
]