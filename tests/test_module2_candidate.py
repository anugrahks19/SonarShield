import unittest
from ai.training.candidate_data import crop_bounds,project,parse_labels,text_labels


class CandidateTests(unittest.TestCase):
    def test_fractional_positive_not_rounded_to_empty(self):
        target=(4,.5,.5,.001,.002);bounds=crop_bounds(target,200,200)
        result=project([target],200,200,bounds)
        self.assertEqual(len(result),1);self.assertGreater(result[0][3],0)
        self.assertEqual(len(parse_labels(text_labels(result))),1)
    def test_all_context_objects_projected(self):
        boxes=[(0,.5,.5,.1,.1),(2,.7,.5,.1,.1),(4,.99,.99,.01,.01)]
        result=project(boxes,1000,1000,(350,350,800,650))
        self.assertEqual([b[0] for b in result],[0,2]);parse_labels(text_labels(result))
    def test_partial_box_is_bounded_to_actual_crop(self):
        result=project([(1,.5,.5,.4,.4)],100,100,(45,45,60,60))
        self.assertEqual(result,[(1,.5,.5,1.,1.)]);parse_labels(text_labels(result))
    def test_invalid_parent_not_silently_repaired(self):
        with self.assertRaises(ValueError):parse_labels('0 .128470 .602715 .319440 .236690')
        with self.assertRaises(ValueError):parse_labels('4 .5 .5 0 .2')


if __name__=='__main__':unittest.main()
