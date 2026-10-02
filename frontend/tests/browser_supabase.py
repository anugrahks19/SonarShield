"""Mock Supabase HTTP contract + real browser; does not use production credentials."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
sample=json.loads((root/'public/contact-105.json').read_text())
image=(root/'public/contact-105.jpg').read_bytes()
record_id='11111111-1111-1111-1111-111111111111'
record=None
saved_image=None
history=[]
inference=[]
traffic=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
 page=browser.new_page();errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 def respond(route,value,status=200):route.fulfill(status=status,content_type='application/json',body=json.dumps(value))
 def api(route):
  global record,history
  req=route.request;traffic.append(req.url)
  if req.method=='GET':return respond(route,dict(url='https://mock.supabase.co',publishableKey='sb_publishable_TEST_ONLY_0123456789',bucket='sonar-records'))
  body=req.post_data_json;action=body['action']
  if action=='list':return respond(route,dict(records=[] if record is None else [dict(id=record_id,analysis_id=sample['analysis_id'],source=record['source'],has_image=saved_image is not None,deleting=False,expires_at='2026-11-01T00:00:00Z')]))
  if action=='create':
   record=dict(id=record_id,analysis=body['analysis'],source=body['source'],image_sha256=body['image_sha256'],image_path=f'{record_id}/{record_id}/image.jpg',review_history=history)
   return respond(route,record)
  if action=='get':return respond(route,{**record,'review_history':history})
  if action=='review':
   history.append(dict(candidate_id=body['candidate_id'],revision=len(history)+1,reviewer=record_id,status=body['status'],note=body['note'],created_at='2026-10-03T00:00:00Z'));return respond(route,dict(revision=len(history)))
  if action=='delete_begin':return respond(route,dict(image_path=record['image_path']))
  if action=='delete_finish':record=None;history=[];return respond(route,dict(deleted=True))
  raise AssertionError(action)
 def cloud(route):
  global saved_image
  req=route.request;traffic.append(req.url)
  if '/auth/v1/token' in req.url:return respond(route,dict(access_token='TEST_USER_JWT_ONLY_0123456789',expires_in=3600))
  if '/auth/v1/logout' in req.url:return respond(route,{})
  if req.method=='POST':saved_image=req.post_data_buffer;return respond(route,{})
  if req.method=='DELETE':saved_image=None;return respond(route,[])
  route.fulfill(status=200,content_type='image/jpeg',body=saved_image)
 def block(route):inference.append(route.request.url);route.abort()
 page.route('**/api/records',api);page.route('https://mock.supabase.co/**',cloud)
 page.route('**/api/analyze',block);page.route('**/*.hf.space/**',block)
 page.goto('http://127.0.0.1:4182/')
 page.get_by_role('button',name='Explore verified examples').click();page.get_by_role('button',name='Load precomputed example').click();page.get_by_text('PRECOMPUTED EXAMPLE LOADED',exact=True).wait_for()
 panel=page.locator('.shared-records');panel.locator('summary').first.click()
 def signin():
  panel.get_by_label('Reviewer email').fill('reviewer@example.test');panel.get_by_label('Password',exact=True).fill('TEST_PASSWORD_ONLY');panel.get_by_role('button',name='Sign in',exact=True).click();panel.get_by_text('Signed in.',exact=False).wait_for()
 signin();panel.get_by_role('button',name='Save to cloud',exact=True).click();panel.get_by_text('Analysis and paired image saved.',exact=False).wait_for();assert saved_image==image
 review=dict(analysisId=sample['analysis_id'],candidateId=sample['candidates'][0]['candidate_id'],status='CONFIRMED',note='Cloud browser review',reviewedAt='2026-10-03T00:00:00Z')
 page.evaluate("review=>localStorage.setItem('sonarShield.review.v1',JSON.stringify({version:1,reviews:{[JSON.stringify([review.analysisId,review.candidateId])]:review}}))",review)
 page.reload();page.locator('.candidate-list tbody tr').nth(1).wait_for();panel=page.locator('.shared-records');panel.locator('summary').first.click();assert panel.get_by_label('Password',exact=True).input_value()=='';signin()
 panel.get_by_role('button',name='Sync reviews to cloud').click();panel.get_by_text('1 cloud review revisions saved.',exact=True).wait_for();assert history[0]['note']=='Cloud browser review'
 page.get_by_role('button',name='Delete saved session').click();page.reload();panel=page.locator('.shared-records');panel.locator('summary').first.click();signin();panel.get_by_role('button',name='Load cloud records',exact=True).click();panel.get_by_role('button',name='Open cloud record').click();page.locator('.candidate-list tbody tr').nth(1).wait_for()
 page.get_by_role('button',name='View report').click();page.locator('.report-source-banner').get_by_text('PRECOMPUTED EXAMPLE · NOT LIVE INFERENCE',exact=True).wait_for()
 assert not inference and not errors,(inference,errors)
 assert not page.evaluate("JSON.stringify(localStorage)").find('TEST_USER_JWT_ONLY')>=0
 print(json.dumps(dict(mock_cloud_pair_restored=True,review_revision_synced=True,credentials_not_persisted=True,source_preserved=True,inference_calls=len(inference),page_errors=errors)))
 browser.close()
