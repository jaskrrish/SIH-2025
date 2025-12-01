"""
URL routing for mail app API endpoints
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from mail.viewsets import (
    EmailViewSet,
    AttachmentViewSet,
    UserEmailSettingsViewSet,
    LabelViewSet,
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'emails', EmailViewSet, basename='email')
router.register(r'attachments', AttachmentViewSet, basename='attachment')
router.register(r'settings', UserEmailSettingsViewSet, basename='settings')
router.register(r'labels', LabelViewSet, basename='label')

urlpatterns = [
    path('', include(router.urls)),
]
