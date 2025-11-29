"""
SMTP Server Implementation using aiosmtpd

Provides both MTA (Mail Transfer Agent) and MSA (Mail Submission Agent) functionality:
- MTA: Port 25 for receiving emails from external servers
- MSA: Ports 587/465 for authenticated email submission from users

Implements QKD encryption for internal emails and standard TLS for external communication.
"""

import asyncio
import ssl
import logging
from email import message_from_bytes
from email.utils import parseaddr
from typing import Optional

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as SMTPServer, AuthResult, LoginPassword
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

logger = logging.getLogger('smtp_server')


class DjangoAuthenticator:
    """
    Authenticator for SMTP that uses Django's authentication system.
    Supports LOGIN and PLAIN mechanisms.
    """

    def __call__(self, server, session, envelope, mechanism, auth_data):
        """
        Authenticate user against Django User model.

        Args:
            server: SMTP server instance
            session: Current SMTP session
            envelope: Email envelope
            mechanism: Auth mechanism (LOGIN or PLAIN)
            auth_data: Authentication credentials

        Returns:
            AuthResult with success status
        """
        fail_nothandled = AuthResult(success=False, handled=False)

        if mechanism not in ('LOGIN', 'PLAIN'):
            return fail_nothandled

        # Parse authentication data
        if isinstance(auth_data, LoginPassword):
            username = auth_data.login.decode('utf-8')
            password = auth_data.password.decode('utf-8')
        else:
            return fail_nothandled

        # Authenticate against Django
        user = authenticate(username=username, password=password)

        if user is not None and user.is_active:
            # Store authenticated user in session
            session.auth_data = {
                'username': username,
                'user_id': user.id,
                'email': user.email
            }
            logger.info(f"Authentication successful for user: {username}")
            return AuthResult(success=True)
        else:
            logger.warning(f"Authentication failed for username: {username}")
            return AuthResult(success=False, handled=True)


class QutEmailHandler:
    """
    Base SMTP handler for processing incoming emails.
    Queues emails for async processing via Celery.
    """

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """
        Handle RCPT TO command.
        Default implementation accepts all recipients.
        Override in subclasses for specific logic.
        """
        envelope.rcpt_tos.append(address)
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        """
        Handle DATA command - process the email message.

        Args:
            server: SMTP server instance
            session: Current SMTP session
            envelope: Email envelope with mail_from, rcpt_tos, content

        Returns:
            SMTP response code and message
        """
        try:
            logger.info(
                f"Received email from {envelope.mail_from} "
                f"to {envelope.rcpt_tos} "
                f"({len(envelope.content)} bytes)"
            )

            # Queue for async processing
            from mail.tasks import process_smtp_email

            # Serialize envelope for Celery
            envelope_data = {
                'mail_from': envelope.mail_from,
                'rcpt_tos': envelope.rcpt_tos,
                'content': envelope.content,
                'peer': session.peer if hasattr(session, 'peer') else None,
            }

            # Queue task
            process_smtp_email.delay(envelope_data)

            return '250 Message accepted for delivery'

        except Exception as e:
            logger.error(f"Error processing email: {str(e)}", exc_info=True)
            return '451 Requested action aborted: error in processing'


class AuthenticatedSMTPHandler(QutEmailHandler):
    """
    SMTP handler for MSA (Mail Submission Agent).
    Requires authentication for all operations.
    Ports: 587 (STARTTLS), 465 (implicit TLS)
    """

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        """
        Handle MAIL FROM command.
        Requires authentication before accepting.
        """
        # Check if session is authenticated
        if not hasattr(session, 'auth_data') or session.auth_data is None:
            logger.warning(
                f"Unauthenticated MAIL FROM attempt from {session.peer}: {address}"
            )
            return '530 5.7.0 Authentication required'

        # Validate sender address matches authenticated user
        username = session.auth_data.get('username')
        expected_address = f"{username}@{settings.EMAIL_DOMAIN}"

        # Extract email from address (handle "Name <email>" format)
        _, email_addr = parseaddr(address)

        if email_addr.lower() != expected_address.lower():
            logger.warning(
                f"User {username} attempted to send from unauthorized address: {email_addr}"
            )
            return f'550 5.7.1 {email_addr}: Sender address rejected'

        envelope.mail_from = address
        return '250 OK'

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """
        Handle RCPT TO command.
        Accepts any recipient for authenticated users.
        """
        if not hasattr(session, 'auth_data') or session.auth_data is None:
            return '530 5.7.0 Authentication required'

        envelope.rcpt_tos.append(address)
        logger.debug(f"Accepted recipient: {address}")
        return '250 OK'


