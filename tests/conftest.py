
from copy import deepcopy
import email
import imaplib
import json
import logging
from pathlib import Path
import pytest
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from setup_env import SECRETS

from tests.utils.utils import ApiKeyHandler

# ============================================== Constants ==============================================

# Email dict keys
REQUEST_EMAIL_KEY = "request"
API_KEY_EMAIL_KEY = "key"

# Secrets dict keys
EMAIL_FILE_NAME = "email_credentials"
API_KEY_FILE_NAME = "api_key"
API_KEY_JSON_KEY = "api_key"

# ============================================== Options ==============================================

def pytest_addoption(parser):
    parser.addoption(
        "--wait-for-capacity",
        action="store",
        default=5,
        help="Wait given minutes for the request cap to refresh.",
    )
    parser.addoption(
        "--update-api-key",
        action="store_true",
        default=False,
        help="Whether to update the key locally stored with the outcome of the key retrieval test.",
    )

# ============================================== Fixtures ==============================================
# AEMET

@pytest.fixture(scope="session")
def landing_page():
    return "https://opendata.aemet.es/centrodedescargas/inicio"

@pytest.fixture(scope="session")
def key_generation_page():
    return "https://opendata.aemet.es/centrodedescargas/altaUsuario?"

@pytest.fixture(scope="session")
def email_headers():
    return {
        REQUEST_EMAIL_KEY: "API Key servicio AEMET OpenData",
        API_KEY_EMAIL_KEY: "Alta en el servicio AEMET OpenData",
    }

@pytest.fixture(scope="session")
def base_api_url():
    return "https://opendata.aemet.es/opendata/api"

@pytest.fixture(scope="session")
def data_point_structure():
    return {
        'rec',
        'ins',
        'ttierra',
        'tsmx',
        'albedo',
        'latitud',
        'altitud',
        'dddx',
        'uvi',
        'tsb',
        'nombre',
        'longitud',
        'srs',
        'rad_kj_m2',
        'tsmn',
        'alt_nieve',
        'vel',
        'fhora',
        'temp',
        'lluv',
        'tcielo',
        'identificacion',
        'dddstd',
        'difusa',
        'tmn',
        'pres',
        'par',
        'hr',
        'ts',
        'neta',
        'uvb',
        'uvab',
        'qdato',
        'ir_solar',
        'global',
        'velx',
        'directa',
        'rad_w_m2',
        'ddd',
        'tmx'
    }

@pytest.fixture(scope="session")
def request_cap_wait(request):
    return int(request.config.getoption("--wait-for-capacity"))

@pytest.fixture(scope="session")
def update_key(request):
    return bool(request.config.getoption("--update-api-key"))

@pytest.fixture(scope="session")
def api_key_handler():

    return ApiKeyHandler(SECRETS[API_KEY_FILE_NAME], API_KEY_JSON_KEY)


# Email service

@pytest.fixture(scope="session")
def email_credentials() -> dict[str, str]:
    email_credentials_file = SECRETS[EMAIL_FILE_NAME]
    return json.loads(email_credentials_file.read_text())


@pytest.fixture(scope="session")
def gmail_imap_object(email_credentials):

    class IMAP_handler:

        DEFAULT_INBOX = "inbox"

        def __init__(self, email_credentials = email_credentials, imap_url = 'imap.gmail.com'):
            self._mail = imaplib.IMAP4_SSL(imap_url)
            self.credentials = email_credentials

        @property
        def mail(self):
            return self._mail

        def start(self):
            try:
                self.mail.login(self.credentials["address"], self.credentials["pswd"])
            except Exception as e:
                logging.error(f"Login failed: {str(e)}")
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
                raise Exception("Cannot retrive emails.")

    IMAP_object = IMAP_handler(email_credentials=email_credentials)         
    IMAP_object.start()

    return IMAP_object

# Selenium

@pytest.fixture(scope="session")
def webdriver_options():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,800")
    chrome_options.add_argument("--allow-insecure-localhost")
    return chrome_options


@pytest.fixture()
def webdriver_factory(webdriver_options):
    
    drivers = []
    
    def _get_selenium_webdriver(headless = True):
        options = deepcopy(webdriver_options)
        if headless:
            options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        drivers.append(driver)
        return driver

    yield _get_selenium_webdriver

    for driver in drivers:
        try:
            driver.close()
        except:
            pass


def fail_with_selenium_screenshot(driver: WebDriver, screenshot_name: str, description: str, exception_msg: str):
    screenshot = (Path("debug") / screenshot_name).with_suffix(".png")
    driver.save_screenshot(screenshot)
    pytest.fail(
        (
        f"{description} \n"
        f"Error message: {exception_msg} \n"
        f"Inspect screenshot {screenshot.as_posix()} for more information."
        )
    )