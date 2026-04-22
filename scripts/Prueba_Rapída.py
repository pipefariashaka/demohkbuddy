import re
from playwright.sync_api import Playwright, sync_playwright, expect

# Este script navega a Correos de Chile, busca ayuda sobre "envío" y verifica el acceso al artículo de retiro de envíos.

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    # Navegación a la página principal
    page.goto("https://www.correos.cl/")

    # Navegar al centro de ayuda
    page.get_by_role("link", name="Ayuda").click()
    
    # Realizar búsqueda de información
    page.get_by_label("Buscar en preguntas frecuentes").fill("envio")
    page.get_by_role("button", name="Buscar").click()
    
    # Seleccionar resultado y verificar contenido esperado
    page.get_by_role("link", name=re.compile("¿Dónde puedo retirar mis enví")).click()
    expect(page.get_by_text("Contáctanos")).to_be_visible()

    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)