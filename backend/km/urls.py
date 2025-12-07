from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.status, name='km_status'),
    path('get_key/', views.get_key, name='km_get_key'),
    path('get_key_with_id/', views.get_key_with_id, name='km_get_key_with_id'),
]
