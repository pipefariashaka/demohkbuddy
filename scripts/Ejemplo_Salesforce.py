import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context(ignore_https_errors=True, user_agent="Haka2026", viewport={"width":1920,"height":1080})
    page = context.new_page()
    page.goto("https://ability-customization-9251.lightning.force.com/lightning/page/home")
    page.get_by_role("button", name="Cerrar").click()
    page.get_by_role("link", name="Cuentas").click()
    page.get_by_role("button", name="Nuevo").click()
    page.get_by_role("textbox", name="Nombre de la cuenta").click()
    page.get_by_role("textbox", name="Nombre de la cuenta").fill("Haka lab")
    page.get_by_role("textbox", name="Sitio Web").click()
    page.get_by_role("textbox", name="Sitio Web").fill("www.hakalab.com")
    page.get_by_role("combobox", name="Tipo").click()
    page.get_by_text("Integrador").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
