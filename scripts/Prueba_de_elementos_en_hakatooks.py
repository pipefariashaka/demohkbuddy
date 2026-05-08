import re
from playwright.sync_api import Playwright, sync_playwright, expect


# Este test navega por varias secciones de HakaTools y edita una entrada en una tabla dinámica.
def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context()
    page = context.new_page()

    # Navegar a la URL inicial
    page.goto("https://hakatools.hakalab.com/hakatools")

    # Navegar a la sección de Elementos
    page.locator("#menuGoElements").get_by_text("Elementos").click()

    # Interactuar con la pestaña Selector de fechas
    page.get_by_role("tab", name="Selector de fechas").click()
    page.locator("#datePicker").get_by_text("14").click()

    # Interactuar con la pestaña CheckBox
    page.get_by_role("tab", name="CheckBox").click()
    page.get_by_role("checkbox", name="Simple checkbox").check()

    # Interactuar con la pestaña Grupo de Botones
    page.get_by_role("tab", name="Grupo de Botones").click()
    page.get_by_text("Segunda opción").click()

    # Interactuar con la pestaña Tablas
    page.get_by_role("tab", name="Tablas").click()
    page.get_by_role("cell", name="Canada").click()

    # Navegar a la sección de Interacciones
    page.get_by_text("Interacciones").click()

    # Interactuar con la pestaña Tabla dinámica
    page.get_by_role("tab", name="Tabla dinámica").click()

    # Editar una entrada en la tabla dinámica
    page.get_by_role("button", name="Editar").first.click()
    # Playwright hace focus automáticamente, dblclick antes de fill es redundante
    page.locator("#inputNameInModal").fill("Diego maradona")
    page.get_by_role("button", name="Agregar").click()

    # --- Verificaciones finales ---
    # Verificar que el nombre editado esté visible en la tabla
    expect(page.get_by_text("Diego maradona")).to_be_visible()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)