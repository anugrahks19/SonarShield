import unittest
from select_module2_operating_point import analyze,choose,curve,events,fixed,iou

class OperatingPointTests(unittest.TestCase):
    def test_tied_scores_not_split(self):
        points=curve([(.5,0,1),(.5,0,0)],1)
        self.assertEqual(len(points),1);self.assertEqual(points[0]['precision'],.5)
        self.assertIsNone(choose(points))
    def test_select_highest_recall_under_floor(self):
        points=curve([(.9,0,1),(.8,0,0),(.7,0,1),(.6,0,1),(.5,0,1),(.4,0,0)],4)
        selected=choose(points)
        self.assertEqual(selected['threshold'],.5);self.assertEqual(selected['recall'],1)
        self.assertEqual(selected['precision'],.8)
    def test_no_detections_cannot_claim_precision(self):
        self.assertIsNone(score_result:=fixed([],5)['precision']);self.assertIsNone(choose([]))
    def test_class_correct_greedy_and_duplicate(self):
        box=[0,0,10,10]
        rows=[{'gt':[{'class':0,'box':box}], 'predictions':[
            {'class':1,'confidence':.95,'box':box},
            {'class':0,'confidence':.9,'box':box},
            {'class':0,'confidence':.8,'box':box}]}]
        e,s=events(rows);self.assertEqual([v[2] for v in e],[0,1,0])
        self.assertEqual(fixed(e,1,.85)['tp'],1);self.assertEqual(fixed(e,1,.85)['fp'],1)
        self.assertEqual(iou(box,box),1)
    def test_per_class_policy_and_support(self):
        rows=[{'gt':[{'class':c,'box':[0,0,10,10]}],
               'predictions':[{'class':c,'confidence':.1*(c+1),'box':[0,0,10,10]}]} for c in range(5)]
        report=analyze(rows)
        self.assertTrue(report['all_classes_80_80_met']);self.assertEqual(report['ground_truth_boxes'],5)
        self.assertEqual(report['class_precision_floor_policy']['overall']['tp'],5)
    def test_unattainable_class_not_silently_disabled(self):
        rows=[{'gt':[{'class':c,'box':[0,0,10,10]}],
               'predictions':[] if c==0 else [{'class':c,'confidence':.9,'box':[0,0,10,10]}]} for c in range(5)]
        report=analyze(rows)
        self.assertIsNone(report['class_precision_floor_policy']);self.assertFalse(report['all_classes_80_80_met'])

if __name__=='__main__':unittest.main()
