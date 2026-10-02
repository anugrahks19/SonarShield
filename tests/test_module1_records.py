import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from ai.api.gate_f8_api_server import app
class RecordTests(unittest.TestCase):
    def test_auth_isolation_immutable_ai_and_review_conflict(self):
        sample=json.loads((Path(__file__).resolve().parents[1]/'frontend/public/contact-105.json').read_text())
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,SONAR_RECORDS_DB=str(Path(directory)/'records.sqlite'),SONAR_REVIEW_TOKENS_JSON=json.dumps({'alice':'a'*32,'bob':'b'*32})):
            c=TestClient(app);a={'Authorization':'Bearer '+'a'*32};b={'Authorization':'Bearer '+'b'*32}
            self.assertEqual(c.get('/records/x').status_code,401)
            self.assertEqual(c.post('/records',headers=a,json=dict(analysis=sample,source='PRECOMPUTED_EXAMPLE')).status_code,200)
            key=sample['analysis_id'];self.assertEqual(c.get('/records/'+key,headers=b).status_code,404)
            self.assertEqual(c.post('/records',headers=a,json=dict(analysis=sample,source='PRECOMPUTED_EXAMPLE')).status_code,409)
            review=dict(candidate_id=sample['candidates'][0]['candidate_id'],previous_revision=0,status='CONFIRMED',note='checked')
            self.assertEqual(c.post('/records/'+key+'/reviews',headers=a,json=review).status_code,200)
            self.assertEqual(c.post('/records/'+key+'/reviews',headers=a,json=review).status_code,409)
            restored=c.get('/records/'+key,headers=a).json()
            self.assertEqual(restored['analysis'],sample)
            self.assertEqual(restored['review_history'][0]['reviewer'],'alice')
            self.assertEqual(c.delete('/records/'+key,headers=a).status_code,200)
            self.assertEqual(c.get('/records/'+key,headers=a).status_code,404)
if __name__=='__main__':unittest.main()
