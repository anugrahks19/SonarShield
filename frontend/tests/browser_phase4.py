"""Optional live browser smoke check. Run while Vite and frozen F8 are serving."""
import json
import copy
from pathlib import Path

from playwright.sync_api import sync_playwright


IMAGE = Path('E:/GITHUB/a sih 2026/datasets/drishti_sss_v4/val_clean/images/Contact_105_sslo_png_jpg.rf.4ef20d167e305a8cd5713496355c6f40.jpg')
SCREENSHOT = Path('E:/GITHUB/a sih 2026/frontend/phase4-browser-check.png')


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900}, device_scale_factor=1)
    console_errors = []
    page_errors = []
    failed_requests = []
    http_errors = []
    page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
    page.on('pageerror', lambda error: page_errors.append(str(error)))
    page.on('requestfailed', lambda request: failed_requests.append(f'{request.url}: {request.failure}'))
    page.on('response', lambda response: http_errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)

    page.goto('http://127.0.0.1:5173/', wait_until='networkidle')
    page.get_by_text('OK', exact=True).first.wait_for(timeout=15000)
    page.locator('input[type=file]').set_input_files(str(IMAGE))
    with page.expect_response(lambda response: response.url.endswith('/analyze'), timeout=180000) as pending:
        page.get_by_role('button', name='Run analysis').click()
    response = pending.value
    payload = response.json()
    page.get_by_text('ANALYSIS COMPLETE', exact=True).wait_for(timeout=15000)
    assert response.status == 200
    assert payload['summary']['candidate_count'] == 2
    assert page.locator('.bbox').count() == 2
    assert page.locator('.candidate-list tbody tr').count() == 2

    def alignment():
        return page.evaluate('''() => {
          const stage = document.querySelector('.image-stage').getBoundingClientRect();
          const box = document.querySelector('.bbox').getBoundingClientRect();
          const image = document.querySelector('.image-stage img').getBoundingClientRect();
          return {stage: {x: stage.x, y: stage.y, width: stage.width, height: stage.height}, box: {x: box.x, y: box.y, width: box.width, height: box.height}, image: {x: image.x, y: image.y, width: image.width, height: image.height}};
        }''')

    def assert_alignment(rects):
        x1, y1, x2, y2 = payload['candidates'][0]['detection']['bbox']
        stage, box, image = rects['stage'], rects['box'], rects['image']
        assert abs(stage['x'] - image['x']) < 1 and abs(stage['y'] - image['y']) < 1
        assert abs(box['x'] - (stage['x'] + stage['width'] * x1 / payload['input']['width'])) < 2
        assert abs(box['y'] - (stage['y'] + stage['height'] * y1 / payload['input']['height'])) < 2
        assert abs(box['width'] - (stage['width'] * (x2 - x1) / payload['input']['width'])) < 2

    assert_alignment(alignment())
    page.get_by_role('button', name='Zoom in').click()
    page.get_by_role('button', name='Zoom in').click()
    page.get_by_role('button', name='Zoom in').click()
    assert_alignment(alignment())
    page.locator('.viewer-canvas').hover()
    box_before_pan = alignment()['box']['x']
    page.mouse.move(500, 450)
    page.mouse.down()
    page.mouse.move(560, 475)
    page.mouse.up()
    assert_alignment(alignment())
    print('pan_delta_x', round(alignment()['box']['x'] - box_before_pan, 1))

    page.get_by_role('button', name='Confirm target').click()
    page.get_by_placeholder('Add observations…').fill('Confirmed after visual inspection.')
    page.get_by_role('button', name='Save review').click()
    page.get_by_role('dialog').get_by_text(payload['candidates'][0]['decision']['status'], exact=True).wait_for()
    page.get_by_role('button', name='Confirm review').click()
    assert '1 / 2 REVIEWED' in page.locator('.review-progress-line').inner_text()
    page.get_by_role('button', name='Next →').click()
    page.get_by_role('button', name='False positive', exact=True).click()
    page.get_by_placeholder('Add observations…').fill('Likely seabed return.')
    page.get_by_role('button', name='Save review').click()
    page.get_by_role('button', name='Confirm review').click()
    assert '2 / 2 REVIEWED' in page.locator('.review-progress-line').inner_text()
    assert 'REVIEW COMPLETE' in page.locator('.review-progress-line').inner_text()
    page.get_by_role('button', name='← Previous').click()
    assert 'Confirmed after visual inspection.' in page.get_by_placeholder('Add observations…').input_value()
    assert payload['candidates'][0]['decision']['status'] == 'REVIEW'
    page.screenshot(path=str(SCREENSHOT), full_page=True)

    page.reload(wait_until='networkidle')
    page.route('**/analyze', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(payload)))
    page.locator('input[type=file]').set_input_files(str(IMAGE))
    page.get_by_role('button', name='Run analysis').click()
    page.get_by_text('ANALYSIS COMPLETE', exact=True).wait_for()
    assert '2 / 2 REVIEWED' in page.locator('.review-progress-line').inner_text()
    assert page.get_by_placeholder('Add observations…').input_value() == 'Confirmed after visual inspection.'
    assert page.locator('.candidate-list tbody tr').count() == 2
    page.unroute('**/analyze')

    page.get_by_role('button', name='Reset review').click()
    page.get_by_role('dialog').get_by_role('button', name='Reset review').click()
    assert '1 / 2 REVIEWED' in page.locator('.review-progress-line').inner_text()
    assert page.get_by_placeholder('Add observations…').input_value() == ''
    assert payload['candidates'][0]['decision']['status'] == 'REVIEW'

    background = Path('E:/GITHUB/a sih 2026/datasets/drishti_sss_v4/benchmark_bg/images/bg_1693569221.750_x1000.jpg')
    page.locator('input[type=file]').set_input_files(str(background))
    with page.expect_response(lambda result: result.url.endswith('/analyze'), timeout=180000) as pending_background:
        page.get_by_role('button', name='Run analysis').click()
    background_response = pending_background.value.json()
    assert background_response['summary']['candidate_count'] == 0
    page.get_by_text('NO CANDIDATES TO REVIEW', exact=True).wait_for()
    assert page.locator('.bbox').count() == 0
    assert page.locator('.review-summary').count() == 1

    single = Path('E:/GITHUB/a sih 2026/datasets/drishti_sss_v4/val_clean/images/Contact_103_sslo_png_jpg.rf.53fe66a3739b5f18e390901f89cf481e.jpg')
    page.locator('input[type=file]').set_input_files(str(single))
    with page.expect_response(lambda result: result.url.endswith('/analyze'), timeout=180000) as pending_single:
        page.get_by_role('button', name='Run analysis').click()
    assert pending_single.value.json()['summary']['candidate_count'] == 1
    assert page.locator('.candidate-list tbody tr').count() == 1
    assert page.locator('.review-progress-line').inner_text().startswith('0 / 1 REVIEWED')

    synthetic = copy.deepcopy(payload)
    synthetic['analysis_id'] = 'ANL-three-candidate-browser-qa'
    synthetic['candidates'][1]['decision']['status'] = 'REJECT'
    third = copy.deepcopy(payload['candidates'][0])
    third['candidate_id'] = 'CAND-third-browser-qa'
    third['provenance']['candidate_id'] = third['candidate_id']
    third['decision']['status'] = 'UNKNOWN'
    third['detection']['bbox'] = [coordinate + 100 for coordinate in third['detection']['bbox']]
    synthetic['candidates'].append(third)
    synthetic['summary']['candidate_count'] = 3
    page.route('**/analyze', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(synthetic)))
    page.locator('input[type=file]').set_input_files(str(IMAGE))
    page.get_by_role('button', name='Run analysis').click()
    page.get_by_text('ANALYSIS COMPLETE', exact=True).wait_for()
    assert page.locator('.candidate-list tbody tr').count() == 3
    assert page.locator('.bbox').count() == 3
    page.get_by_role('group', name='Filter AI decisions').get_by_role('button', name='REJECT').click()
    assert page.locator('.candidate-list tbody tr').count() == 1
    page.get_by_role('group', name='Filter AI decisions').get_by_role('button', name='ALL').click()
    page.locator('.candidate-list tbody tr').nth(2).click()
    assert page.locator('.candidate-hero .badge').inner_text() == 'UNKNOWN'
    page.get_by_role('button', name='Needs investigation', exact=True).click()
    page.get_by_placeholder('Add observations…').fill('Check adjacent passes.')
    page.get_by_role('button', name='Save review').click()
    page.get_by_role('button', name='Confirm review').click()
    assert page.locator('.candidate-hero .badge').inner_text() == 'UNKNOWN'
    assert page.locator('.review-progress-line').inner_text().startswith('1 / 3 REVIEWED')

    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.locator('.workspace').evaluate('(element) => getComputedStyle(element).gridTemplateColumns.split(" ").length') == 1
    page.screenshot(path=str(SCREENSHOT.with_name('phase4-browser-mobile.png')), full_page=True)
    print(json.dumps({'http_status': response.status, 'analysis_id': payload['analysis_id'], 'candidates': len(payload['candidates']), 'direct_api_url': response.url, 'cors_allow_origin': response.headers.get('access-control-allow-origin'), 'console_errors': console_errors, 'page_errors': page_errors, 'http_errors': http_errors, 'failed_requests': failed_requests, 'screenshot': str(SCREENSHOT)}))
    browser.close()
