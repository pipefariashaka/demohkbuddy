import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context(ignore_https_errors=True, user_agent="Haka2026", viewport={"width":1920,"height":1080})
    page = context.new_page()
    page.goto("https://hakatools.hakalab.com/hakatools")
    page.locator("#menuGoForms").get_by_text("Formularios").click()
    page.get_by_role("textbox", name="Nombre de usuario").fill("Felipe")
    page.get_by_role("textbox", name="Correo").fill("farias3felipe@gmail.com")
    page.get_by_role("textbox", name="Dirección", exact=True).fill("mi casita")
    page.get_by_role("textbox", name="Dirección permanente").fill("mi casita 2")
    page.get_by_role("button", name="Enviar").click()
    
    expect(page.get_by_text("Resultado Formulario")).to_be_visible()
    
    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)