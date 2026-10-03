import importlib.util,tempfile,unittest
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'scripts/audit_module2_data.py'
spec=importlib.util.spec_from_file_location('audit_module2_data',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class AuditTests(unittest.TestCase):
    def test_zero_extent_and_outside_boxes_are_errors(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'label.txt';path.write_text('0 .5 .5 0 .1\n2 .99 .5 .2 .1\n4 .5 .5 .2 .2\n')
            counts,errors,empty=module.label_summary(path)
            self.assertEqual(counts,{4:1});self.assertEqual(len(errors),2);self.assertFalse(empty)
    def test_empty_is_not_verified_background_and_missing_is_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'label.txt';self.assertEqual(module.label_summary(path)[1],['MISSING_LABEL'])
            path.write_text('');self.assertTrue(module.label_summary(path)[2])
    def test_nonfinite_and_unknown_classes(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'label.txt';path.write_text('0 nan .5 .2 .2\n8 .5 .5 .2 .2\n')
            self.assertEqual(len(module.label_summary(path)[1]),2)


if __name__=='__main__':unittest.main()
