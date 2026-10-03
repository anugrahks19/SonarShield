import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from ai.runtime.xtf import windows
from ai.runtime.survey import acquisition_quality,reconcile
from ai.runtime.survey_job import run_job

def records():
    for i in range(24):yield dict(channel=0,samples=np.zeros(8,dtype=np.uint16),ping_number=i,packet_offset=1024+i*64,slant_range_m=50)
class FakeRuntime:
    hashes={'detector':'a'*64,'fusion':'b'*64}
    calls=0
    def initialize(self):pass
    def analyze(self,data,name,tiled):
        self.calls+=1
        class Output:
            def model_dump(self):return dict(candidates=[dict(candidate_id=name,detection=dict(bbox=[1,2,5,6],class_id=0,class_name='Crab Pot',confidence=.8),quality=dict(image=dict(flags=[])))])
        return Output()
class JobTests(unittest.TestCase):
    def test_overlap_source_mapping_and_quality(self):
        output=list(windows(records(),rows=16,overlap=8))
        self.assertEqual(len(output),2)
        self.assertEqual(output[0][1]['row_indices'][-8:],output[1][1]['row_indices'][:8])
        self.assertEqual(output[0][1]['acquisition_quality']['zero_row_fraction'],1)
        self.assertIn('MOTION_CORRECTION_NOT_APPLIED',output[0][1]['acquisition_quality']['flags'])
        with self.assertRaises(ValueError):list(windows([],rows=16,overlap=16))
    def test_reconcile_does_not_mix_class_channel_or_segment(self):
        make=lambda window,**kw:dict(window=window,candidate_id=str(window),class_id=0,channel=0,segment=0,confidence=.8,source_box=[0,8,5,12],**kw)
        first=make(0);second=make(1);third=dict(make(2),channel=1);fourth=dict(make(3),class_id=2);fifth=dict(make(4),segment=1)
        merged=reconcile([first,second,third,fourth,fifth]);self.assertEqual(len(merged),4);self.assertEqual(len(merged[0]['observations']),2)
    def test_reconcile_rejects_incompatible_rectified_grids(self):
        first=dict(window=0,candidate_id='a',class_id=0,channel=0,segment=0,confidence=.8,source_box=[0,8,5,12],grid_identity=[20,.5,'PORT'])
        second=dict(first,window=1,candidate_id='b',grid_identity=[21,.5,'PORT'])
        self.assertEqual(len(reconcile([first,second])),2)

    def test_motion_dropouts_are_disclosed_and_not_reconstructed(self):
        block=list(records());block[0].update(pitch_raw=4,roll_raw=0,heave_raw=.2)
        for row in block[1:]:row.update(pitch_raw=0,roll_raw=0,heave_raw=0)
        quality=acquisition_quality(block)
        self.assertIn('NONLEVEL_ACQUISITION_REQUIRES_REVIEW',quality['flags'])
        self.assertIn('UNALIGNED_HEAVE_CORRECTION_UNAVAILABLE',quality['flags'])
        self.assertFalse(quality['missing_samples_reconstructed'])
        self.assertEqual(quality['zero_sample_row_indices'],list(range(24)))

    def test_progress_resume_cancel_and_configuration_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);log=root/'test.xtf';log.write_bytes(b'MOCK_SOURCE_NOT_XTF');output=root/'run';runtime=FakeRuntime()
            with patch('ai.runtime.survey_job.packets',side_effect=lambda path:records()):
                state=run_job(log,output,rows=16,overlap=8,max_windows=2,runtime=runtime)
                self.assertEqual(state['status'],'BOUNDED_COMPLETE');self.assertEqual(runtime.calls,2)
                saved=json.loads((output/'window-00000.json').read_text())
                self.assertIn('CANDIDATE_INTERSECTS_ACQUISITION_DROPOUT',[f['code'] for f in saved['candidates'][0]['quality']['image']['flags']])
                run_job(log,output,rows=16,overlap=8,max_windows=2,runtime=runtime,resume=True);self.assertEqual(runtime.calls,2)
                with self.assertRaises(ValueError):run_job(log,output,rows=16,overlap=4,max_windows=2,runtime=runtime,resume=True)
                cancel=root/'cancel';cancel.touch();other=FakeRuntime()
                state=run_job(log,root/'cancelled',rows=16,overlap=8,max_windows=2,runtime=other,cancel_file=cancel)
                self.assertEqual(state['status'],'CANCELLED');self.assertEqual(other.calls,0)
            self.assertFalse((output/'.job.lock').exists())

    def test_resume_rejects_changed_image_output_without_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);log=root/'test.xtf';log.write_bytes(b'MOCK_SOURCE_NOT_XTF');output=root/'run';runtime=FakeRuntime()
            with patch('ai.runtime.survey_job.packets',side_effect=lambda path:records()):
                run_job(log,output,rows=16,overlap=8,max_windows=2,runtime=runtime)
                before=runtime.calls;(output/'window-00000.png').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'missing or changed'):run_job(log,output,rows=16,overlap=8,max_windows=2,runtime=runtime,resume=True)
                self.assertEqual(runtime.calls,before)
