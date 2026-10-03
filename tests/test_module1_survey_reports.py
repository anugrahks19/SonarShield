import json,tempfile,unittest,csv,copy,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from ai.runtime.pipeline import AnalysisRuntime
from ai.runtime.survey_job import run_job
from ai.runtime.sonar_geometry import geodesic
from ai.api.f8_api_schema import AnalyzeResponse

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_survey_positions import evaluate

ROOT=Path(__file__).resolve().parents[1]
BASE=json.loads((ROOT/'frontend/public/contact-105.json').read_text())


class Stub:
    hashes={'detector':'a'*64,'fusion':'b'*64}
    def initialize(self):pass
    def analyze(self,data,name,tiled):
        from PIL import Image
        import io,hashlib
        width,height=Image.open(io.BytesIO(data)).size
        r=copy.deepcopy(BASE);r.update(schema_version='F8.1',analysis_id='SYNTHETIC_TEST_ONLY')
        r['input'].update(width=width,height=height,sha256=hashlib.sha256(data).hexdigest(),filename=name)
        c=r['candidates'][0];c['detection']['bbox']=[1,2,5,6]
        c['classification']['reliability']=None;c['classification']['presentation'].update(reliability_band='UNCALIBRATED',uncertainty_level='UNKNOWN')
        c['provenance'].update(image_sha256=r['input']['sha256'],detector_artifact_sha256='a'*64,fusion_artifact_sha256='b'*64,decision_policy_sha256=None,classification_calibration_sha256=None,localization_uncertainty_sha256=None)
        c['decision']['status']='REVIEW'
        from ai.runtime.localization import localize
        c['localization']=localize([1,2,5,6],width,height)
        c['evidence']['bbox']=[1,2,5,6]
        c['evidence']['geometry'].update(width_px=4,height_px=4,bbox_area_px=16)
        r['candidates']=[c];r['summary']=dict(candidate_count=1,confirmed_count=0,review_count=1,rejected_count=0,unknown_count=0)
        class Output:
            def model_dump(self):return r
        return Output()


def rows(count=16):
    for i in range(count):yield dict(channel=0,channel_type_raw=2,nav_units_code=3,timestamp_raw=f'2020-01-01T00:00:{i:02d}',heading_raw=0,pitch_raw=0,roll_raw=0,heave_raw=0,altitude_raw=3,slant_range_m=10,sensor_x_raw=0,sensor_y_raw=i/111000,ship_x_raw=0,ship_y_raw=i/111000,samples=np.arange(100,dtype=np.uint16)*500,ping_number=i,packet_offset=1024+i*256)


class SurveyReportTests(unittest.TestCase):
    def test_source_to_geometry_report_and_offline_viewer(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);log=root/'input.xtf';log.write_bytes(b'SYNTHETIC_NOT_A_SURVEY')
            config=dict(version='xtf-flat-bottom-v1',source_log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),configuration_reference='SYNTHETIC TEST ONLY NOT FIELD VALIDATION',projection_authorized=True,navigation_datum='WGS84',nav_units_code=3,timestamp_timezone='UTC',position_reference='SENSOR',channels={0:dict(side='STARBOARD',sample_order='NEAR_TO_FAR')},altitude_source_reference='Synthetic known altitude',altitude_scale=1,heading_source_reference='Synthetic heading',pose_alignment_reference='Synthetic aligned pose',zero_heave_verified=True,ground_resolution_m=.5)
            with patch('ai.runtime.survey_job.packets',side_effect=lambda path:rows(32)):
                state=run_job(log,root/'run',rows=16,overlap=0,max_windows=2,runtime=Stub(),geometry_profile=config)
                self.assertEqual(state['geographic'],'OPERATOR_CONFIGURED_NOT_FIELD_VALIDATED')
                response=json.loads((root/'run/window-00000.json').read_text());AnalyzeResponse.model_validate(response)
                c=response['candidates'][0];self.assertGreater(c['localization']['coordinates']['geographic']['longitude'],0)
                self.assertEqual(c['decision']['status'],'REVIEW');self.assertIsNone(c['classification']['reliability'])
                report=json.loads((root/'run/report.json').read_text());self.assertEqual(report['field_accuracy'],'NOT_EVALUATED')
                self.assertEqual(len(json.loads((root/'run/contacts.geojson').read_text())['features']),2)
                contacts=json.loads((root/'run/contacts.json').read_text())['contacts']
                self.assertEqual(contacts[0]['geographic'],c['localization']['coordinates']['geographic'])
                self.assertEqual(json.loads((root/'run/contacts.json').read_text())['coordinate_system'],'RECTIFIED_GRID_COLUMN_CHANNEL_ROW')
                with (root/'run/report.csv').open(newline='') as f: self.assertEqual(next(csv.DictReader(f))['source'],'LOCAL_RAW_SURVEY_INFERENCE')
                html=(root/'run/window-00000.html').read_text();self.assertIn('LOCAL OFFLINE INFERENCE',html);self.assertNotIn('fetch(',html)
                self.assertIn('human_reviews',html)
                config['source_log_sha256']='f'*64
                with self.assertRaisesRegex(ValueError,'source-log hash'):run_job(log,root/'bad',rows=16,max_windows=1,runtime=Stub(),geometry_profile=config)

    def test_reference_error_requires_real_explicit_matches(self):
        lat,lon=0,0;point=geodesic().Direct(lat,lon,90,10)
        report={'rows':[dict(candidate_id='c',latitude=point['lat2'],longitude=point['lon2'],estimated_width_m=2,estimated_height_m=3)]}
        reference=[dict(candidate_id='c',latitude='0',longitude='0',reference_source='SYNTHETIC UNIT TEST NOT FIELD DATA',reference_uncertainty_m='0',width_m='2',height_m='3')]
        self.assertAlmostEqual(evaluate(report,reference)['mean_error_m'],10,places=5)
        with self.assertRaises(ValueError):evaluate(report,[])
        with self.assertRaises(ValueError):evaluate(report,reference+reference)
        bad=copy.deepcopy(report);bad['rows'][0]['latitude']=None
        with self.assertRaises(ValueError):evaluate(bad,reference)

if __name__=='__main__':unittest.main()
