from django.urls import path
from . import views

urlpatterns = [
    path('sync/<int:account_id>', views.sync_emails, name='sync_emails'),
    path('send', views.send_email, name='send_email'),
    path('<int:email_id>', views.get_email, name='get_email'),
    path('', views.list_emails, name='list_emails'),
]
