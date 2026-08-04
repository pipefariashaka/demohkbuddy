import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    context = browser.new_context(viewport={"width":1920,"height":1080})
    page = context.new_page()
    page.goto("https://hakalab.com/")
    page.get_by_role("button", name="Contacto").click()
    page.get_by_role("textbox", name="Ingresa tu nombre").click()
    page.get_by_role("textbox", name="Ingresa tu nombre").fill("Felipe")
    page.get_by_role("textbox", name="Ingresa tu empresa").click()
    page.get_by_role("textbox", name="Ingresa tu empresa").fill("Haka")
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
