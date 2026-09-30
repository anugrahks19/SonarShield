"""Optional live Phase 6 QA. Run with Vite and F8 on localhost."""
import json
import copy
import base64
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path('E:/GITHUB/a sih 2026/frontend')
CONTACT = Path('E:/GITHUB/a sih 2026/datasets/drishti_sss_v4/val_clean/images/Contact_105_sslo_png_jpg.rf.4ef20d167e305a8cd5713496355c6f40.jpg')
BACKGROUND = Path('E:/GITHUB/a sih 2026/datasets/drishti_sss_v4/benchmark_bg/images/bg_1693569221.750_x1000.jpg')
TRANSPARENT_TILE = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=')

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900}, accept_downloads=True)
    errors = []
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('https://tile.openstreetmap.org/**', lambda route: route.fulfill(status=200, content_type='image/png', body=TRANSPARENT_TILE))
    page.goto('http://127.0.0.1:5173/', wait_until='networkidle')
    page.get_by_role('button', name='Reports').click()
    page.get_by_text('NO ANALYSIS AVAILABLE').wait_for()
    page.get_by_role('button', name='Open analysis').click()
    page.locator('input[type=file]').set_input_files(str(CONTACT))
    with page.expect_response(lambda response: response.url.endswith('/analyze'), timeout=180000) as pending:
        page.get_by_role('button', name='Run analysis').click()
    real = pending.value.json()
    assert pending.value.status == 200 and len(real['candidates']) == 2
    assert pending.value.headers.get('access-control-allow-origin') == '*'
    page.get_by_role('button', name='Confirm target').click()
    page.get_by_placeholder('Add observations…').fill('Human note in report.')
    page.get_by_role('button', name='Save review').click()
    page.get_by_role('button', name='Confirm review').click()
    page.get_by_role('button', name='View report').click()
    page.get_by_text('MARINE ANOMALY ANALYSIS REPORT').wait_for()
    assert page.locator('.report-candidate').count() == 2
    assert page.locator('.report-image-box').count() == 2
    assert 'CONFIRMED' in page.locator('.report-candidate').first.inner_text()
    assert real['candidates'][0]['decision']['status'] in page.locator('.report-candidate').first.inner_text()
    page.get_by_role('button', name='Original', exact=True).click()
    assert page.locator('.report-image-box').count() == 0
    page.get_by_role('button', name='Annotated', exact=True).click()
    assert page.locator('.report-image-box').count() == 2
    with page.expect_response(lambda response: response.url.endswith('/report')) as report_request:
        page.get_by_role('button', name='Request F8 report metadata').click()
    backend_report = report_request.value.json()
    assert report_request.value.status == 200 and backend_report['status'] == 'GENERATED'
    assert 'No downloadable artifact' in page.locator('.report-backend-reference').inner_text()
    with page.expect_download() as download:
        page.get_by_role('button', name='Export JSON').click()
    exported = json.loads(download.value.path().read_text(encoding='utf-8'))
    assert exported['analysis'] == real
    assert exported['human_review']['storage'] == 'LOCAL_BROWSER'
    assert len(exported['human_review']['reviews']) == 1
    with page.expect_download() as download:
        page.get_by_role('button', name='Export CSV').click()
    csv = download.value.path().read_text(encoding='utf-8-sig')
    assert csv.count('\n') == 3 and 'CONFIRMED' in csv
    assert real['candidates'][0]['decision']['status'] in csv
    pdf = ROOT / 'phase6-print-check.pdf'
    page.pdf(path=str(pdf), format='A4', print_background=True)
    page.screenshot(path=str(ROOT / 'phase6-browser-check.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.get_by_role('button', name='Export JSON').is_visible()
    assert page.locator('.report-paper').bounding_box()['width'] <= 390
    page.get_by_role('button', name='← Analysis').click()
    geographic = copy.deepcopy(real)
    geographic['analysis_id'] = 'ANL-phase6-geographic-fixture'
    for index, candidate in enumerate(geographic['candidates']):
        candidate['localization']['metadata']['status'] = 'GEOGRAPHIC'
        candidate['localization']['metadata']['available_spaces'] = ['IMAGE_PIXEL', 'GEOGRAPHIC']
        candidate['localization']['coordinates']['geographic'] = {'coordinate_system': 'WGS84', 'latitude': 10.123456 + index, 'longitude': 76.123456 + index, 'heading_deg': None}
    geographic['candidates'][0]['decision']['status'] = 'UNKNOWN'
    geographic['candidates'][1]['decision']['status'] = 'REJECT'
    geographic['summary']['review_count'] = 0
    geographic['summary']['rejected_count'] = 1
    geographic['summary']['unknown_count'] = 1
    page.route('**/analyze', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(geographic)))
    page.locator('input[type=file]').set_input_files(str(CONTACT))
    page.get_by_role('button', name='Run analysis').click()
    page.get_by_role('button', name='View report').click()
    assert 'UNKNOWN' in page.locator('.report-candidate').first.inner_text()
    assert 'REJECT' in page.locator('.report-candidate').nth(1).inner_text()
    assert '10.123456' in page.locator('.report-location-list').inner_text()
    with page.expect_download() as geo_download:
        page.get_by_role('button', name='Export CSV').click()
    geo_csv = geo_download.value.path().read_text(encoding='utf-8-sig')
    assert '10.123456' in geo_csv and '76.123456' in geo_csv
    page.unroute('**/analyze')
    page.get_by_role('button', name='← Analysis').click()
    page.locator('input[type=file]').set_input_files(str(BACKGROUND))
    with page.expect_response(lambda response: response.url.endswith('/analyze'), timeout=180000) as background:
        page.get_by_role('button', name='Run analysis').click()
    assert background.value.json()['summary']['candidate_count'] == 0
    page.get_by_role('button', name='View report').click()
    page.get_by_text('NO CANDIDATES DETECTED', exact=False).wait_for()
    assert page.locator('.report-candidate').count() == 0
    assert page.locator('#report-provenance').is_visible()
    assert errors == [], errors
    print(json.dumps({'live_candidates': 2, 'zero_candidates': 0, 'backend_report_status': backend_report['status'], 'local_review_exported': True, 'console_errors': errors, 'pdf': str(pdf)}))
    browser.close()
