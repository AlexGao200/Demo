"""
Title: User registration flow with valid inputs

Test steps:

1. Navigate to the login page by clicking on “Login”
2. Navigate to the registration page by clicking on “Registration”
3. Enter valid info (First name, Last name, Email, Username, Password, Confirm password, Organization Sign-up Code (Optional))
4. Check the email inbox for a confirmation email and click the confirmation link.

Expected result: The user is logged in and redirected to the Home page.
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


def test_registration_1(setup_browser):
    driver = setup_browser
    driver.get("http://frontend:3000")  # Accessing the frontend service in Docker

    wait = WebDriverWait(driver, 10)

    login_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//nav[@class='nav-links']/a[text()='Login']")
        )
    )
    login_button.click()

    register_link = driver.find_element(By.XPATH, "//a[text()='Register']")
    register_link.click()

    first_name_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='Enter first name']")
        )
    )
    first_name_input.send_keys("Jane")

    last_name_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='Enter last name']")
        )
    )
    last_name_input.send_keys("Doe")

    email_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
    )
    email_input.send_keys("jane.doe@gmail.com")

    username_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='Enter username']")
        )
    )
    username_input.send_keys("janedoe")

    password_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
    )
    password_input.send_keys("Janedoe123456!")

    confirm_password_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='Confirm password']")
        )
    )
    confirm_password_input.send_keys("Janedoe123456!")

    register_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@type='submit' and text()='Register']")
        )
    )
    register_button.click()

    home_url = "http://frontend:3000"
    wait.until(EC.url_to_be(home_url))  # Wait until the URL matches the home page
    assert (
        driver.current_url == home_url
    ), "User is not redirected to the home page after registration."
