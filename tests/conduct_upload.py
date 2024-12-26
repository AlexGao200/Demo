from playwright.sync_api import Playwright, sync_playwright


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://localhost:3000/login")
    page.locator('input[type="password"]').fill("7AoMn4*g#uL$Lt")
    page.locator('input[type="text"]').fill("acacetatest@gmail.com")
    page.get_by_role("button", name="Login").click()
    page.get_by_role("link", name="View Uploads").click()
    page.get_by_role("button", name="Upload").click()
    page.get_by_label("Test First Name's Personal").check()
    page.get_by_role("button", name="Continue").click()
    page.locator("li").filter(has_text="TestDimension2").click()
    page.get_by_role("button", name="TestDimension2").click()
    page.get_by_text("Value2").click()
    page.get_by_role("button", name="Confirm").click()
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Continue").click()
    page.get_by_role("textbox").click()
    page.get_by_role("textbox").set_input_files(
        "30382 V2 LC-04-9000-0001 REVC ATLASPLAN Surgical Technique 1223.pdf"
    )
    page.get_by_role("button", name="Complete").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
