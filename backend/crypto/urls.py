from django.urls import path
from . import views


urlpatterns = [
    path("local-keys/", views.local_keys, name="crypto_local_keys"),
]

