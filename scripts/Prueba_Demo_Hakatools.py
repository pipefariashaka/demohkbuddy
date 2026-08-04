import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context(viewport={"width":1920,"height":1080})
    page = context.new_page()
    page.goto("https://hakatools.hakalab.com/hakatools")
    page.locator("#menuGoForms").get_by_text("Formularios").click()
    page.get_by_role("tab", name="Formulario completo").click()
    page.get_by_role("textbox", name="Nombre de usuario").click()
    page.get_by_role("textbox", name="Nombre de usuario").fill("Felipe")
    page.get_by_role("textbox", name="Apellido").click()
    page.get_by_role("textbox", name="Apellido").fill("Farías")
    page.get_by_role("textbox", name="Correo").click()
    page.get_by_role("textbox", name="Correo").fill("fariasfelipe@hakalab.com")
    page.get_by_role("radio", name="Femenino").check()
    page.get_by_role("textbox", name="Teléfono").click()
    page.get_by_role("textbox", name="Teléfono").fill("12345678")
    page.get_by_role("textbox", name="Fecha de nacimiento").fill("1986-07-03")
    page.get_by_role("textbox", name="Profesión").click()
    page.get_by_role("textbox", name="Profesión").fill("QA")
    page.get_by_label("Lenguaje favorito").select_option("java")
    page.get_by_role("textbox", name="Comentario").click()
    page.get_by_role("textbox", name="Comentario").fill("Esto es un demo automatizado desde hakabuddy")
    page.get_by_role("button", name="Enviar").click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
