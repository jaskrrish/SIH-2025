"""
IMAP client for retrieving emails with UID-based incremental fetching
"""
import imaplib
import email
import logging
from email.header import decode_header
from django.conf import settings
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class IMAPClient:
    """Enhanced IMAP client with UID-based incremental fetching"""

    def __init__(self):
        self.host = getattr(settings, 'IMAP_HOST', 'localhost')
        self.port = getattr(settings, 'IMAP_PORT', 993)
        self.use_ssl = getattr(settings, 'IMAP_USE_SSL', True)

    def connect(self, username: str, password: str):
        """
        Connect to IMAP server

        Args:
            username: IMAP username
            password: IMAP password

        Returns:
            IMAP connection object
        """
        try:
            if self.use_ssl:
                imap = imaplib.IMAP4_SSL(self.host, self.port, timeout=30)
            else:
                imap = imaplib.IMAP4(self.host, self.port, timeout=30)

            imap.login(username, password)
            logger.info(f"IMAP connection established for {username}")
            return imap

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP connection failed: {str(e)}")
            raise

    def fetch_new_emails(
        self,
        username: str,
        password: str,
        folder: str = 'INBOX',
        last_uid: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Fetch new emails using UID-based incremental fetching

        Args:
            username: IMAP username
            password: IMAP password
            folder: Mailbox folder (default: INBOX)
            last_uid: Last processed UID (fetch only newer emails)
            limit: Maximum number of emails to fetch

        Returns:
            List of dicts with 'uid' and 'raw' (RFC822 bytes)
        """
        emails = []

        try:
            imap = self.connect(username, password)
            status, _ = imap.select(folder, readonly=False)

            if status != 'OK':
                logger.error(f"Failed to select folder {folder}")
                return emails

            # Build search criteria based on UID
            if last_uid:
                # Fetch only UIDs greater than last_uid
                search_criteria = f'UID {last_uid + 1}:*'
            else:
                # Fetch all emails (or latest N)
                search_criteria = 'ALL'

            # Search for messages
            status, messages = imap.uid('SEARCH', None, search_criteria)

            if status != 'OK':
                logger.error("IMAP search failed")
                return emails

            # Get UIDs
            uid_list = messages[0].split()

            if not uid_list:
                logger.info("No new emails to fetch")
                return emails

            # Limit to most recent N emails
            uid_list = uid_list[-limit:]

            logger.info(f"Fetching {len(uid_list)} emails from {folder}")

            # Fetch each email by UID
            for uid in uid_list:
                try:
                    uid_int = int(uid.decode())
                    status, msg_data = imap.uid('FETCH', uid, '(RFC822)')

                    if status != 'OK' or not msg_data or msg_data[0] is None:
                        logger.warning(f"Failed to fetch UID {uid_int}")
                        continue

                    # Extract raw email bytes
                    raw_email = msg_data[0][1]

                    emails.append({
                        'uid': uid_int,
                        'raw': raw_email
                    })

                except Exception as e:
                    logger.exception(f"Error fetching UID {uid}: {str(e)}")
                    continue

            imap.close()
            imap.logout()

            logger.info(f"Successfully fetched {len(emails)} emails")

        except Exception as e:
            logger.exception(f"Failed to fetch emails: {str(e)}")

        return emails

    def fetch_emails(
        self,
        username: str,
        password: str,
        folder: str = 'INBOX',
        limit: int = 10
    ) -> List[Dict]:
        """
        Fetch emails from mailbox (legacy method for compatibility)

        Args:
            username: IMAP username
            password: IMAP password
            folder: Mailbox folder (default: INBOX)
            limit: Maximum number of emails to fetch

        Returns:
            List of email dictionaries
        """
        emails = []

        try:
            imap = self.connect(username, password)
            imap.select(folder)

            # Search for all emails
            status, messages = imap.search(None, 'ALL')

            if status != 'OK':
                return emails

            # Get message IDs
            msg_ids = messages[0].split()[-limit:]

            for msg_id in msg_ids:
                status, msg_data = imap.fetch(msg_id, '(RFC822)')

                if status != 'OK':
                    continue

                # Parse email
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract headers
                subject = self._decode_header(msg['Subject'])
                from_addr = msg['From']
                to_addr = msg['To']
                date = msg['Date']

                # Extract body
                body = self._get_body(msg)

                emails.append({
                    'id': msg_id.decode(),
                    'subject': subject,
                    'from': from_addr,
                    'to': to_addr,
                    'date': date,
                    'body': body,
                    'raw': raw_email
                })

            imap.close()
            imap.logout()

        except Exception as e:
            logger.exception(f"Failed to fetch emails: {str(e)}")

        return emails

    def get_folder_list(self, username: str, password: str) -> List[str]:
        """
        Get list of available IMAP folders

        Args:
            username: IMAP username
            password: IMAP password

        Returns:
            List of folder names
        """
        try:
            imap = self.connect(username, password)
            status, folders = imap.list()

            if status != 'OK':
                return []

            folder_list = []
            for folder in folders:
                # Parse folder name from IMAP list response
                # Format: (\\HasNoChildren) "." "INBOX"
                parts = folder.decode().split('"')
                if len(parts) >= 3:
                    folder_list.append(parts[-2])

            imap.logout()
            return folder_list

        except Exception as e:
            logger.exception(f"Failed to get folder list: {str(e)}")
            return []

    def mark_as_read(self, username: str, password: str, uid: int, folder: str = 'INBOX') -> bool:
        """
        Mark an email as read using UID

        Args:
            username: IMAP username
            password: IMAP password
            uid: Email UID
            folder: Mailbox folder

        Returns:
            True if successful
        """
        try:
            imap = self.connect(username, password)
            imap.select(folder, readonly=False)

            imap.uid('STORE', str(uid), '+FLAGS', '\\Seen')

            imap.close()
            imap.logout()

            logger.info(f"Marked email UID {uid} as read")
            return True

        except Exception as e:
            logger.exception(f"Failed to mark email as read: {str(e)}")
            return False

    def delete_email(self, username: str, password: str, uid: int, folder: str = 'INBOX') -> bool:
        """
        Delete an email using UID

        Args:
            username: IMAP username
            password: IMAP password
            uid: Email UID
            folder: Mailbox folder

        Returns:
            True if successful
        """
        try:
            imap = self.connect(username, password)
            imap.select(folder, readonly=False)

            # Mark for deletion
            imap.uid('STORE', str(uid), '+FLAGS', '\\Deleted')

            # Expunge to permanently delete
            imap.expunge()

            imap.close()
            imap.logout()

            logger.info(f"Deleted email UID {uid}")
            return True

        except Exception as e:
            logger.exception(f"Failed to delete email: {str(e)}")
            return False

    def verify_connection(self, username: str, password: str) -> bool:
        """
        Verify IMAP connection and authentication

        Args:
            username: IMAP username
            password: IMAP password

        Returns:
            True if connection successful
        """
        try:
            imap = self.connect(username, password)
            imap.logout()
            logger.info("IMAP connection verified successfully")
            return True

        except Exception as e:
            logger.error(f"IMAP connection verification failed: {str(e)}")
            return False

    @staticmethod
    def _decode_header(header_value):
        """Decode email header"""
        if header_value is None:
            return ""

        decoded = decode_header(header_value)
        header_text = ""

        for text, encoding in decoded:
            if isinstance(text, bytes):
                try:
                    header_text += text.decode(encoding or 'utf-8')
                except:
                    header_text += text.decode('utf-8', errors='ignore')
            else:
                header_text += str(text)

        return header_text

    @staticmethod
    def _get_body(msg):
        """Extract email body"""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                pass

        return body