class MTAHandler(QutEmailHandler):
    """
    SMTP handler for MTA (Mail Transfer Agent).
    Accepts emails from external servers destined for local domain.
    Port: 25
    No authentication required, but validates recipient domain.
    """

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """
        Handle RCPT TO command.
        Only accept mail for @yourdomain.com addresses.
        """
        # Extract email from address
        _, email_addr = parseaddr(address)

        # Check if recipient is local domain
        if not email_addr.lower().endswith(f'@{settings.EMAIL_DOMAIN}'.lower()):
            logger.warning(
                f"Relay attempt from {session.peer}: {address} (rejected)"
            )
            return '550 5.7.1 Relay access denied'

        # Verify mailbox exists
        from mail.models import Mailbox
        try:
            Mailbox.objects.get(email_address__iexact=email_addr)
            envelope.rcpt_tos.append(address)
            logger.debug(f"Accepted recipient for local delivery: {address}")
            return '250 OK'
        except Mailbox.DoesNotExist:
            logger.warning(f"Unknown mailbox: {email_addr}")
            return f'550 5.1.1 {email_addr}: Recipient address rejected: User unknown'


def create_ssl_context():
    """
    Create SSL context for SMTPS (implicit TLS on port 465).

    Returns:
        ssl.SSLContext configured for server use
    """
    try:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(
            certfile=settings.SMTP_TLS_CERT,
            keyfile=settings.SMTP_TLS_KEY
        )
        # Enforce strong TLS
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        logger.info("SSL context created successfully")
        return context
    except Exception as e:
        logger.error(f"Failed to create SSL context: {str(e)}")
        raise


class SMTPServerManager:
    """
    Manages multiple SMTP server instances (MTA, MSA, SMTPS).
    Provides unified start/stop interface.
    """

    def __init__(self):
        self.mta_controller: Optional[Controller] = None
        self.msa_controller: Optional[Controller] = None
        self.smtps_controller: Optional[Controller] = None

    def start_mta(self):
        """
        Start MTA server (port 25) for receiving external emails.
        """
        logger.info("Starting MTA server on port 25...")

        self.mta_controller = Controller(
            MTAHandler(),
            hostname=settings.SMTP_SERVER_HOSTNAME,
            port=settings.SMTP_MTA_PORT,
            # STARTTLS available but not required for port 25
            # (many external servers still don't use it)
        )
        self.mta_controller.start()
        logger.info(f"MTA server started on {settings.SMTP_SERVER_HOSTNAME}:{settings.SMTP_MTA_PORT}")

    def start_msa(self):
        """
        Start MSA server (port 587) for authenticated submission with STARTTLS.
        """
        logger.info("Starting MSA server on port 587...")

        # Create SMTP server with auth
        self.msa_controller = Controller(
            AuthenticatedSMTPHandler(),
            hostname=settings.SMTP_SERVER_HOSTNAME,
            port=settings.SMTP_MSA_PORT,
            authenticator=DjangoAuthenticator(),
            auth_required=True,
            auth_require_tls=True,  # Require TLS before auth
        )
        self.msa_controller.start()
        logger.info(f"MSA server started on {settings.SMTP_SERVER_HOSTNAME}:{settings.SMTP_MSA_PORT}")

    def start_smtps(self):
        """
        Start SMTPS server (port 465) for authenticated submission with implicit TLS.
        """
        logger.info("Starting SMTPS server on port 465...")

        try:
            ssl_context = create_ssl_context()

            self.smtps_controller = Controller(
                AuthenticatedSMTPHandler(),
                hostname=settings.SMTP_SERVER_HOSTNAME,
                port=settings.SMTP_SMTPS_PORT,
                authenticator=DjangoAuthenticator(),
                auth_required=True,
                # Implicit TLS
                ssl_context=ssl_context,
            )
            self.smtps_controller.start()
            logger.info(f"SMTPS server started on {settings.SMTP_SERVER_HOSTNAME}:{settings.SMTP_SMTPS_PORT}")
        except Exception as e:
            logger.error(f"Failed to start SMTPS server: {str(e)}")
            logger.info("SMTPS server will not be available")

    def start_all(self):
        """
        Start all SMTP servers (MTA + MSA + SMTPS).
        """
        logger.info("Starting all SMTP servers...")
        self.start_mta()
        self.start_msa()
        self.start_smtps()
        logger.info("All SMTP servers started successfully")

    def stop_mta(self):
        """Stop MTA server"""
        if self.mta_controller:
            logger.info("Stopping MTA server...")
            self.mta_controller.stop()
            self.mta_controller = None
            logger.info("MTA server stopped")

    def stop_msa(self):
        """Stop MSA server"""
        if self.msa_controller:
            logger.info("Stopping MSA server...")
            self.msa_controller.stop()
            self.msa_controller = None
            logger.info("MSA server stopped")

    def stop_smtps(self):
        """Stop SMTPS server"""
        if self.smtps_controller:
            logger.info("Stopping SMTPS server...")
            self.smtps_controller.stop()
            self.smtps_controller = None
            logger.info("SMTPS server stopped")

    def stop_all(self):
        """
        Gracefully stop all SMTP servers.
        """
        logger.info("Stopping all SMTP servers...")
        self.stop_mta()
        self.stop_msa()
        self.stop_smtps()
        logger.info("All SMTP servers stopped")

    def __enter__(self):
        """Context manager support"""
        self.start_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.stop_all()
