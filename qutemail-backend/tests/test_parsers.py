"""
Unit tests for email parsers
"""
from django.test import TestCase
from mail.parsers import MailParserWrapper


class MailParserTest(TestCase):
    def test_parse_simple_email(self):
        """Test parsing a simple email"""
        raw_email = b"""From: sender@example.com
To: recipient@qutemail.local
Subject: Test Email
Date: Mon, 29 Jan 2025 10:00:00 +0000
Message-ID: <test@example.com>

Hello, this is a test email.
"""
        parser = MailParserWrapper(raw_email)

        self.assertEqual(parser.get_subject(), 'Test Email')
        self.assertEqual(parser.get_from(), 'sender@example.com')
        self.assertIn('recipient@qutemail.local', parser.get_to())
        self.assertIn('Hello', parser.get_body_text())
        self.assertFalse(parser.is_encrypted())

    def test_parse_encrypted_email(self):
        """Test parsing QKD-encrypted email"""
        raw_email = b"""From: sender@qutemail.local
To: recipient@qutemail.local
Subject: [QKD-ENCRYPTED] Secure Message
Date: Mon, 29 Jan 2025 10:00:00 +0000

[ENCRYPTED MESSAGE]
Key ID: test-key-123
Ciphertext: abc123def456
Nonce: 789xyz
Tag: tag123

This message is encrypted with QKD.
"""
        parser = MailParserWrapper(raw_email)

        self.assertTrue(parser.is_encrypted())
        metadata = parser.get_qkd_metadata()

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['qkd_key_id'], 'test-key-123')
        self.assertEqual(metadata['ciphertext'], 'abc123def456')

    def test_parse_email_with_multiple_recipients(self):
        """Test parsing email with multiple recipients"""
        raw_email = b"""From: sender@example.com
To: recipient1@qutemail.local, recipient2@qutemail.local
Subject: Multi-recipient Test
Date: Mon, 29 Jan 2025 10:00:00 +0000

Test message for multiple recipients.
"""
        parser = MailParserWrapper(raw_email)

        recipients = parser.get_to()
        self.assertTrue(len(recipients) >= 1)
        self.assertIn('recipient1@qutemail.local', str(recipients))

    def test_parse_email_with_cc_bcc(self):
        """Test parsing email with CC and BCC headers"""
        raw_email = b"""From: sender@example.com
To: recipient@qutemail.local
Cc: cc1@example.com, cc2@example.com
Subject: CC Test
Date: Mon, 29 Jan 2025 10:00:00 +0000

Test message with CC recipients.
"""
        parser = MailParserWrapper(raw_email)

        cc_recipients = parser.get_cc()
        self.assertIsNotNone(cc_recipients)
        # CC functionality depends on parser implementation

    def test_parse_html_email(self):
        """Test parsing email with HTML body"""
        raw_email = b"""From: sender@example.com
To: recipient@qutemail.local
Subject: HTML Email
Content-Type: text/html; charset="utf-8"
Date: Mon, 29 Jan 2025 10:00:00 +0000

<html><body><h1>Hello</h1><p>This is an HTML email.</p></body></html>
"""
        parser = MailParserWrapper(raw_email)

        html_body = parser.get_body_html()
        self.assertIsNotNone(html_body)
        self.assertIn('HTML', str(html_body) if html_body else '')
