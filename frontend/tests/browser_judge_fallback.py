"""Judge fallback QA against a local preview on port 4182; never calls ZeroGPU."""
import json
from io import BytesIO
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader


BASE = 'http://127.0.0.1:4182/'
IMAGE = Path(__file__).resolve().parents[1] / 'public' / 'contact-105.jpg'

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900}, accept_downloads=True)
    errors = []
    space_requests = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def block_space(route):
        space_requests.append(route.request.url)
        route.abort()

    page.route('**/huggingface.co/**', block_space)
    page.route('**/*.hf.space/**', block_space)
    page.goto(BASE, wait_until='domcontentloaded')
    page.get_by_role('button', name='Explore verified examples').click()
    page.get_by_text('No new inference will run', exact=False).wait_for()
    page.get_by_role('button', name='Load precomputed example').click()
    page.get_by_text('PRECOMPUTED EXAMPLE LOADED', exact=True).wait_for()
    assert page.locator('.candidate-list tbody tr').count() == 2
    assert page.locator('.bbox').count() == 2
    assert page.locator('.judge-source-banner').first.get_by_text('PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE').is_visible()
    assert len(space_requests) <= 1, space_requests  # initial reachability check only
    page.get_by_role('button', name='Confirm target').click()
    page.get_by_placeholder('Add observations…').fill('Reviewed verified sample')
    page.get_by_role('button', name='Save review').click()
    page.get_by_role('button', name='Confirm review').click()
    assert page.get_by_placeholder('Add observations…').input_value() == 'Reviewed verified sample'

    page.get_by_role('button', name='View report').click()
    page.locator('.report-source-banner').get_by_text('PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE').wait_for()
    with page.expect_download() as download_info:
        page.get_by_role('button', name='Export JSON').click()
    download = download_info.value
    assert 'precomputed-example' in download.suggested_filename
    exported = json.loads(Path(download.path()).read_text(encoding='utf-8'))
    assert exported['result_source'] == 'PRECOMPUTED_EXAMPLE'
    assert exported['source_label'] == 'PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE'
    assert exported['analysis']['summary']['candidate_count'] == 2
    assert exported['human_review']['reviews'][0]['note'] == 'Reviewed verified sample'
    with page.expect_download() as csv_info:
        page.get_by_role('button', name='Export CSV').click()
    csv_download = csv_info.value
    assert 'precomputed-example' in csv_download.suggested_filename
    csv_text = Path(csv_download.path()).read_text(encoding='utf-8')
    assert 'PRECOMPUTED_EXAMPLE' in csv_text
    assert 'PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE' in csv_text
    print_text = '\n'.join((part.extract_text() or '') for part in PdfReader(BytesIO(page.pdf(print_background=True))).pages)
    assert 'PRECOMPUTED EXAMPLE' in print_text and 'NOT LIVE INFERENCE' in print_text
    assert len(space_requests) <= 1, space_requests

    page.get_by_role('button', name='← Analysis').click()
    for sample, expected in [('contact-103', 1), ('contact-104', 1), ('background', 0)]:
        page.get_by_role('button', name='Explore verified examples').click()
        page.get_by_label('Choose a real test image').select_option(sample)
        page.get_by_role('button', name='Load precomputed example').click()
        page.get_by_text('PRECOMPUTED EXAMPLE LOADED', exact=True).wait_for()
        assert page.locator('.candidate-list tbody tr').count() == expected
        assert page.locator('.bbox').count() == expected
        assert len(space_requests) <= 1, space_requests

    page.locator('input[type=file]').set_input_files(str(IMAGE))
    page.get_by_role('button', name='Run analysis').click()
    page.get_by_text('ANALYSIS FAILED', exact=True).wait_for()
    assert page.get_by_text('The Hugging Face Space could not be reached.', exact=False).is_visible()
    assert page.get_by_role('button', name='View verified example').is_visible()
    assert page.get_by_role('button', name='Try live again later').is_visible()
    assert page.locator('.image-stage img').evaluate('(image) => image.complete && image.naturalWidth > 0')
    calls_after_failure = len(space_requests)
    page.get_by_role('button', name='View verified example').click()
    page.get_by_text('not a result for your uploaded image', exact=False).wait_for()
    assert len(space_requests) == calls_after_failure
    page.get_by_role('button', name='Load precomputed example').click()
    page.get_by_text('PRECOMPUTED EXAMPLE LOADED', exact=True).wait_for()
    assert len(space_requests) == calls_after_failure
    assert errors == [], errors
    print(json.dumps({'space_requests_before_explicit_fallback': calls_after_failure, 'space_request_urls': space_requests, 'additional_inference_calls': 0, 'page_errors': errors}))
    browser.close()
