"""Explicit Phase 7 demo-mode Chrome QA. Requires Vite with VITE_DEMO_MODE=true on 5174."""
import json

from playwright.sync_api import sync_playwright


SAMPLES = [('contact-103', 1), ('contact-104', 1), ('contact-105', 2), ('background', 0)]
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/health', lambda route: route.fulfill(status=503, content_type='application/json', body='{}'))
    page.route('**/analyze', lambda route: route.abort())
    page.goto('http://127.0.0.1:5174/', wait_until='networkidle')
    page.get_by_text('DEMO MODE', exact=True).wait_for()
    assert page.get_by_text('BACKEND OFFLINE', exact=True).count() == 0
    assert page.locator('.top-status').get_by_text('OFFLINE').is_visible()
    for sample, count in SAMPLES:
        page.get_by_label('Load demo example').select_option(sample)
        page.get_by_text('DEMO ANALYSIS LOADED').wait_for()
        assert page.locator('.candidate-list tbody tr').count() == count
        assert page.locator('.bbox').count() == count
        assert page.get_by_text('DEMO DATA', exact=True).is_visible()
        assert page.locator('.image-stage img').evaluate('(image) => image.complete && image.naturalWidth > 0')
        page.get_by_role('button', name='View report').click()
        page.get_by_text('MARINE ANOMALY ANALYSIS REPORT').wait_for()
        assert page.locator('.report-candidate').count() == count
        page.get_by_role('button', name='← Analysis').click()
    assert errors == [], errors
    print(json.dumps({'demo_samples': SAMPLES, 'backend_analyze_calls': 0, 'page_errors': errors}))
    browser.close()
