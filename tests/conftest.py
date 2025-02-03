
from copy import deepcopy
import json
import logging
from pathlib import Path
import pytest

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from setup_env import SECRETS

from tests.utils.api_key_handler import ApiKeyHandler
from tests.utils.imap_handler import IMAP_handler


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        "--allow-missing-datapoints",
        action="store_true",
        default=False,
        help="Whether to pass a test in which the data series retrieved is not exhaustive.",
    )


@pytest.fixture(scope="session")
def request_cap_wait(request):
    return int(request.config.getoption("--wait-for-capacity"))


@pytest.fixture(scope="session")
def allow_missing_datapoints(request):
    return bool(request.config.getoption("--allow-missing-datapoints"))


# ============================================== AEMET ==============================================


@pytest.fixture(scope="session")
def landing_page():
    return {
        "url": "https://opendata.aemet.es/centrodedescargas/inicio",
    }

@pytest.fixture(scope="session")
def key_generation_page():
    return {
        "url": "https://opendata.aemet.es/centrodedescargas/altaUsuario?",
        "text": "Obtención API Key",
    }


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
def antartida_api_endpoint():
    def _url(base_api, start_date, end_date, station):
        return f"{base_api}/antartida/datos/fechaini/{start_date}/fechafin/{end_date}/estacion/{station}"

    return _url

@pytest.fixture(scope="session")
def date_format():
    def _format(time_zone):
        return f"%Y-%m-%dT%H:%M:%S{time_zone}"
    
    return _format

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


# ============================================== API Key =============================================


@pytest.fixture(scope="session")
def api_key_handler():

    return ApiKeyHandler(SECRETS[API_KEY_FILE_NAME], API_KEY_JSON_KEY)


# ============================================== Email ==============================================

@pytest.fixture(scope="session")
def email_credentials() -> dict[str, str]:
    email_credentials_file = SECRETS[EMAIL_FILE_NAME]
    return json.loads(email_credentials_file.read_text())


@pytest.fixture(scope="session")
def gmail_imap_object(email_credentials):

    IMAP_object = IMAP_handler(email_credentials=email_credentials)         
    IMAP_object.start()

    return IMAP_object

# ============================================== Selenium ==============================================

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


def save_selenium_screenshot(driver: WebDriver, screenshot_name: str):
    screenshot = (Path("debug") / screenshot_name).with_suffix(".png")
    driver.save_screenshot(screenshot)
    return screenshot.as_posix()