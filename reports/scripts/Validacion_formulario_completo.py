import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context(ignore_https_errors=True, user_agent="Haka2026", viewport={"width":1920,"height":1080})
    page = context.new_page()
    page.goto("https://hakatools.hakalab.com/hakatools")
    page.locator("#menuGoInteractions").get_by_text("Interacciones").click()
    page.get_by_role("tab", name="Lista seleccionable").click()
    page.get_by_label("Lista seleccionable").get_by_text("Episode I - The Phantom Menace").click()
    page.get_by_role("button", name="No seleccionar ninguno").click()
    page.get_by_role("tab", name="Arrastrar y soltar").click()
    page.get_by_role("tab", name="Tabla dinámica").click()
    page.get_by_role("button", name="Editar").first.click()
    page.locator("#inputNameInModal").dblclick()
    page.locator("#inputNameInModal").click()
    page.locator("#inputNameInModal").dblclick()
    page.locator("#inputNameInModal").fill("Diego Maradona")
    page.get_by_role("button", name="Agregar").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
