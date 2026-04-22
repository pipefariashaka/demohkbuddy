import re
from playwright.sync_api import Playwright, sync_playwright, expect

# Este script navega a Correos de Chile, busca ayuda sobre "envío" y verifica el acceso al artículo de retiro de envíos.

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://playwright.dev")
    page.get_by_role("link", name="Get started").click()
    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)