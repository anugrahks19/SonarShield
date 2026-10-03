import copy
import unittest
from ai.runtime.survey_evaluation import evaluate


def fixture():
    m={'rendering_source_sha256':'r'*64,'images':[{'image_sha256':'i'*64,'source_sha256':'s'*64,
       'day':'150603','split':'TEST','width':100,'height':100,'rendering_version':'LOG1P_PERCENTILE_V1'}]}
    a={'annotations':[{'image_sha256':'i'*64,'reviewer':'Independent test fixture reviewer','qualified_review':True,
                     'status':'TARGETS_CONFIRMED','objects':[{'class_id':0,'bbox':[0,0,10,10]}]}]}
    p={'artifacts':{'detector':'b5e475286d7703288719c52e0b31044588c0e114bd426d60057c0f695eaa3605',
                   'fusion':'b57dc4e7c9eb713c11a716c72e1087a7f3e942811779d01978527b669ef9d02b'},
       'rendering_source_sha256':'r'*64,'operating_point':{'detector_confidence_min':.15,'tiled':True,'matching_iou':.5},
       'images':[{'image_sha256':'i'*64,'objects':[{'class_id':0,'bbox':[0,0,10,10],'confidence':.8}]}]}
    return m,a,p


class EvaluationTests(unittest.TestCase):
    def test_duplicate_prediction_counts_fp_and_small_pool_cannot_pass(self):
        m,a,p=fixture();p['images'][0]['objects']*=2;r=evaluate(m,a,p)
        self.assertEqual(r['overall']['tp'],1);self.assertEqual(r['overall']['fp'],1)
        self.assertEqual(r['overall']['precision'],.5);self.assertFalse(r['accuracy_checks_passed'])
        self.assertFalse(r['public_xtf_enabled'])
    def test_wrong_class_is_fp_and_fn(self):
        m,a,p=fixture();p['images'][0]['objects'][0]['class_id']=2;r=evaluate(m,a,p)
        self.assertEqual([r['overall'][k] for k in ('tp','fp','fn')],[0,1,1])
    def test_unreviewed_missing_and_invalid_background_rejected(self):
        for change in ('UNREVIEWED','BACKGROUND_CONFIRMED'):
            m,a,p=fixture();a['annotations'][0]['status']=change
            with self.assertRaises(ValueError):evaluate(m,a,p)
        m,a,p=fixture();p['images']=[]
        with self.assertRaises(ValueError):evaluate(m,a,p)
    def test_day_leakage_and_artifact_change(self):
        m,a,p=fixture();e=copy.deepcopy(m['images'][0]);e['image_sha256']='q'*64;e['split']='DEV';m['images'].append(e)
        with self.assertRaises(ValueError):evaluate(m,a,p)
        m,a,p=fixture();p['artifacts']['detector']='0'*64
        with self.assertRaises(ValueError):evaluate(m,a,p)
    def test_boxes_and_unknown_class(self):
        for changes in ({'bbox':[0,0,200,10]},{'class_id':8},{'bbox':[0,0,float('nan'),10]}):
            m,a,p=fixture();p['images'][0]['objects'][0].update(changes)
            with self.assertRaises(ValueError):evaluate(m,a,p)
    def test_confirmed_negative_false_alarm_and_zero_denominator(self):
        m,a,p=fixture();a['annotations'][0].update(status='BACKGROUND_CONFIRMED',objects=[])
        r=evaluate(m,a,p);self.assertEqual(r['confirmed_background_images'],1)
        self.assertEqual(r['overall']['fp'],1);self.assertIsNone(r['overall']['recall'])
    def test_complete_independent_fixture_passes_checks_without_auto_release(self):
        m,a,p=fixture();m['images']=[];a['annotations']=[];p['images']=[]
        m.update(independent_external_validation=True,split_provenance_verified=True)
        for index in range(25):
            identity=f'{index:064x}';objects=[]
            if index<5:
                objects=[{'class_id':index,'bbox':[j%10*10,j//10*10,j%10*10+5,j//10*10+5]} for j in range(30)]
            m['images'].append({'image_sha256':identity,'source_sha256':'s'*64,'acquisition_group':'EXTERNAL_SYNTHETIC_TEST',
                 'day':'150603','split':'TEST','width':100,'height':100,'rendering_version':'LOG1P_PERCENTILE_V1'})
            a['annotations'].append({'image_sha256':identity,'reviewer':'SYNTHETIC_TEST_ONLY','qualified_review':True,
                 'status':'TARGETS_CONFIRMED' if objects else 'BACKGROUND_CONFIRMED','objects':copy.deepcopy(objects)})
            p['images'].append({'image_sha256':identity,'objects':[{**o,'confidence':.8} for o in objects]})
        r=evaluate(m,a,p);self.assertTrue(r['accuracy_checks_passed']);self.assertFalse(r['public_xtf_enabled'])
        self.assertEqual(r['overall']['tp'],150);self.assertEqual(r['confirmed_background_images'],20)


if __name__=='__main__':unittest.main()
