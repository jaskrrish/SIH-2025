"""
Unit tests for Email services
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from mail.services import EmailSendService
from mail.models import Email, EmailQueue, UserEmailSettings

User = get_user_model()


class EmailSendServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.settings = UserEmailSettings.objects.create(
            user=self.user,
            email_address='testuser@qutemail.local',
            display_name='Test User',
            enable_qkd_encryption=True
        )
        self.service = EmailSendService(self.user)

    def test_compose_email_plain(self):
        """Test composing plain (unencrypted) email"""
        email = self.service.compose_email(
            to_addresses=['recipient@example.com'],
            subject='Test Email',
            body_text='Hello, World!',
            encrypt=False
        )

        self.assertIsNotNone(email)
        self.assertEqual(email.subject, 'Test Email')
        self.assertFalse(email.is_encrypted)
        self.assertEqual(email.status, Email.Status.QUEUED)

        # Check queue entry was created
        self.assertTrue(EmailQueue.objects.filter(email=email).exists())

    def test_compose_email_encrypted(self):
        """Test composing QKD-encrypted email"""
        email = self.service.compose_email(
            to_addresses=['recipient@example.com'],
            subject='Secure Email',
            body_text='Secret message',
            encrypt=True
        )

        self.assertIsNotNone(email)
        self.assertTrue(email.is_encrypted)
        self.assertIsNotNone(email.qkd_key_id)
        self.assertIn('[QKD-ENCRYPTED]', email.subject)
        self.assertIn('Key ID:', email.body_text)


class QKDServiceTest(TestCase):
    def test_request_key_simulator_mode(self):
        """Test requesting key in simulator mode"""
        from qkd.services import QKDService

        service = QKDService()
        result = service.request_key(key_size=256)

        self.assertIn('key_id', result)
        self.assertIn('key_material', result)
        self.assertEqual(result['source'], 'simulator')
        self.assertEqual(len(result['key_material']), 64)  # 256 bits = 64 hex chars

    def test_get_key_by_id(self):
        """Test retrieving key by ID"""
        from qkd.services import QKDService

        service = QKDService()

        # Request a key
        key_data = service.request_key(256)
        key_id = key_data['key_id']

        # Retrieve the same key
        retrieved = service.get_key_by_id(key_id)
        self.assertEqual(retrieved['key_id'], key_id)
        self.assertIn('key_material', retrieved)
