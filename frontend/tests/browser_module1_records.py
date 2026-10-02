"""Offline persistence/portable-record verification; zero HF inference calls."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    context=browser.new_context(accept_downloads=True)
    page=context.new_page();errors=[];inference=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def block(route):
        if '/queue/' in route.request.url or '/run/' in route.request.url:inference.append(route.request.url)
        route.abort()
    page.route('**/*huggingface.co/**',block);page.route('**/*.hf.space/**',block)
    page.goto('http://127.0.0.1:4182/')
    page.get_by_role('button',name='Explore verified examples').click()
    page.get_by_role('button',name='Load precomputed example').click()
    page.get_by_text('PRECOMPUTED EXAMPLE LOADED',exact=True).wait_for()
    page.wait_for_function("new Promise(resolve => {const q=indexedDB.open('sonar-shield-records',1);q.onsuccess=()=>{const db=q.result;const r=db.transaction('sessions').objectStore('sessions').get('active');r.onsuccess=()=>{resolve(!!r.result);db.close()}}})")
    with page.expect_download() as dl:page.get_by_role('button',name='Export complete record').click()
    record_path=Path(dl.value.path());record=json.loads(record_path.read_text())
    assert record['source']=='PRECOMPUTED_EXAMPLE' and len(record['result']['candidates'])==2
    page.reload();page.locator('.candidate-list tbody tr').nth(1).wait_for()
    assert page.locator('.bbox').count()==2
    page.get_by_role('button',name='Delete saved session').click()
    page.get_by_text('Saved session deleted.',exact=False).wait_for()
    page.reload();page.get_by_role('button',name='Export complete record').wait_for()
    assert page.get_by_role('button',name='Export complete record').is_disabled()
    with page.expect_file_chooser() as chooser:page.get_by_role('button',name='Import complete record').click()
    chooser.value.set_files(str(record_path))
    page.locator('.candidate-list tbody tr').nth(1).wait_for()
    assert page.locator('.bbox').count()==2
    assert not inference and not errors,(inference,errors)
    print(json.dumps(dict(refresh_restored=True,portable_roundtrip=True,source_preserved=True,inference_calls=0,page_errors=errors)))
    browser.close()
