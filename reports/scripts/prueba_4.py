import re
from playwright.sync_api import Playwright, sync_playwright, expect

# Este script navega al portal Hakatools, accede a la sección de formularios y completa los campos de nombre y correo.

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(ignore_https_errors=True, user_agent="Haka2026", viewport={"width":1920,"height":1080})
    page = context.new_page()
    
    # Navegación y selección de formulario
    page.goto("https://hakatools.hakalab.com/hakatools")
    page.locator("#menuGoForms").get_by_text("Formularios").click()
    
    # Completar formulario de usuario
    page.get_by_role("textbox", name="Nombre de usuario").fill("Felipe")
    page.get_by_role("textbox", name="Correo").fill("felipe@gmail.com")

    # Verificación final
    expect(page.get_by_role("textbox", name="Correo")).to_have_value("felipe@gmail.com")

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)