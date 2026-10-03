import hashlib
import unittest
from fastapi.testclient import TestClient
from ai.api.edge_server import create_app


class Result:
    def model_dump(self, **kwargs): return {'summary': {'candidate_count': 0}, 'candidates': []}


class Runtime:
    def __init__(self): self.calls=[]; self.error=None
    def analyze(self, data, name, tiled):
        self.calls.append((data,name,tiled))
        if self.error: raise self.error
        return Result()


class EdgeTests(unittest.TestCase):
    def setUp(self):
        self.runtime=Runtime(); self.token='a'*40
        self.client=TestClient(create_app(self.runtime,{'auv-test':self.token}))
        self.headers={'Authorization':'Bearer '+self.token,'Content-Type':'image/png','X-Request-Id':'frame-123'}
    def test_auth_before_input_and_lazy_capabilities(self):
        self.assertEqual(self.client.post('/v1/edge/analyze',content=b'bad').status_code,401)
        r=self.client.get('/v1/edge/capabilities',headers=self.headers)
        self.assertEqual(r.status_code,200);self.assertFalse(r.json()['vehicle_control']);self.assertEqual(self.runtime.calls,[])
    def test_contract_device_identity_and_no_secret(self):
        r=self.client.post('/v1/edge/analyze',content=b'fake-png-for-mock',headers=self.headers)
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['device_id'],'auv-test')
        self.assertEqual(r.json()['input_sha256'],hashlib.sha256(b'fake-png-for-mock').hexdigest())
        self.assertNotIn(self.token,r.text);self.assertEqual(len(self.runtime.calls),1)
    def test_bounds_and_content_type(self):
        for changes,status in [({'Content-Length':str(32*1024*1024+1)},413),({'Content-Type':'application/octet-stream'},415),({'X-Request-Id':'../unsafe'},422)]:
            r=self.client.post('/v1/edge/analyze',content=b'a',headers={**self.headers,**changes})
            self.assertEqual(r.status_code,status)
        self.assertEqual(self.runtime.calls,[])
    def test_stream_cap_without_length(self):
        import ai.api.edge_server as module
        from unittest.mock import patch
        with patch.object(module,'MAX_IMAGE_BYTES',3):
            r=self.client.post('/v1/edge/analyze',content=iter([b'aa',b'aa']),headers=self.headers)
        self.assertEqual(r.status_code,413);self.assertEqual(self.runtime.calls,[])
    def test_invalid_busy_and_unavailable(self):
        for error,status in [(ValueError('bad'),422),(RuntimeError('SERVICE_BUSY: occupied'),503),(FileNotFoundError('secret-path'),503)]:
            self.runtime.error=error;r=self.client.post('/v1/edge/analyze',content=b'a',headers=self.headers)
            self.assertEqual(r.status_code,status);self.assertNotIn('secret-path',r.text)
    def test_disabled_and_unique_tokens(self):
        self.assertEqual(TestClient(create_app(self.runtime,{})).get('/v1/edge/capabilities').status_code,401)
        with self.assertRaises(ValueError):create_app(self.runtime,{'x':self.token,'y':self.token})


if __name__=='__main__':unittest.main()
