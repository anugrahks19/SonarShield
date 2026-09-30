"""Browser smoke test for the deployed Gradio Space from a local production preview."""
import json
import os
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright


BASE = os.environ.get('FRONTEND_PREVIEW_URL', 'http://127.0.0.1:4175').rstrip('/')
IMAGE = Path(__file__).resolve().parents[1] / 'public/contact-105.jpg'

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    console_errors, page_errors = [], []
    page.on('console', lambda item: console_errors.append(item.text) if item.type == 'error' else None)
    page.on('pageerror', lambda error: page_errors.append(str(error)))
    page.goto(BASE + '/analysis', wait_until='domcontentloaded')
    page.get_by_role('heading', name='Sonar analysis', exact=True).wait_for()
    page.locator('input[type=file]').set_input_files(str(IMAGE))
    page.get_by_role('button', name='Run analysis').click()
    try:
        page.locator('.candidate-list tbody tr').first.wait_for(timeout=120000)
        print(json.dumps({
            'status': 'PASS',
            'candidates': page.locator('.candidate-list tbody tr').count(),
            'boxes': page.locator('.bbox').count(),
            'console_errors': console_errors,
            'page_errors': page_errors,
        }))
    except PlaywrightTimeout:
        print(json.dumps({
            'status': 'FAIL',
            'banner': page.locator('[role=alert]').all_inner_texts(),
            'console_errors': console_errors,
            'page_errors': page_errors,
        }))
        raise
    finally:
        browser.close()
