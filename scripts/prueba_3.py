import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(ignore_https_errors=True, user_agent="Haka2026", viewport={"width":1920,"height":1080})
    page = context.new_page()
    page.goto("https://hakalab.com/")
    page.get_by_role("link", name="Servicios").click()
    page.get_by_role("link", name="Nosotros").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
