"""
Title: User upload with valid document format

Test steps:

1. Navigate to the library page by clicking on “View Uploads”
2. Click on “Upload” to upload file
3. Choose a file with valid format (word, pdf)

Expected result: The user successfully uploaded the document, and it shows up in the library.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@pytest.fixture(scope="module")
def setup_browser():
    # Set up the Selenium Chrome WebDriver to connect to the Selenium server
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # Optional: Run in headless mode (without opening a browser window)
    driver = webdriver.Remote(
        command_executor="http://selenium:4444/wd/hub", options=options
    )

    yield driver  # This will run the test using the driver

    driver.quit()  # Clean up after tests


def test_upload_1(setup_browser):
    driver = setup_browser
    driver.get("http://frontend:3000")  # Accessing the frontend service in Docker

    wait = WebDriverWait(driver, 10)

    login_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//nav[@class='nav-links']/a[text()='Login']")
        )
    )
    login_button.click()

    email_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='text']"))
    )
    email_input.send_keys("janedoe@gmail.com")

    password_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
    )
    password_input.send_keys("JaneDoe1234!")

    login_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@type='submit' and text()='Login']")
        )
    )
    login_button.click()

    home_url = "http://frontend:3000"
    wait.until(EC.url_to_be(home_url))  # Wait until the URL matches the home page
    assert (
        driver.current_url == home_url
    ), "User is not redirected to the home page after login"

    view_uploads_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//a[text()='View Uploads']"))
    )
    view_uploads_button.click()

    upload_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@type='button' and text()='Upload']")
        )
    )
    upload_button.click()

    # upload a pdf doc
