"""Live Phase 7 Chrome QA. Requires F8 on 8000 and Vite on 5173."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path('E:/GITHUB/a sih 2026')
BASE = os.environ.get('PHASE8_FRONTEND_URL', 'http://127.0.0.1:5173').rstrip('/')
OUTPUT = Path('C:/Users/USER/.codex/worktrees/5a69/a sih 2026/frontend')
CONTACTS = [
    ROOT / 'datasets/drishti_sss_v4/val_clean/images/Contact_103_sslo_png_jpg.rf.53fe66a3739b5f18e390901f89cf481e.jpg',
    ROOT / 'datasets/drishti_sss_v4/val_clean/images/Contact_104_sslo_png_jpg.rf.22e4adfcabfab6cc53f6c4ec51d4099d.jpg',
    ROOT / 'datasets/drishti_sss_v4/val_clean/images/Contact_105_sslo_png_jpg.rf.4ef20d167e305a8cd5713496355c6f40.jpg',
]
BACKGROUND = ROOT / 'datasets/drishti_sss_v4/benchmark_bg/images/bg_1693569221.750_x1000.jpg'
SIZES = [(1280, 720), (1440, 900), (1920, 1080), (1024, 768), (768, 1024), (390, 844)]


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900}, accept_downloads=True)
    console_errors, page_errors = [], []
    page.on('console', lambda item: console_errors.append(item.text) if item.type == 'error' else None)
    page.on('pageerror', lambda error: page_errors.append(str(error)))
    page.goto(f'{BASE}/', wait_until='networkidle')
    assert page.get_by_role('heading', name='Sonar analysis', exact=True).is_visible()
    assert page.get_by_text('DEMO MODE', exact=True).count() == 0
    assert page.get_by_role('button', name='Open navigation').count() == 0
    page.get_by_role('button', name='Overview').click()
    assert page.url.endswith('/overview') and page.get_by_role('heading', name='Mission status').is_visible()
    page.get_by_role('button', name='System').click()
    assert page.url.endswith('/system') and page.get_by_role('heading', name='Service status').is_visible()
    page.get_by_role('button', name='Analysis', exact=True).click()

    counts = []
    for source in CONTACTS:
        page.locator('input[type=file]').set_input_files(str(source))
        with page.expect_response(lambda response: response.url.endswith('/analyze'), timeout=180000) as pending:
            page.get_by_role('button', name='Run analysis').click()
        response = pending.value
        assert response.status == 200 and response.headers.get('access-control-allow-origin') == '*'
        payload = response.json()
        counts.append(payload['summary']['candidate_count'])
        assert page.locator('.candidate-list tbody tr').count() == len(payload['candidates'])
        assert page.locator('.bbox').count() == len(payload['candidates'])
        assert page.locator('.sonar-marker').count() == 0
        assert 'PIXEL_ONLY' in page.locator('.location-state').inner_text()
        assert page.locator('.candidate-hero').get_by_text(payload['candidates'][0]['detection']['class_name']).is_visible()

    assert counts == [1, 1, 2], counts
    assert page.get_by_role('button', name='Next candidate').is_enabled()
    page.locator('.page-intro h1').click()
    page.keyboard.press('ArrowRight')
    assert page.locator('.candidate-list tbody tr').nth(1).get_attribute('aria-selected') == 'true'
    page.keyboard.press('ArrowLeft')
    assert page.locator('.candidate-list tbody tr').first.get_attribute('aria-selected') == 'true'
    page.get_by_role('button', name='Next candidate').click()
    assert page.locator('.candidate-list tbody tr').nth(1).get_attribute('aria-selected') == 'true'
    page.get_by_role('button', name='Confirm target').click()
    page.get_by_placeholder('Add observations…').fill('Phase 7 browser review.')
    page.get_by_role('button', name='Save review').click()
    page.get_by_role('button', name='Confirm review').click()
    page.get_by_text('Review saved locally.', exact=True).wait_for()
    assert page.locator('.review-summary progress').get_attribute('value') == '1'
    page.get_by_role('button', name='View report').click()
    assert '/reports/' in page.url
    page.locator('.report-candidate').first.wait_for()
    assert page.locator('.report-candidate').count() == 2
    assert 'Phase 7 browser review.' in page.locator('.report-candidate').nth(1).inner_text()
    assert payload['candidates'][1]['decision']['status'] in page.locator('.report-candidate').nth(1).inner_text()
    page.screenshot(path=str(OUTPUT / 'phase7-report.png'), full_page=True)
    page.get_by_role('button', name='← Analysis').click()

    overflow = []
    for width, height in SIZES:
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(150)
        dimensions = page.evaluate('({body:document.body.scrollWidth,viewport:window.innerWidth,viewer:document.querySelector(".viewer-canvas").getBoundingClientRect().height})')
        if dimensions['body'] > dimensions['viewport'] + 1:
            overflow.append((width, dimensions['body']))
        assert dimensions['viewer'] >= 340
        if width == 390:
            assert page.get_by_role('button', name='Open navigation').is_visible()
            page.get_by_role('button', name='Open navigation').click()
            assert page.get_by_role('button', name='Reports').is_visible()
            page.get_by_role('button', name='Close navigation').click()
            page.screenshot(path=str(OUTPUT / 'phase7-mobile.png'), full_page=True)
        if width == 1440:
            page.screenshot(path=str(OUTPUT / 'phase7-analysis.png'), full_page=True)
    assert not overflow, overflow

    page.set_viewport_size({'width': 1440, 'height': 900})
    page.locator('input[type=file]').set_input_files(str(BACKGROUND))
    with page.expect_response(lambda response: response.url.endswith('/analyze'), timeout=180000) as pending_background:
        page.get_by_role('button', name='Run analysis').click()
    assert pending_background.value.json()['summary']['candidate_count'] == 0
    page.get_by_role('button', name='View report').click()
    assert page.locator('.report-candidate').count() == 0
    page.goto(f'{BASE}/reports/ANL-unavailable', wait_until='networkidle')
    page.get_by_text('NO ANALYSIS AVAILABLE').wait_for()
    page.goto(f'{BASE}/candidates', wait_until='networkidle')
    assert page.get_by_role('heading', name='Sonar analysis', exact=True).is_visible()
    page.goto(f'{BASE}/overview', wait_until='networkidle')
    assert page.get_by_role('heading', name='Mission status').is_visible()
    page.goto(f'{BASE}/system', wait_until='networkidle')
    assert page.get_by_role('heading', name='Service status').is_visible()
    assert console_errors == [], console_errors
    assert page_errors == [], page_errors
    offline = browser.new_page(viewport={'width': 1024, 'height': 768})
    offline.route('**/health', lambda route: route.fulfill(status=503, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'}, body='{}'))
    offline.goto(f'{BASE}/system', wait_until='networkidle')
    offline.get_by_text('BACKEND OFFLINE', exact=True).wait_for()
    assert offline.get_by_role('button', name='Check connection').is_enabled()
    offline.get_by_role('button', name='Analysis', exact=True).click()
    assert offline.get_by_role('heading', name='Sonar analysis', exact=True).is_visible()
    offline.close()
    print(json.dumps({'live_candidate_counts': counts, 'sizes_checked': SIZES, 'horizontal_overflow': overflow, 'offline_ui': 'PASS', 'console_errors': console_errors, 'page_errors': page_errors}))
    browser.close()
