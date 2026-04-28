import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(ignore_https_errors=True, viewport={"width":1280,"height":720})
    page = context.new_page()
    page.goto("https://hakalab.com/")
    page.get_by_role("link", name="Productos").click()
    page.get_by_role("img", name="Hakabuddy").click()
    page.locator("#productos-button-hakabuddy").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
