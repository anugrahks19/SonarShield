import tempfile, unittest
from pathlib import Path
from prepare_module2_automatic_handoff import exclusions,verify_record,sha

class HandoffTests(unittest.TestCase):
    def test_protected_parent_propagates_to_crop(self):
        r={'image_sha256':'crop','parent_sha256':'parent','box_count':1}
        self.assertIn('HISTORICAL_TEST_OR_BACKGROUND_IDENTITY_OR_PARENT',exclusions(r,set(),{'parent'},set(),set(),set()))
    def test_near_quarantine_is_not_duplicate_claim(self):
        r={'image_sha256':'image','parent_sha256':'parent','box_count':1}
        self.assertEqual(exclusions(r,{'image'},set(),set(),set(),set()),['SIMILARITY_QUARANTINE_NOT_PROVEN_DUPLICATE'])
    def test_empty_is_not_negative(self):
        r={'image_sha256':'image','parent_sha256':'parent','box_count':0}
        self.assertIn('EMPTY_LABEL_NOT_CONFIRMED_BACKGROUND',exclusions(r,set(),set(),set(),set(),set()))
    def test_dev_and_native_bad_parent_excluded(self):
        r={'image_sha256':'crop','parent_sha256':'parent','box_count':1}
        reasons=exclusions(r,set(),set(),{'parent'},{'parent'},set())
        self.assertEqual(len(reasons),2)
    def test_source_drift_and_class_counts(self):
        with tempfile.TemporaryDirectory() as d:
            image=Path(d)/'image';image.write_bytes(b'bytes');label=Path(d)/'label';label.write_text('0 0.5 0.5 0.2 0.2\n')
            r={'image':str(image),'image_sha256':sha(image),'label':str(label),'label_sha256':sha(label),'source_image':str(image),'parent_sha256':sha(image),'source_label':str(label),'source_label_sha256':sha(label),'box_count':1}
            errors,counts=verify_record(r);self.assertEqual(errors,[]);self.assertEqual(counts['0'],1)
            label.write_text('0 0.5 0.5 2 2\n');errors,_=verify_record(r);self.assertTrue(errors)

if __name__=='__main__':unittest.main()
