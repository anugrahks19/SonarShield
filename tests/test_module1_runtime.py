import hashlib,json,unittest
from pathlib import Path
import numpy as np
from fastapi.testclient import TestClient
from ai.runtime.pipeline import AnalysisRuntime,decode_image,merge_candidates
from ai.runtime.localization import RasterMetadata,localize,validate_metadata
from ai.api.gate_f8_api_server import app

ROOT=Path(__file__).resolve().parents[1]
DATA=(ROOT/'frontend/public/contact-105.jpg').read_bytes()
def metadata():
    return dict(version='ground-range-raster-v1',image_sha256=hashlib.sha256(DATA).hexdigest(),width=640,height=640,geometry='GROUND_RANGE_CORRECTED',navigation_source='SYNTHETIC_TEST_NOT_FIELD_DATA',position_reference='SENSOR_WGS84',across_track_m_per_pixel=0.1,along_track_m_per_pixel=0.1,nadir_x_px=320,navigation=[dict(row=0,latitude=10,longitude=76,heading_deg=0,timestamp='2026-10-02T00:00:00Z'),dict(row=640,latitude=10.0001,longitude=76,heading_deg=0,timestamp='2026-10-02T00:00:10Z')])
class Detector:
    def predict(self,image,**options):
        return [dict(bbox=[10,10,30,30],detector_confidence=.7,**{'class':2},source='global')]
class Fusion:
    def predict_proba(self,row): return np.array([[.2,.8]])
class Module1Tests(unittest.TestCase):
    def test_safe_import_and_deprecated_endpoints(self):
        c=TestClient(app)
        self.assertEqual(c.get('/health').json()['components']['calibration'],'UNAVAILABLE')
        self.assertEqual(c.post('/detect').status_code,410)
        self.assertEqual(c.post('/report').status_code,501)
        self.assertEqual(c.post('/analyze',files={'file':('bad.jpg',b'not image','image/jpeg')}).status_code,422)
    def test_adjacent_classes_and_duplicate_merge(self):
        make=lambda b,cl=0:dict(bbox=b,detector_confidence=.8,**{'class':cl})
        self.assertEqual(len(merge_candidates([make([0,0,10,10])],[make([11,0,21,10]),make([0,0,10,10]),make([0,0,10,10],2)],100,100)),3)
    def test_unavailable_calibration_and_real_identity(self):
        r=AnalysisRuntime(detector=Detector(),fusion=Fusion(),features=['confidence'],hashes={'detector':'a'*64,'fusion':'b'*64})
        out=r.analyze(DATA,'contact.jpg').model_dump()
        self.assertEqual(out['input']['sha256'],hashlib.sha256(DATA).hexdigest())
        self.assertEqual(out['candidates'][0]['detection']['class_name'],'Shipwreck')
        self.assertIsNone(out['candidates'][0]['classification']['reliability'])
        self.assertEqual(out['candidates'][0]['decision']['status'],'REVIEW')
        self.assertEqual(out['summary']['review_count'],1)
    def test_metadata_identity_and_north_heading(self):
        m=validate_metadata(metadata(),DATA,640,640)
        loc=localize([400,310,420,330],640,640,m)
        self.assertGreater(loc['coordinates']['geographic']['longitude'],76)
        self.assertAlmostEqual(loc['physical_dimensions']['width_m'],2)
        bad=metadata();bad['image_sha256']='0'*64
        with self.assertRaises(ValueError):validate_metadata(bad,DATA,640,640)
    def test_missing_metadata_and_stale_navigation(self):
        self.assertIsNone(localize([0,0,20,20],640,640)['coordinates']['geographic'])
        bad=metadata();bad['navigation'][1]['timestamp']='2026-10-02T00:01:00Z'
        with self.assertRaises(ValueError):RasterMetadata.model_validate(bad)
    def test_invalid_boxes_scores_and_inputs(self):
        with self.assertRaises(ValueError):decode_image(b'broken')
        with self.assertRaises(ValueError):merge_candidates([dict(bbox=[0,0,1,1],detector_confidence=float('nan'),**{'class':0})],[],640,640)
        r=AnalysisRuntime(root=ROOT/'.temp/no-artifacts')
        with self.assertRaises(FileNotFoundError):r.initialize()
    def test_contained_same_contact_is_merged(self):
        p=lambda b:dict(bbox=b,detector_confidence=.8,**{"class":0})
        self.assertEqual(len(merge_candidates([p([0,0,20,20])],[p([1,1,18,18])],100,100)),1)
    def test_busy_admission(self):
        r=AnalysisRuntime();r.admission.acquire()
        with self.assertRaisesRegex(RuntimeError,'SERVICE_BUSY'):r.analyze(DATA,'image.jpg')
        r.admission.release()
if __name__=='__main__': unittest.main()
