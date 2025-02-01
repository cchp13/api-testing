
import json
import logging
from pathlib import Path
import re
import time
import tkinter as tk
from tkinter import messagebox

import pytest
from selenium.webdriver.common.by import By

from tests.conftest import API_KEY_EMAIL_KEY, REQUEST_EMAIL_KEY, fail_with_selenium_screenshot

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


@pytest.fixture()
def wait_until_new_email(email_headers, gmail_imap_object, email_counts_before):
    def _wait_until_new_email(key: str) -> str:
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
    """Ensuring the API Key emails used are the ones triggered during this testing session."""
    email_counts = {}
    for email_type, header_content in email_headers.items():
        email_counts[email_type] = gmail_imap_object.count_emails_by_subject(header_content)
    return email_counts


def test_navigation_to_api_key_generation_page(landing_page, key_generation_page, webdriver_factory):
    """Test the entire API Key generation workflow, from AEMENT data landing page up to API Key storage."""
    ## GIVEN: A webdriver starting at AEMET data landing page.
    driver = webdriver_factory(headless=True)
    driver.get(landing_page)

    ## WHEN: Click on API Key button.
    cards = driver.find_elements(By.CLASS_NAME, "card-block")
    # Get the Menu card which leads to the API Key generation process.
    filtered_card = [card for card in cards if "API Key" in card.text]

    if len(filtered_card) != 1:
        pytest.fail("Cannot identify menu item for API Key generation.")
    
    api_key_menu_button = filtered_card[0].find_element(By.CLASS_NAME, "btn")
    # Ensure button is visible
    api_key_menu_button.location_once_scrolled_into_view
    api_key_menu_button.click()
    
    ## THEN: We land on the API Key generation page.
    if driver.find_element(By.ID, "intro-header-rec").text != "Obtención API Key":
        pytest.fail("Cannot identify Key generation page")

    assert driver.current_url == key_generation_page


def test_API_key_request(
        key_generation_page,
        webdriver_factory,
        email_credentials,
        wait_until_new_email,
        api_key_handler,
        update_key,
    ):
    """
    This is a long workflow for a test. We are keeping it this way because each step of the process heavily relies
    on the previous steps and even if we split the logic in more tests we would have to rely on the order of execution,
    which is definitely worse that having a longer-than-usual test.
    """
    headful_driver = webdriver_factory(headless=False)
    headful_driver.get(key_generation_page)
    headful_driver.find_element(By.ID, "email").send_keys(email_credentials["address"])
    
    # Notify the tester that manual input is required
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Manual input required.", "Go to the Chrome for Testing window, fullfil the captcha, and press 'Ok'. " \
            "Do not click on 'Enviar', do not resize the Window."
    )

    # Destroy the main window after the popup is closed
    root.destroy()

    # Click Enviar to request key
    try:
        headful_driver.find_element(By.ID, "enviar").click()
        headful_driver.find_element(By.XPATH, ".//span[contains(text(),'Su petición ha sido enviada')]")
    except Exception as e:
        fail_with_selenium_screenshot(
            headful_driver,
            "failed-to-send-key-request",
            "Could not verify that API Key was requested.",
            str(e),
        )

    # Close the headful driver.
    headful_driver.close()

    # Wait for first email to be received    
    key_request_confirmation_email = wait_until_new_email(REQUEST_EMAIL_KEY)
    logger.info(f"Key request email: {key_request_confirmation_email}")
    # Regex pattern to extract the href URL
    pattern = r"<a\s+href=['\"]([^'\"]+)['\"][^>]*>\s*Confirmar generación API Key\s*</a>"

    # Search for the pattern in the HTML string
    match = re.search(pattern, key_request_confirmation_email)

    if match:
        href_url = match.group(1)
    else:
        logging.info(f"Email content: {key_request_confirmation_email}")
        pytest.fail("Could not extract key confirmation URL on API Key request first email.")

    driver = webdriver_factory(headless=True)
    driver.get(href_url)
    try:
        driver.find_element(By.XPATH, ".//body[contains(text(),'Su API Key se ha generado correctamente')]")
    except Exception as e:
        fail_with_selenium_screenshot(
            driver,
            "first-api-generation-email-link",
            "Something went wrong while following the link on the first email.",
            str(e),
        )

    API_Key_email = wait_until_new_email(API_KEY_EMAIL_KEY)
    logger.info(f"API Key email: {API_Key_email}")
    assert API_Key_email

    # Regex pattern to extract the content of the textarea
    pattern = r"<textarea[^>]*>(.*?)</textarea>"

    # Search for the textarea content
    match = re.search(pattern, API_Key_email)
    api_key = match.group(1)
    assert api_key

    # Update API Key if requested
    if update_key:
        api_key_handler.update_key(api_key)
    