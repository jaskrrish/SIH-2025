import imaplib
import email
import json
import base64
from email.header import decode_header
from datetime import datetime
from typing import List, Dict, Any

from .models import Email


class IMAPClient:
    """
    Handle IMAP email fetching & parsing
    Supports Gmail / Outlook / standard IMAP servers
    """

    # -----------------------------
    # GMAIL & COMMON IMAP FOLDERS
    # -----------------------------
    GMAIL_FOLDERS = {
        "INBOX": "inbox",
        "[Gmail]/Sent Mail": "sent",
        "[Gmail]/Drafts": "draft",
        "[Gmail]/Trash": "trash",
        "[Gmail]/Spam": "spam",
        "[Gmail]/All Mail": "all"
    }

    def __init__(self, account):
        """
        account: EmailAccount model instance
        """
        self.account = account
        self.connection = None

    # -----------------------------
    # CONNECTION MANAGEMENT
    # -----------------------------
    def connect(self) -> bool:
        try:
            if self.account.imap_use_ssl:
                self.connection = imaplib.IMAP4_SSL(
                    self.account.imap_host,
                    self.account.imap_port
                )
            else:
                self.connection = imaplib.IMAP4(
                    self.account.imap_host,
                    self.account.imap_port
                )

            password = self.account.get_app_password()
            self.connection.login(self.account.email, password)
            print("[IMAP] Login successful")
            return True

        except Exception as e:
            raise Exception(f"[IMAP] Connection failed: {str(e)}")

    def disconnect(self):
        try:
            if self.connection:
                self.connection.close()
                self.connection.logout()
        except Exception:
            pass

    # -----------------------------
    # FOLDER HELPERS
    # -----------------------------
    def list_folders(self) -> List[str]:
        """
        Return raw IMAP folder names
        """
        folders = []
        status, data = self.connection.list()
        if status == "OK":
            for line in data:
                parts = line.decode().split(' "/" ')
                if len(parts) == 2:
                    folders.append(parts[1].strip('"'))
        return folders

    def map_folder(self, imap_folder: str) -> str:
        """
        Normalize IMAP folders to frontend labels
        """
        if imap_folder in self.GMAIL_FOLDERS:
            return self.GMAIL_FOLDERS[imap_folder]

        folder_lower = imap_folder.lower()
        if "sent" in folder_lower:
            return "sent"
        if "draft" in folder_lower:
            return "draft"
        if "trash" in folder_lower or "bin" in folder_lower:
            return "trash"
        if "spam" in folder_lower:
            return "spam"
        return "inbox"

    # -----------------------------
    # EMAIL FETCHING
    # -----------------------------
    def fetch_emails(self, folder: str = "INBOX", limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch last N emails from a folder
        """
        self.connection.select(folder)
        status, messages = self.connection.search(None, "ALL")

        if status != "OK":
            return []

        emails = []
        message_numbers = messages[0].split()

        for num in message_numbers[-limit:]:
            _, msg_data = self.connection.fetch(num, "(RFC822)")
            email_message = email.message_from_bytes(msg_data[0][1])

            parsed = self.parse_email(email_message)
            parsed["folder"] = self.map_folder(folder)

            emails.append(parsed)

        return emails

    # -----------------------------
    # EMAIL PARSING
    # -----------------------------
    def parse_email(self, msg: email.message.Message) -> Dict[str, Any]:

        # SUBJECT
        subject, enc = decode_header(msg.get("Subject", ""))[0]
        if isinstance(subject, bytes):
            subject = subject.decode(enc or "utf-8", errors="ignore")

        # SENDER
        from_name, from_email = email.utils.parseaddr(msg.get("From", ""))

        # RECIPIENTS
        to_emails = [a[1] for a in email.utils.getaddresses([msg.get("To", "")])]
        cc_emails = [a[1] for a in email.utils.getaddresses([msg.get("Cc", "")])]

        # BODY
        body_text = ""
        body_html = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disp = str(part.get("Content-Disposition"))

                if "attachment" in disp:
                    continue

                payload = part.get_payload(decode=True)
                if not payload:
                    continue

                if content_type == "text/plain":
                    body_text += payload.decode(errors="ignore")
                elif content_type == "text/html":
                    body_html += payload.decode(errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = payload.decode(errors="ignore")

        # -----------------------------
        # QUTEMAIL / QKD HEADERS
        # -----------------------------
        security_level = msg.get("X-QuteMail-Security-Level")
        is_encrypted = msg.get("X-QuteMail-Encrypted") == "true"

        if is_encrypted and security_level and security_level != "regular":
            body_text = self._decrypt_body(msg, body_text, security_level)

        # DATE
        date_str = msg.get("Date")
        sent_at = (
            email.utils.parsedate_to_datetime(date_str)
            if date_str else datetime.now()
        )

        # MESSAGE-ID
        message_id = msg.get(
            "Message-ID",
            f"<{id(msg)}@local>"
        )

        return {
            "message_id": message_id,
            "subject": subject or "(No Subject)",
            "from_email": from_email,
            "from_name": from_name,
            "to_emails": json.dumps(to_emails),
            "cc_emails": json.dumps(cc_emails),
            "bcc_emails": json.dumps([]),
            "body_text": body_text,
            "body_html": body_html,
            "sent_at": sent_at,
            "is_encrypted": is_encrypted,
        }

    # -----------------------------
    # DECRYPTION HANDLER
    # -----------------------------
    def _decrypt_body(self, msg, body_text: str, security_level: str) -> str:
        try:
            from crypto import router as crypto_router

            decrypt_kwargs = {
                "ciphertext": body_text,
                "requester_sae": self.account.email
            }

            if security_level == "qkd":
                key_id = msg.get("X-QuteMail-Key-ID")
                decrypt_kwargs["key_id"] = key_id

            elif security_level == "aes":
                aes_key = msg.get("X-QuteMail-AES-Key")
                if aes_key:
                    decrypt_kwargs["key_material"] = base64.b64decode(aes_key)

            decrypted = crypto_router.decrypt(
                security_level=security_level,
                **decrypt_kwargs
            )

            print(f"[IMAP] Decrypted ({security_level})")
            return decrypted.decode("utf-8")

        except Exception as e:
            print(f"[IMAP] Decryption failed: {e}")
            return f"[Encrypted message – decryption failed]\n\n{body_text}"
