import copy,unittest
from freeze_module2_candidate import validate_selection

def fixture():
    point={'threshold':.4,'precision':.8,'recall':.4,'tp':4,'fp':1,'fn':6}
    return {'selected_precision_floor_candidate':{'model':'M2.08','scope':'EXPLORATORY_DEV_NOT_PRODUCTION_APPROVED',
        'policy':'GLOBAL','deployed':False,'calibrated_probability':False,'thresholds':{str(i):.4 for i in range(5)},'metrics':point},
        'models':{'M2.08':{'best_global_recall_at_precision_80':point}}}

class FreezeTests(unittest.TestCase):
    def test_valid_selection(self):self.assertEqual(validate_selection(fixture())['model'],'M2.08')
    def test_reject_calibration_deployment_and_unknown_model(self):
        for key,value in [('deployed',True),('calibrated_probability',True),('model','untrusted')]:
            r=fixture();r['selected_precision_floor_candidate'][key]=value
            with self.assertRaises(ValueError):validate_selection(r)
    def test_missing_mismatched_thresholds_rejected(self):
        for thresholds in [{'0':.4},{str(i):(.5 if i==1 else .4) for i in range(5)}]:
            r=fixture();r['selected_precision_floor_candidate']['thresholds']=thresholds
            with self.assertRaises(ValueError):validate_selection(r)
    def test_fabricated_metrics_rejected(self):
        r=copy.deepcopy(fixture());r['selected_precision_floor_candidate']['metrics']=dict(r['selected_precision_floor_candidate']['metrics'],precision=.95)
        with self.assertRaises(ValueError):validate_selection(r)

if __name__=='__main__':unittest.main()
