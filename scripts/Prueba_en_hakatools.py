import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context(viewport={"width":1920,"height":1080})
    page = context.new_page()
    page.goto("https://hakatools.hakalab.com/hakatools")
    page.locator("#menuGoForms").get_by_text("Formularios").click()
    page.get_by_role("textbox", name="Nombre de usuario").click()
    page.get_by_role("textbox", name="Nombre de usuario").fill("Juani")
    page.get_by_role("textbox", name="Correo").click()
    page.get_by_role("textbox", name="Correo").fill("juani@hakalab.com")
    page.get_by_role("textbox", name="Dirección", exact=True).click()
    page.get_by_role("textbox", name="Dirección", exact=True).fill("mi casita")
    page.get_by_role("button", name="Enviar").click()


    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)