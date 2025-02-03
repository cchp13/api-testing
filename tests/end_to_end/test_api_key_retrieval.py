
import logging
import re
import time
import tkinter as tk
from tkinter import messagebox

import pytest
from selenium.webdriver.common.by import By

from tests.conftest import API_KEY_EMAIL_KEY, REQUEST_EMAIL_KEY, save_selenium_screenshot

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@pytest.fixture()
def wait_until_new_email(email_headers, gmail_imap_object, email_counts_before):
    def _wait_until_new_email(key: str) -> str:
        """Wait until a new email with the given header is found on the inbox."""
        n = 0
        N = 100
        target_header = email_headers[key]
        target_count = email_counts_before[key] + 1
        email_received = False
        while (not email_received) and n<N:
            email_received = gmail_imap_object.count_emails_by_subject(target_header) == target_count
            n += 1
            time.sleep(1)
        
        return gmail_imap_object.get_last_email_by_subject(target_header)

    return _wait_until_new_email

@pytest.fixture(scope="session", autouse=True)
def email_counts_before(gmail_imap_object, email_headers):
    """Before the tests begin, count the amount of emails matching each target header."""
    email_counts = {}
    for email_type, header_content in email_headers.items():
        email_counts[email_type] = gmail_imap_object.count_emails_by_subject(header_content)
    return email_counts


def test_navigation_to_api_key_generation_page(landing_page, key_generation_page, webdriver_factory):
    """Test that the provided AEMET landing page includes a functional link to the API request page."""
    ## GIVEN: A webdriver starting at AEMET data landing page.
    driver = webdriver_factory(headless=True)
    logger.info(f"Selenium webdriver getting {landing_page["url"]}")
    driver.get(landing_page["url"])

    ## WHEN: Clicking on API Key button.
    cards = driver.find_elements(By.CLASS_NAME, "card-block")
    # Get the Menu card which leads to the API Key generation process.
    filtered_card = [card for card in cards if "API Key" in card.text]

    if len(filtered_card) != 1:
        logger.error(f"Found {len(filtered_card)} menu cards matching description.")
        pytest.fail("Cannot identify menu item for API Key generation.")
    
    api_key_menu_button = filtered_card[0].find_element(By.CLASS_NAME, "btn")
    # Ensure button is visible
    api_key_menu_button.location_once_scrolled_into_view

    logger.info(f"Selenium webdriver clicking on API Key menu button.")
    api_key_menu_button.click()
    
    ## THEN: We land on the API Key generation page.
    assert driver.find_element(By.ID, "intro-header-rec").text == key_generation_page["text"]
    assert driver.current_url == key_generation_page["url"]


def test_API_key_request(
        key_generation_page,
        webdriver_factory,
        email_credentials,
        wait_until_new_email,
        api_key_handler,
    ):
    """
    This test encompasses the rest of the API key generation process. Although it involves multiple different
    operations, from captcha to email parsing, splitting the logic into smaller tests would make us need to
    rely on the order of execution, which is definitely worse that having a longer-than-usual test.
    """
    # Open a 'headful' webdriver starting at the API Key request page.
    headful_driver = webdriver_factory(headless=False)
    logger.info(f"Selenium webdriver getting {key_generation_page["url"]}")
    headful_driver.get(key_generation_page["url"])
    logger.info(f"Input email {email_credentials["address"]} into the form.")
    headful_driver.find_element(By.ID, "email").send_keys(email_credentials["address"])
    
    # Notify the tester that manual input is required
    root = tk.Tk()
    root.withdraw()
    logger.info(f"Awaiting user input for Captcha.")
    messagebox.showinfo(
        "Manual input required.", "Go to the Chrome for Testing window, fullfil the captcha, and press 'Ok'. " \
            "Do not click on 'Enviar', do not resize the Window."
    )

    # Destroy the main window after the popup is closed
    root.destroy()

    # Click Enviar to request key
    logger.info("Trying to send key request.")
    try:
        headful_driver.find_element(By.ID, "enviar").click()
        headful_driver.find_element(By.XPATH, ".//span[contains(text(),'Su petición ha sido enviada')]")
        logger.info("Key request acknowledged.")
    except Exception as e:
        screenshot_path = save_selenium_screenshot(
            headful_driver,
            "failed-to-send-key-request",
        )
        logger.warning("Could not verify that API Key was successfully requested.")
        logger.warning(f"Exception message: {str(e)}")
        logger.warning(f"Inspect screenshot {screenshot_path} for more information.")


    # Close the headful driver.
    logger.info("Closing headful driver")
    headful_driver.close()

    # Wait for first email to be received
    logger.info(f"Waiting for API Key request confirmation email.")
    key_request_confirmation_email = wait_until_new_email(REQUEST_EMAIL_KEY)
    logger.info(f"Key request email: {key_request_confirmation_email}")
    # Regex pattern to extract the href URL
    pattern = r"<a\s+href=['\"]([^'\"]+)['\"][^>]*>\s*Confirmar generación API Key\s*</a>"

    # Search for the pattern in the HTML string
    match = re.search(pattern, key_request_confirmation_email)

    if match:
        href_url = match.group(1)
        logging.info(f"API Key confirmation url parsed from email: {href_url}")
    else:
        logging.error(f"url could not be parsed from API Key confirmation email.")
        pytest.fail("Could not extract key confirmation URL on API Key request first email.")

    logging.info("Starting headless webdriver for API Key retrieval.")
    driver = webdriver_factory(headless=True)

    logger.info(f"Selenium webdriver getting {href_url}")
    driver.get(href_url)
    try:
        driver.find_element(By.XPATH, ".//body[contains(text(),'Su API Key se ha generado correctamente')]")
        logger.info("Key request confirmation acknowledged.")
    except Exception as e:
        screenshot_path = save_selenium_screenshot(
            driver,
            "api-generation-email-link",
        )
        logger.warning("Something went wrong while following the link on the first email.")
        logger.warning(f"Exception message: {str(e)}")
        logger.warning(f"Inspect screenshot {screenshot_path} for more information.")


    logger.info(f"Waiting for email containing API Key.")
    API_Key_email = wait_until_new_email(API_KEY_EMAIL_KEY)
    logger.info(f"API Key email: {API_Key_email}")
    assert API_Key_email

    # Regex pattern to extract the content of the textarea
    pattern = r"<textarea[^>]*>(.*?)</textarea>"

    # Search for the textarea content
    match = re.search(pattern, API_Key_email)

    if match:
        api_key = match.group(1)
        # I would not log the key for security concerns.
        logging.info(f"API Key successfully parsed from email.")
    else:
        logging.error(f"API Key could not be parsed from API Key email.")
        pytest.fail("Could not extract API Key from the email.")

    assert api_key

    # Update API Key
    api_key_handler.update_key(api_key)
    