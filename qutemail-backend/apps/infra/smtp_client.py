"""
SMTP client for sending emails with attachment support
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate, make_msgid
from django.conf import settings
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SMTPClient:
    """Enhanced SMTP client with support for attachments, CC, BCC, and HTML"""

    def __init__(self):
        self.host = getattr(settings, 'SMTP_HOST', 'localhost')
        self.port = getattr(settings, 'SMTP_PORT', 587)
        self.use_tls = getattr(settings, 'SMTP_USE_TLS', True)

    def send_email(self,
                   from_addr: str,
                   to_addrs: List[str],
                   subject: str,
                   body_text: str = '',
                   body_html: str = '',
                   cc_addrs: List[str] = None,
                   bcc_addrs: List[str] = None,
                   attachments: List[Dict] = None,
                   message_id: str = None,
                   in_reply_to: str = None,
                   references: str = None,
                   username: str = None,
                   password: str = None) -> bool:
        """
        Send an email via SMTP with full RFC822 support

        Args:
            from_addr: Sender email address
            to_addrs: List of recipient email addresses
            subject: Email subject
            body_text: Plain text body content
            body_html: HTML body content (optional)
            cc_addrs: CC recipients
            bcc_addrs: BCC recipients
            attachments: List of dicts with 'filename', 'content_type', 'data'
            message_id: Custom Message-ID header
            in_reply_to: In-Reply-To header for threading
            references: References header for threading
            username: SMTP auth username
            password: SMTP auth password

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message container
            if body_html:
                msg = MIMEMultipart('alternative')
            elif attachments:
                msg = MIMEMultipart('mixed')
            else:
                msg = MIMEMultipart()

            # Set headers
            msg['From'] = from_addr
            msg['To'] = ', '.join(to_addrs)
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)

            if cc_addrs:
                msg['Cc'] = ', '.join(cc_addrs)

            if message_id:
                msg['Message-ID'] = message_id
            else:
                msg['Message-ID'] = make_msgid(domain='qutemail.local')

            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to

            if references:
                msg['References'] = references

            # Attach body
            if body_html:
                # Create alternative part for text and HTML
                text_part = MIMEText(body_text, 'plain', 'utf-8')
                html_part = MIMEText(body_html, 'html', 'utf-8')
                msg.attach(text_part)
                msg.attach(html_part)
            else:
                text_part = MIMEText(body_text, 'plain', 'utf-8')
                msg.attach(text_part)

            # Attach files
            if attachments:
                for attachment in attachments:
                    self._attach_file(msg, attachment)

            # Prepare recipient list (To + Cc + Bcc)
            all_recipients = to_addrs.copy()
            if cc_addrs:
                all_recipients.extend(cc_addrs)
            if bcc_addrs:
                all_recipients.extend(bcc_addrs)

            # Send email
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                # Enable debug logging
                server.set_debuglevel(0)

                if self.use_tls:
                    server.starttls()

                if username and password:
                    server.login(username, password)

                server.send_message(msg, from_addr=from_addr, to_addrs=all_recipients)

            logger.info(f"Email sent successfully from {from_addr} to {to_addrs}")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {str(e)}")
            return False
        except Exception as e:
            logger.exception(f"Failed to send email: {str(e)}")
            return False

    def _attach_file(self, msg: MIMEMultipart, attachment: Dict):
        """
        Attach a file to the email message

        Args:
            msg: MIME message object
            attachment: Dict with 'filename', 'content_type', 'data'
        """
        filename = attachment['filename']
        content_type = attachment.get('content_type', 'application/octet-stream')
        data = attachment['data']

        # Parse content type
        maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')

        if maintype == 'text':
            # Text attachment
            part = MIMEText(data.decode('utf-8') if isinstance(data, bytes) else data, _subtype=subtype)
        else:
            # Binary attachment
            part = MIMEBase(maintype, subtype)
            part.set_payload(data)
            encoders.encode_base64(part)

        # Set filename
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')

        # Handle inline images
        if attachment.get('is_inline') and attachment.get('content_id'):
            part.add_header('Content-ID', f"<{attachment['content_id']}>")

        msg.attach(part)

    def verify_connection(self, username: str = None, password: str = None) -> bool:
        """
        Verify SMTP connection and authentication

        Args:
            username: SMTP username
            password: SMTP password

        Returns:
            True if connection successful
        """
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()

                if username and password:
                    server.login(username, password)

            logger.info("SMTP connection verified successfully")
            return True

        except Exception as e:
            logger.error(f"SMTP connection verification failed: {str(e)}")
            return False
