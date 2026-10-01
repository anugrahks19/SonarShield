"""Opt-in: one real live gateway inference, followed by review/report/export checks.

python tests/browser_live_gateway.py --live
Never reads or prints HF_TOKEN. This consumes the service account's GPU quota.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true', help='Authorize one real inference request')
parser.add_argument('--base', default='https://sonarshield26.vercel.app')
args = parser.parse_args()
if not args.live:
    parser.error('--live is required because this check consumes real GPU quota')

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900}, accept_downloads=True)
    page.set_default_timeout(30000)
    requests, gateway_responses, errors = [], [], []

    def request_seen(request):
        requests.append(request.url)
        if 'huggingface.co/' in request.url or '.hf.space/' in request.url:
            assert 'authorization' not in request.headers, 'Browser sent an unexpected HF credential'

    def response_seen(response):
        if response.url.endswith('/api/analyze') and response.request.method == 'POST':
            gateway_responses.append(response)

    page.on('request', request_seen)
    page.on('response', response_seen)
    page.on('pageerror', lambda error: errors.append(str(error)))
    # Readiness only; no inference. Avoid running against an old deployment.
    assert page.request.get(args.base + '/api/analyze').status == 405, 'Gateway deployment is not ready'
    page.goto(args.base + '/analysis', wait_until='domcontentloaded')
    page.locator('input[type=file]').set_input_files(str(Path(__file__).resolve().parents[1] / 'public/contact-105.jpg'))
    page.get_by_role('button', name='Run analysis', exact=True).click()
    page.wait_for_function("!!document.querySelector('.notice.error') || !!document.querySelector('.judge-source-banner.live') || document.body.textContent.includes('Live analysis complete')", timeout=285000)
    assert len(gateway_responses) == 1
    response = gateway_responses[0]
    payload = response.json()
    if response.status != 200:
        print(json.dumps({'live_verified': False, 'http_status': response.status, 'error': payload.get('error'), 'gateway_calls': 1}))
        browser.close()
        raise SystemExit(2)
    page.get_by_text('LIVE ANALYSIS COMPLETE', exact=True).wait_for()
    count = page.locator('.candidate-list tbody tr').count()
    if count:
        page.get_by_role('button', name='Confirm target', exact=True).click()
        page.get_by_placeholder('Add observations…').fill('Authenticated gateway live verification')
        page.get_by_role('button', name='Save review', exact=True).click()
        page.get_by_role('button', name='Confirm review', exact=True).click()
    page.get_by_role('button', name='View report', exact=True).click()
    page.locator('.report-source-banner').get_by_text('LIVE ANALYSIS', exact=True).wait_for()
    with page.expect_download() as download_info:
        page.get_by_role('button', name='Export JSON', exact=True).click()
    exported = json.loads(Path(download_info.value.path()).read_text(encoding='utf-8'))
    assert exported['result_source'] == 'LIVE_ANALYSIS'
    assert exported['analysis'] == payload
    assert not any('/run/' in url or '/queue/join' in url for url in requests)
    assert not errors, errors
    print(json.dumps({'live_verified': True, 'http_status': response.status, 'candidates': count, 'gateway_calls': 1, 'browser_direct_inference_calls': 0, 'review_checked': count > 0, 'report_and_export_checked': True, 'page_errors': []}))
    browser.close()
