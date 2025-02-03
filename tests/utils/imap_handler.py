
import email
import imaplib
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class IMAP_handler:

    DEFAULT_INBOX = "inbox"

    def __init__(self, email_credentials, imap_url = 'imap.gmail.com'):
        self._mail = imaplib.IMAP4_SSL(imap_url)
        self.credentials = email_credentials

    @property
    def mail(self):
        return self._mail

    def check(self):
        try:
            self.mail.login(self.credentials["address"], self.credentials["pswd"])
        except Exception:
            return False
        
        return True

    def start(self):
        try:
            self.mail.login(self.credentials["address"], self.credentials["pswd"])
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise
        self.mail.select(self.DEFAULT_INBOX, readonly=True)  # Connect to the inbox.

    def close(self):
        self.mail.logout()

    def restart(self):
        self.close()
        time.sleep(1)
        self.start()

    def _refresh_inbox(self):
        self.mail.select(self.DEFAULT_INBOX, readonly=True)

    def count_emails_by_subject(self, subject: str) -> int:
        self._refresh_inbox()
        status, messages = self.mail.search(None, f'SUBJECT "{subject}"')
        if status == 'OK':
            # Convert the message IDs to a list of email IDs
            email_ids = messages[0].split()

            if not email_ids:
                return 0
            else:
                # Fetch the most recent email with the matching subject
                return len(email_ids)
        else:
            raise Exception("Cannot retrieve emails.")

    def get_last_email_by_subject(self, subject: str) -> str:
        self._refresh_inbox()
        status, messages = self.mail.search(None, f'SUBJECT "{subject}"')
        if status == 'OK':
            # Convert the message IDs to a list of email IDs
            email_ids = messages[0].split()

            if not email_ids:
                return None
            else:
                # Fetch the most recent email with the matching subject
                latest_email_id = email_ids[-1]
                status, msg_data = self.mail.fetch(latest_email_id, '(RFC822)')

                if status != 'OK':
                    return None
                else:
                    # Parse the email content
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Extract the email body
                    if not msg.is_multipart():
                        body = msg.get_payload(decode=True).decode()
                    else:
                        body = ""
                        for part in msg.walk():
                            # Parts could be multi-part too. Will implement if blocking.
                            try:
                                body_part = part.get_payload(decode=True).decode()
                                body += body_part
                            except:
                                pass
                    return body
        else:
            raise Exception("Cannot retrieve emails.")