"""
URL configuration for qutemail_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path("api/auth/", include("accounts.urls")),  # /api/auth/register, /api/auth/login, /api/auth/me
    
    # Email Accounts
    path("api/email-accounts/", include("email_accounts.urls")),  # /api/email-accounts/connect, list, delete
    
    # Mail (IMAP/SMTP)
    path("api/mail/", include("mail.urls")),  # /api/mail/sync, send, list
    
    path("api/km/", include("km.urls")),  # KM simulator endpoints
    path("api/crypto/", include("crypto.urls")),  # Crypto utilities (local KM cache)
]
