import json,os,sqlite3,sys,tempfile,unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from ai.api.control_server import app
ROOT=Path(__file__).resolve().parents[1]

class ControlTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.root=Path(self.directory.name)
        self.config=patch.dict(os.environ,SONAR_RECORDS_DB=str(self.root/'records.sqlite'),SONAR_REVIEW_TOKENS_JSON=json.dumps({'alice':'a'*32,'bob':'b'*32,'eve':'e'*32}),SONAR_REVIEW_TEAMS_JSON=json.dumps({'alice':'judges','bob':'judges'}),SONAR_RECORD_RETENTION_DAYS='30',SONAR_ADMISSION_DB=str(self.root/'usage.sqlite'),SONAR_ADMISSION_TOKEN='s'*32,SONAR_DAILY_RUN_LIMIT='2',SONAR_CONCURRENT_RUN_LIMIT='1')
        self.config.start();self.client=TestClient(app)
        self.a={'Authorization':'Bearer '+'a'*32};self.b={'Authorization':'Bearer '+'b'*32};self.e={'Authorization':'Bearer '+'e'*32};self.gateway={'Authorization':'Bearer '+'s'*32}
        self.sample=json.loads((ROOT/'frontend/public/contact-105.json').read_text());self.key=self.sample['analysis_id']
    def tearDown(self):self.config.stop();self.directory.cleanup()
    def test_lightweight_entrypoint(self):
        import subprocess
        result=subprocess.run([sys.executable,'-B','-c',"import ai.api.control_server,sys; assert not any(k in sys.modules for k in ['torch','cv2','ultralytics'])"],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_shared_image_pair_team_and_history(self):
        self.assertEqual(self.client.post('/records',headers=self.a,json=dict(analysis=self.sample,source='PRECOMPUTED_EXAMPLE')).status_code,200)
        self.assertEqual(self.client.get('/records',headers=self.b).json()['records'][0]['has_image'],False)
        data=(ROOT/'frontend/public/contact-105.jpg').read_bytes()
        self.assertEqual(self.client.post(f'/records/{self.key}/image',headers=self.b,content=data).status_code,200)
        self.assertEqual(self.client.get(f'/records/{self.key}/image',headers=self.a).content,data)
        self.assertEqual(self.client.get(f'/records/{self.key}/image',headers=self.e).status_code,404)
        self.assertEqual(self.client.post(f'/records/{self.key}/image',headers=self.a,content=b'bad').status_code,422)
        item=dict(candidate_id=self.sample['candidates'][0]['candidate_id'],previous_revision=0,status='CONFIRMED',note='Shared review')
        self.assertEqual(self.client.post(f'/records/{self.key}/reviews',headers=self.b,json=item).json()['reviewer'],'bob')
        self.assertEqual(self.client.post(f'/records/{self.key}/reviews',headers=self.a,json=item).status_code,409)
        self.assertEqual(self.client.get(f'/records/{self.key}',headers=self.a).json()['analysis'],self.sample)
        self.client.delete(f'/records/{self.key}',headers=self.a)
        self.assertEqual(self.client.get(f'/records/{self.key}/image',headers=self.b).status_code,404)
    def test_retention_and_actual_backup(self):
        self.client.post('/records',headers=self.a,json=dict(analysis=self.sample,source='PRECOMPUTED_EXAMPLE'))
        with closing(sqlite3.connect(self.root/'records.sqlite')) as conn:conn.execute("UPDATE analyses SET created_at='2000-01-01T00:00:00+00:00'");conn.commit()
        self.assertEqual(self.client.get('/records',headers=self.a).json()['records'],[])
        import subprocess
        result=subprocess.run([sys.executable,'-B','scripts/backup_records.py',str(self.root/'records.sqlite'),str(self.root/'backup.sqlite')],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        with closing(sqlite3.connect(self.root/'backup.sqlite')) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM analyses').fetchone()[0],0)
    def test_admission_auth_concurrency_and_persistent_budget(self):
        self.assertEqual(self.client.post('/admission/acquire').status_code,401)
        lease=self.client.post('/admission/acquire',headers=self.gateway).json()
        self.assertEqual(TestClient(app).post('/admission/acquire',headers=self.gateway).status_code,429)
        self.assertEqual(self.client.post('/admission/release',headers=self.gateway,json={'lease_id':lease['lease_id']}).status_code,200)
        second=self.client.post('/admission/acquire',headers=self.gateway).json()
        self.client.post('/admission/release',headers=self.gateway,json={'lease_id':second['lease_id']})
        self.assertEqual(TestClient(app).post('/admission/acquire',headers=self.gateway).status_code,429)
    def test_auth_before_body_and_cors_preflight(self):
        self.assertEqual(self.client.post('/records',content=b'x'*2300*1024).status_code,401)
        self.assertEqual(self.client.post('/records',headers=self.a,content=b'x'*2300*1024).status_code,413)
        response=self.client.options('/records',headers={'Origin':'http://127.0.0.1:4182','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Authorization,Content-Type'})
        self.assertEqual(response.status_code,200)
        self.assertNotIn('access-control-allow-origin',self.client.options('/records',headers={'Origin':'https://evil.invalid','Access-Control-Request-Method':'POST'}).headers)

    def test_corrected_import_rejects_semantic_corruption(self):
        source=json.loads((ROOT/'frontend/tests/fixtures/module1-cpu-response.json').read_text())
        for mutate in [lambda x:x['summary'].update(candidate_count=999),lambda x:x['candidates'][0]['classification'].update(class_id=4),lambda x:x['candidates'][0]['provenance'].update(image_sha256='0'*64)]:
            bad=json.loads(json.dumps(source));mutate(bad)
            self.assertEqual(self.client.post('/records',headers=self.a,json=dict(analysis=bad,source='LIVE_ANALYSIS')).status_code,422)
