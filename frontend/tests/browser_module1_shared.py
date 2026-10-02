"""Real local control service + browser shared-record workflow, without inference. Requires Vite DEV server at 127.0.0.1:5173."""
import json,os,sys,tempfile,threading,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import uvicorn
from playwright.sync_api import sync_playwright
with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,SONAR_RECORDS_DB=str(Path(directory)/'records.sqlite'),SONAR_REVIEW_TOKENS_JSON=json.dumps({'test-reviewer':'TEST_REVIEWER_ONLY_01234567890123456789'}),SONAR_ALLOWED_ORIGINS='http://127.0.0.1:5173'):
    server=uvicorn.Server(uvicorn.Config('ai.api.control_server:app',host='127.0.0.1',port=8093,log_level='error',access_log=False))
    worker=threading.Thread(target=server.run,daemon=True);worker.start()
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.05)
        assert server.started
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
            page=browser.new_page();errors=[];inference=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            def block(route):
                if '/queue/' in route.request.url or '/run/' in route.request.url or '/api/analyze' in route.request.url:inference.append(route.request.url)
                route.abort()
            page.route('**/*huggingface.co/**',block);page.route('**/*.hf.space/**',block);page.route('**/api/analyze',block)
            page.goto('http://127.0.0.1:5173/?legacy-records=1')
            page.get_by_role('button',name='Explore verified examples').click();page.get_by_role('button',name='Load precomputed example').click()
            page.get_by_text('PRECOMPUTED EXAMPLE LOADED',exact=True).wait_for()
            panel=page.locator('.shared-records');panel.locator('summary').first.click()
            panel.get_by_label('Record service URL').fill('http://127.0.0.1:8093');panel.get_by_label('Reviewer credential').fill('TEST_REVIEWER_ONLY_01234567890123456789')
            panel.get_by_role('button',name='Connect and list records').click();panel.get_by_text('Connected.',exact=False).wait_for()
            panel.get_by_role('button',name='Save current analysis and image').click();panel.get_by_text('Analysis and paired image saved.',exact=False).wait_for()
            assert panel.get_by_role('button',name='Open stored record').count()==1
            fixture=json.loads((Path(__file__).resolve().parents[1]/'public/contact-105.json').read_text())
            review=dict(analysisId=fixture['analysis_id'],candidateId=fixture['candidates'][0]['candidate_id'],status='CONFIRMED',note='Explicit shared browser review',reviewedAt='2026-10-02T00:00:00Z')
            page.evaluate("review => localStorage.setItem('sonarShield.review.v1',JSON.stringify({version:1,reviews:{[JSON.stringify([review.analysisId,review.candidateId])]:review}}))",review)
            page.reload();page.locator('.candidate-list tbody tr').nth(1).wait_for()
            panel=page.locator('.shared-records');panel.locator('summary').first.click()
            panel.get_by_label('Record service URL').fill('http://127.0.0.1:8093');panel.get_by_label('Reviewer credential').fill('TEST_REVIEWER_ONLY_01234567890123456789')
            panel.get_by_role('button',name='Connect and list records').click();panel.get_by_text('Connected.',exact=False).wait_for()
            panel.get_by_role('button',name='Sync current reviews').click();panel.get_by_text('1 review revisions saved.',exact=False).wait_for()
            panel.get_by_text('Immutable review revision history',exact=True).click();panel.get_by_text('Explicit shared browser review',exact=True).wait_for()
            page.reload();page.locator('.candidate-list tbody tr').nth(1).wait_for()
            # Clear browser session to prove shared storage can reconstruct the paired record.
            page.get_by_role('button',name='Delete saved session').click();page.get_by_text('Saved session deleted.',exact=False).wait_for();page.reload()
            panel=page.locator('.shared-records');panel.locator('summary').first.click()
            assert panel.get_by_label('Reviewer credential').input_value()==''
            panel.get_by_label('Record service URL').fill('http://127.0.0.1:8093');panel.get_by_label('Reviewer credential').fill('TEST_REVIEWER_ONLY_01234567890123456789')
            panel.get_by_role('button',name='Connect and list records').click();panel.get_by_role('button',name='Open stored record').wait_for();panel.get_by_role('button',name='Open stored record').click()
            page.locator('.candidate-list tbody tr').nth(1).wait_for()
            page.get_by_role('button',name='View report').click();page.locator('.report-source-banner').get_by_text('PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE',exact=True).wait_for()
            assert not errors and not inference,(errors,inference)
            print(json.dumps(dict(shared_pair_restored=True,shared_review_synced=True,credential_not_persisted=True,source_preserved=True,inference_calls=0,page_errors=errors)))
            browser.close()
    finally:server.should_exit=True;worker.join(timeout=10)
