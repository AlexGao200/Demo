"""
Title: User login with invalid credentials

Test steps:

1. Navigate to the login page by clicking on “Login”
2. Enter invalid email and password
3. Clicks Login

Expected result: The user is shown an error message and prompted to reenter email/password
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


def test_login_2(setup_browser):
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
    email_input.send_keys("invalid.email@example.com")

    password_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
    )
    password_input.send_keys("1234567")

    login_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@type='submit' and text()='Login']")
        )
    )
    login_button.click()

    assert (
        driver.find_element(
            By.XPATH, "//p[text()='An unexpected error occurred. Please try again.']"
        )
        is not None
    ), "Error message not displayed"  # change the error message
