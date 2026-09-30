"""Mock Gradio quota and success responses without spending ZeroGPU quota.

Requires local production preview on port 4182.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = json.loads((ROOT / 'public/contact-105.json').read_text(encoding='utf-8'))
IMAGE = ROOT / 'public/contact-105.jpg'
MOCK = 'https://mock.hf.space'
CONFIG = {
    'root': MOCK, 'protocol': 'sse', 'enable_queue': False, 'run_history': False,
    'app_id': 'judge-mock', 'components': [
        {'id': 1, 'type': 'image', 'props': {}},
        {'id': 2, 'type': 'checkbox', 'props': {}},
        {'id': 3, 'type': 'json', 'props': {}},
    ],
    'dependencies': [{'id': 0, 'api_name': 'analyze_image_gradio', 'inputs': [1, 2],
                      'outputs': [3], 'queue': False, 'api_visibility': 'public',
                      'types': {'generator': False}}],
}
API = {'named_endpoints': {'/analyze_image_gradio': {
    'parameters': [
        {'parameter_name': 'image_filepath', 'parameter_has_default': False, 'component': 'Image', 'type': {'type': 'string'}},
        {'parameter_name': 'run_tiled_auxiliary', 'parameter_has_default': True, 'parameter_default': True, 'component': 'Checkbox', 'type': {'type': 'boolean'}},
    ],
    'returns': [{'component': 'JSON', 'type': {'type': 'object'}}],
}}, 'unnamed_endpoints': {}}


def scenario(browser, mode):
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    requests, errors = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def mock_route(route):
        url = route.request.url
        requests.append(url)
        headers = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*'}
        if route.request.method == 'OPTIONS':
            route.fulfill(status=204, headers=headers)
        elif url.endswith('/host'):
            route.fulfill(json={'host': MOCK}, headers=headers)
        elif url.endswith('/config'):
            route.fulfill(json=CONFIG, headers=headers)
        elif url.endswith('/info'):
            route.fulfill(json=API, headers=headers)
        elif url.endswith('/upload'):
            route.fulfill(json=['/tmp/judge-image.jpg'], headers=headers)
        elif '/run/analyze_image_gradio' in url:
            if mode == 'quota':
                route.fulfill(status=503, json={'error': 'You have exceeded your ZeroGPU runs limit.'}, headers=headers)
            else:
                route.fulfill(json={'data': [PAYLOAD]}, headers=headers)
        else:
            route.abort()

    page.route('https://huggingface.co/**', mock_route)
    page.route('https://mock.hf.space/**', mock_route)
    page.goto('http://127.0.0.1:4182/', wait_until='domcontentloaded')
    page.locator('input[type=file]').set_input_files(str(IMAGE))
    page.get_by_role('button', name='Run analysis').click()
    if mode == 'quota':
        page.get_by_text('LIVE GPU LIMIT REACHED', exact=True).wait_for()
        assert page.get_by_text('Live inference is unavailable because the shared ZeroGPU limit was reached.', exact=False).is_visible()
        assert page.locator('.top-status').get_by_text('GPU LIMIT').is_visible()
        assert page.locator('.image-stage img').evaluate('(image) => image.complete && image.naturalWidth > 0')
        calls = sum('/run/analyze_image_gradio' in url for url in requests)
        page.get_by_role('button', name='View verified example').click()
        page.get_by_text('No new inference will run', exact=False).wait_for()
        page.get_by_role('button', name='Load precomputed example').click()
        page.get_by_text('PRECOMPUTED EXAMPLE LOADED', exact=True).wait_for()
        assert sum('/run/analyze_image_gradio' in url for url in requests) == calls
    else:
        page.get_by_text('LIVE ANALYSIS COMPLETE', exact=True).wait_for()
        assert page.locator('.judge-source-banner').first.get_by_text('LIVE ANALYSIS', exact=True).is_visible()
        assert page.locator('.candidate-list tbody tr').count() == 2
        page.get_by_role('button', name='View report').click()
        page.locator('.report-source-banner').get_by_text('LIVE ANALYSIS', exact=True).wait_for()
    assert errors == [], errors
    print(json.dumps({'scenario': mode, 'run_calls': sum('/run/analyze_image_gradio' in url for url in requests), 'requests': requests, 'page_errors': errors}))
    page.close()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    scenario(browser, 'quota')
    scenario(browser, 'success')
    browser.close()
