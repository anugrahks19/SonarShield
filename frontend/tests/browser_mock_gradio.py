"""Mock direct uploads plus the authenticated gateway without spending ZeroGPU quota.

Requires local production preview on port 4182.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = json.loads((ROOT / 'public/contact-105.json').read_text(encoding='utf-8'))
CORRECTED_PAYLOAD = json.loads((ROOT / 'tests/fixtures/module1-cpu-response.json').read_text(encoding='utf-8'))
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
        assert 'authorization' not in route.request.headers
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
            if mode == 'large-success':
                assert len(route.request.post_data_buffer) > 4.5 * 1024 * 1024
            route.fulfill(json=['/tmp/gradio/' + 'a' * 64 + '/judge-image.jpg'], headers=headers)
        else:
            route.abort()

    page.route('https://huggingface.co/**', mock_route)
    page.route('https://mock.hf.space/**', mock_route)
    gateway_calls = []
    pending = []

    def gateway_route(route):
        gateway_calls.append(route.request.post_data_json)
        assert set(gateway_calls[-1]) == {'file'}
        assert len(route.request.post_data) < 2048
        assert 'hf_' not in route.request.post_data
        if mode == 'cancel':
            pending.append(route)
            return
        if mode in ('quota', 'quota-no-countdown'):
            from datetime import datetime, timedelta, timezone
            now = datetime.now(timezone.utc)
            details = {'upstreamMessage': 'You have exceeded your ZeroGPU runs limit.', 'receivedAt': now.isoformat()}
            if mode == 'quota':
                details.update({'upstreamMessage': 'You have exceeded your ZeroGPU quota. Try again in 1:23:45.', 'retryAfterSeconds': 5025, 'resetAt': (now + timedelta(seconds=5025)).isoformat()})
            route.fulfill(status=429, json={'error': {'code': 'GPU_QUOTA_EXCEEDED', 'message': 'Live inference is unavailable because the authenticated service account reached its ZeroGPU limit. Your image was not analyzed. Try again later or open a verified example.', 'details': details}})
        elif mode == 'auth':
            route.fulfill(status=502, json={'error': {'code': 'HF_AUTH_FAILED', 'message': 'Hugging Face authentication failed. The service token needs checking in Vercel.'}})
        elif mode == 'offline':
            route.fulfill(status=502, json={'error': {'code': 'API_OFFLINE', 'message': 'The Hugging Face Space could not be reached. Your image was not analyzed.'}})
        elif mode == 'invalid':
            route.fulfill(json={'status': 'COMPLETED'})
        else:
            route.fulfill(json=CORRECTED_PAYLOAD if mode == 'corrected-success' else PAYLOAD)

    page.route('**/api/analyze', gateway_route)
    page.goto('http://127.0.0.1:4182/', wait_until='domcontentloaded')
    if mode == 'large-success':
        # Valid JPEG plus padding; bytes must go to HF, not the Vercel function.
        page.locator('input[type=file]').set_input_files({'name': 'large.jpg', 'mimeType': 'image/jpeg', 'buffer': IMAGE.read_bytes() + bytes(5 * 1024 * 1024)})
    else:
        page.locator('input[type=file]').set_input_files(str(IMAGE))
    page.get_by_role('button', name='Run analysis').click()
    if mode in ('quota', 'quota-no-countdown'):
        page.get_by_text('LIVE GPU LIMIT REACHED', exact=True).wait_for()
        assert page.get_by_text('the authenticated service account reached its ZeroGPU limit', exact=False).is_visible()
        page.get_by_text('Technical details', exact=True).click()
        assert page.locator('.notice.error pre').inner_text().find('You have exceeded') >= 0
        if mode == 'quota':
            assert page.get_by_text('Hugging Face reported reset in', exact=False).is_visible()
        else:
            assert page.get_by_text('Reset time was not supplied by Hugging Face.', exact=True).is_visible()
        assert page.locator('.top-status').get_by_text('GPU LIMIT').is_visible()
        assert page.locator('.image-stage img').evaluate('(image) => image.complete && image.naturalWidth > 0')
        calls = len(gateway_calls)
        page.get_by_role('button', name='View verified example').click()
        page.get_by_text('No new inference will run', exact=False).wait_for()
        page.get_by_role('button', name='Load precomputed example').click()
        page.get_by_text('PRECOMPUTED EXAMPLE LOADED', exact=True).wait_for()
        assert len(gateway_calls) == calls
    elif mode == 'cancel':
        page.wait_for_function("document.querySelector('.upload-actions').textContent.includes('Cancel')")
        page.wait_for_timeout(300)
        assert len(pending) == 1
        page.get_by_role('button', name='Cancel', exact=True).click()
        try:
            pending[0].fulfill(json=PAYLOAD)
        except Exception:
            pass  # Browser may have already aborted the request.
        page.wait_for_timeout(300)
        assert page.locator('.candidate-list tbody tr').count() == 0
        assert page.get_by_role('button', name='Run analysis').is_enabled()
    elif mode in ('auth', 'offline', 'invalid'):
        page.locator('.notice.error').wait_for()
        expected = {'auth': 'HF_AUTH_FAILED', 'offline': 'API_OFFLINE', 'invalid': 'INVALID_API_RESPONSE'}[mode]
        assert page.locator('.notice.error code').inner_text() == expected
        assert page.locator('.candidate-list tbody tr').count() == 0
    else:
        page.get_by_text('LIVE ANALYSIS COMPLETE', exact=True).wait_for()
        assert page.locator('.judge-source-banner').first.get_by_text('LIVE ANALYSIS', exact=True).is_visible()
        assert page.locator('.candidate-list tbody tr').count() == 2
        page.get_by_role('button', name='View report').click()
        page.locator('.report-source-banner').get_by_text('LIVE ANALYSIS', exact=True).wait_for()
        if mode == 'large-success':
            assert gateway_calls[0]['file']['size'] > 4.5 * 1024 * 1024
    assert errors == [], errors
    assert len(gateway_calls) == 1
    assert not any('/run/' in url or '/queue/join' in url for url in requests)
    print(json.dumps({'scenario': mode, 'gateway_calls': len(gateway_calls), 'space_inference_calls': 0, 'page_errors': errors}))
    page.close()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    for mode in ('quota', 'quota-no-countdown', 'success', 'corrected-success', 'large-success', 'auth', 'offline', 'invalid', 'cancel'):
        scenario(browser, mode)
    browser.close()
