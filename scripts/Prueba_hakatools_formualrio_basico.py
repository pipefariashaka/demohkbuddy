# Este script navega a Hakatools, completa el formulario de contacto y envía los datos.

import re
from playwright.sync_api import Playwright, sync_playwright, expect

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context()
    page = context.new_page()

    # Navegación y acceso al formulario
    page.goto("https://hakatools.hakalab.com/hakatools")
    page.locator("#menuGoForms").get_by_text("Formularios").click()

    # Rellenar formulario
    page.get_by_role("textbox", name="Nombre de usuario").fill("Felipe")
    page.get_by_role("textbox", name="Correo").fill("felipe@hakalab.com")
    page.get_by_role("textbox", name="Dirección", exact=True).fill("mi casita")
    page.get_by_role("textbox", name="Dirección permanente").fill("mi casita 2")
    
    # Envío del formulario
    page.get_by_role("button", name="Enviar").click()

    
    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)