from django.urls import path
from . import views

urlpatterns = [
    path('connect', views.connect_account, name='connect_account'),
    path('', views.list_accounts, name='list_accounts'),
    path('<int:account_id>', views.delete_account, name='delete_account'),
]
