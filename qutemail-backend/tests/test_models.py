"""
Unit tests for Email models
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from mail.models import Email, EmailQueue, EmailLog, UserEmailSettings

User = get_user_model()


class EmailModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.settings = UserEmailSettings.objects.create(
            user=self.user,
            email_address='testuser@qutemail.local',
            display_name='Test User'
        )

    def test_email_creation(self):
        """Test creating an email"""
        email = Email.objects.create(
            user=self.user,
            message_id='<test@qutemail.local>',
            folder=Email.Folder.INBOX,
            subject='Test Email',
            from_address='sender@example.com',
            to_addresses=['testuser@qutemail.local'],
            body_text='This is a test email',
            status=Email.Status.RECEIVED
        )

        self.assertEqual(email.subject, 'Test Email')
        self.assertFalse(email.is_read)
        self.assertFalse(email.is_starred)
        self.assertFalse(email.is_encrypted)

    def test_mark_as_read(self):
        """Test marking email as read"""
        email = Email.objects.create(
            user=self.user,
            message_id='<test2@qutemail.local>',
            folder=Email.Folder.INBOX,
            subject='Test',
            from_address='sender@example.com',
            to_addresses=['testuser@qutemail.local'],
            body_text='Test',
            status=Email.Status.RECEIVED
        )

        self.assertFalse(email.is_read)
        email.mark_as_read()
        self.assertTrue(email.is_read)

    def test_move_to_folder(self):
        """Test moving email to different folder"""
        email = Email.objects.create(
            user=self.user,
            message_id='<test3@qutemail.local>',
            folder=Email.Folder.INBOX,
            subject='Test',
            from_address='sender@example.com',
            to_addresses=['testuser@qutemail.local'],
            body_text='Test',
            status=Email.Status.RECEIVED
        )

        email.move_to_folder(Email.Folder.ARCHIVE)
        self.assertEqual(email.folder, Email.Folder.ARCHIVE)


class EmailQueueTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.settings = UserEmailSettings.objects.create(
            user=self.user,
            email_address='testuser@qutemail.local',
            display_name='Test User'
        )

    def test_queue_locking(self):
        """Test queue entry locking mechanism"""
        email = Email.objects.create(
            user=self.user,
            message_id='<test4@qutemail.local>',
            folder=Email.Folder.SENT,
            subject='Test',
            from_address='testuser@qutemail.local',
            to_addresses=['recipient@example.com'],
            body_text='Test',
            status=Email.Status.QUEUED
        )

        queue = EmailQueue.objects.create(email=email)

        # Test locking
        self.assertFalse(queue.is_locked)
        queue.lock(worker_id='worker-1')
        self.assertTrue(queue.is_locked)
        self.assertEqual(queue.locked_by, 'worker-1')

        # Test unlocking
        queue.unlock()
        self.assertFalse(queue.is_locked)
        self.assertIsNone(queue.locked_by)
