"""Optional live F8 + Leaflet browser QA. Run while Vite and F8 are serving."""
import base64
import copy
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


CONTACT = Path('E:/GITHUB/a sih 2026/datasets/drishti_sss_v4/val_clean/images/Contact_105_sslo_png_jpg.rf.4ef20d167e305a8cd5713496355c6f40.jpg')
BACKGROUND = Path('E:/GITHUB/a sih 2026/datasets/drishti_sss_v4/benchmark_bg/images/bg_1693569221.750_x1000.jpg')
OUTPUT = Path('E:/GITHUB/a sih 2026/frontend/phase5-browser-check.png')
TRANSPARENT_TILE = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=')


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
    console_errors, page_errors, http_errors = [], [], []
    page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
    page.on('pageerror', lambda error: page_errors.append(error.stack or str(error)))
    page.on('response', lambda response: http_errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
    page.route('https://tile.openstreetmap.org/**', lambda route: route.fulfill(status=200, content_type='image/png', body=TRANSPARENT_TILE))

    page.goto('http://127.0.0.1:5173/', wait_until='networkidle')
    page.get_by_text('NO ANALYSIS LOADED', exact=True).wait_for()
    assert page.locator('.leaflet-container').count() == 0
    page.locator('input[type=file]').set_input_files(str(CONTACT))
    with page.expect_response(lambda response: response.url.endswith('/analyze'), timeout=180000) as pending:
        page.get_by_role('button', name='Run analysis').click()
    live_response = pending.value
    real = live_response.json()
    page.get_by_text('MAP UNAVAILABLE', exact=True).wait_for()
    assert live_response.status == 200 and len(real['candidates']) == 2
    assert live_response.url.startswith('http://127.0.0.1:8000/')
    assert live_response.headers.get('access-control-allow-origin') == '*'
    assert page.locator('.leaflet-container').count() == 0
    assert page.locator('.candidate-list .geo-row-label.pixel').count() == 2
    assert 'PIXEL_ONLY' in page.locator('.location-state').inner_text()

    geographic = copy.deepcopy(real)
    geographic['analysis_id'] = 'ANL-geographic-browser-fixture'
    for index, candidate in enumerate(geographic['candidates']):
        candidate['localization']['metadata']['status'] = 'GEOGRAPHIC'
        candidate['localization']['metadata']['available_spaces'] = ['IMAGE_PIXEL', 'GEOGRAPHIC']
        candidate['localization']['coordinates']['geographic'] = {'coordinate_system': 'WGS84', 'latitude': 10.123456 + index * .002, 'longitude': 76.123456 + index * .003, 'heading_deg': None}
    geographic['candidates'][0]['decision']['status'] = 'UNKNOWN'
    geographic['candidates'][1]['decision']['status'] = 'REJECT'
    geographic['summary']['review_count'] = 0
    geographic['summary']['rejected_count'] = 1
    geographic['summary']['unknown_count'] = 1

    def load_fixture(payload):
        page.route('**/analyze', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(payload)))
        page.locator('input[type=file]').set_input_files(str(CONTACT))
        page.get_by_role('button', name='Run analysis').click()
        page.get_by_text('ANALYSIS COMPLETE', exact=True).wait_for()
        page.wait_for_timeout(350)
        page.unroute('**/analyze')

    load_fixture(geographic)
    page.locator('.sonar-marker').first.wait_for()
    assert page.locator('.sonar-marker').count() == 2
    assert page.locator('.sonar-marker.status-unknown').count() == 1
    assert page.locator('.sonar-marker.status-reject').count() == 1
    assert page.locator('.sonar-marker.selected').count() == 1
    assert '2 GEOGRAPHIC' in page.locator('.sonar-map-stats').inner_text()
    assert 'TRACK: NOT PROVIDED' in page.locator('.sonar-map-footer').inner_text()
    assert 'GEOGRAPHIC UNCERTAINTY REGION: NOT PROVIDED' in page.locator('.sonar-map-footer').inner_text()
    assert '10.123456' in page.locator('.location-details').inner_text()
    page.locator('.sonar-marker').nth(1).click()
    assert page.locator('.candidate-list tbody tr').nth(1).get_attribute('aria-selected') == 'true'
    assert page.locator('.bbox.is-selected').count() == 1
    assert page.locator('.sonar-marker.selected').count() == 1
    assert '10.125456' in page.locator('.location-details').inner_text()
    page.locator('.candidate-list tbody tr').first.click()
    assert page.locator('.sonar-marker.selected').count() == 1
    assert page.locator('.candidate-list tbody tr').first.get_attribute('aria-selected') == 'true'
    page.locator('.bbox').nth(1).click()
    assert page.locator('.candidate-list tbody tr').nth(1).get_attribute('aria-selected') == 'true'
    page.get_by_role('button', name='Fit candidates').click()
    page.get_by_role('button', name='Zoom map in').click()
    page.get_by_role('button', name='Reset view').click()
    page.get_by_role('button', name='Labels on').click()
    assert page.get_by_role('button', name='Labels off').get_attribute('aria-pressed') == 'false'
    before_review = page.locator('.sonar-marker.status-reject').evaluate('(element) => element.style.transform')
    page.get_by_role('button', name='Confirm target').click()
    page.get_by_placeholder('Add observations…').fill('Human assessment remains separate from location.')
    page.get_by_role('button', name='Save review').click()
    page.get_by_role('button', name='Confirm review').click()
    after_review = page.locator('.sonar-marker.status-reject').evaluate('(element) => element.style.transform')
    assert before_review == after_review
    assert page.locator('.sonar-marker.status-reject').count() == 1
    page.locator('.sonar-marker.status-reject').click()
    assert 'CONFIRMED' in page.locator('.sonar-popup').inner_text()
    assert 'REJECT' in page.locator('.sonar-popup').inner_text()

    for width, height in [(1280, 720), (1440, 900), (1920, 1080), (390, 844)]:
        page.set_viewport_size({'width': width, 'height': height})
        assert page.locator('.sonar-leaflet-map').evaluate('(element) => element.getBoundingClientRect().height') >= 350
        assert page.locator('.sonar-marker').count() == 2
    page.set_viewport_size({'width': 1440, 'height': 900})
    page.screenshot(path=str(OUTPUT), full_page=True)

    mixed = copy.deepcopy(geographic)
    mixed['analysis_id'] = 'ANL-mixed-browser-fixture'
    mixed['candidates'][1]['localization']['metadata']['status'] = 'PIXEL_ONLY'
    mixed['candidates'][1]['localization']['coordinates']['geographic'] = None
    load_fixture(mixed)
    assert page.locator('.sonar-marker').count() == 1
    assert '1 GEOGRAPHIC' in page.locator('.sonar-map-stats').inner_text()
    assert '1 CANDIDATE WITHOUT VALID GEOGRAPHIC LOCATION' in page.locator('.sonar-map-footer').inner_text()
    page.locator('.candidate-list tbody tr').nth(1).click()
    assert 'GEOGRAPHIC POSITION NOT AVAILABLE' in page.locator('.location-details').inner_text()
    assert page.locator('.sonar-marker').count() == 1

    invalid = copy.deepcopy(mixed)
    invalid['analysis_id'] = 'ANL-invalid-browser-fixture'
    invalid['candidates'][0]['localization']['coordinates']['geographic']['latitude'] = 999
    load_fixture(invalid)
    page.get_by_text('LOCATION DATA INVALID', exact=True).first.wait_for()
    assert page.locator('.leaflet-container').count() == 0

    page.locator('input[type=file]').set_input_files(str(BACKGROUND))
    with page.expect_response(lambda response: response.url.endswith('/analyze'), timeout=180000) as pending_background:
        page.get_by_role('button', name='Run analysis').click()
    assert pending_background.value.json()['summary']['candidate_count'] == 0
    page.get_by_text('NO GEOGRAPHIC TARGETS', exact=True).wait_for()
    assert page.locator('.sonar-marker').count() == 0

    assert console_errors == [], console_errors
    assert page_errors == [], page_errors
    assert http_errors == [], http_errors
    normal_console_errors = console_errors.copy()
    normal_page_errors = page_errors.copy()
    normal_http_errors = http_errors.copy()

    page.unroute('https://tile.openstreetmap.org/**')
    page.route('https://tile.openstreetmap.org/**', lambda route: route.abort())
    load_fixture(geographic)
    page.get_by_text('MAP TILES UNAVAILABLE', exact=False).first.wait_for(timeout=15000)
    assert page.locator('.sonar-marker').count() == 2
    assert '10.123456' in page.locator('.location-details').inner_text()

    page.route('**/health', lambda route: route.abort())
    page.reload(wait_until='networkidle')
    page.locator('.top-status').get_by_text('OFFLINE', exact=True).wait_for()
    page.get_by_text('NO ANALYSIS LOADED', exact=True).wait_for()
    print(json.dumps({'real_api_status': live_response.status, 'real_api_cors': live_response.headers.get('access-control-allow-origin'), 'real_candidates': len(real['candidates']), 'geo_fixture_markers': 2, 'mixed_fixture_markers': 1, 'tile_failure_state': 'PASS', 'console_errors_normal': normal_console_errors, 'page_errors_normal': normal_page_errors, 'http_errors_normal': normal_http_errors, 'screenshot': str(OUTPUT)}))
    browser.close()
