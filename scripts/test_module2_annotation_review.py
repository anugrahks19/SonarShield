import json, tempfile, unittest
from pathlib import Path
from review_module2_annotations import digest, validate, record, connect

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.image=self.root/'scene.bin';self.image.write_bytes(b'original')
        self.label=self.root/'scene.txt';self.label.write_text('label')
        self.item={'id':'0','sources':[{'image':str(self.image),'sha256':digest(self.image),'label':str(self.label),'label_sha256':digest(self.label),'width':100,'height':50}]}
        self.value={'status':'PROPOSE_CORRECTION','reviewer':'QA fixture, not real annotation','reason':'test only','boxes':[{'category':'MILCO','x':1,'y':2,'w':10,'h':8}]}
    def tearDown(self): self.temp.cleanup()
    def test_roundtrip_and_history(self):
        before=self.label.read_bytes();record(self.root,self.item,self.value);record(self.root,self.item,{**self.value,'reason':'revision'})
        with connect(self.root) as db:
            rows=db.execute('select payload from decisions order by sequence').fetchall()
        self.assertEqual(len(rows),2);self.assertEqual(json.loads(rows[-1][0])['reason'],'revision');self.assertEqual(self.label.read_bytes(),before)
        self.assertEqual(json.loads(rows[0][0])['approval'],'PROPOSAL_NOT_DATASET_APPROVAL')
    def test_reject_out_of_bounds(self):
        self.value['boxes'][0]['x']=99
        with self.assertRaises(ValueError): validate(self.item,self.value)
    def test_reject_nan(self):
        self.value['boxes'][0]['w']=float('nan')
        with self.assertRaises(ValueError): validate(self.item,self.value)
    def test_reject_background_with_boxes(self):
        self.value['status']='CONFIRM_BACKGROUND'
        with self.assertRaises(ValueError): validate(self.item,self.value)
    def test_requires_identity_and_reason(self):
        for key in ('reviewer','reason'):
            with self.assertRaises(ValueError): validate(self.item,{**self.value,key:''})
    def test_changed_image(self):
        self.image.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Source image changed'): record(self.root,self.item,self.value)
    def test_changed_annotation(self):
        self.label.write_text('changed')
        with self.assertRaisesRegex(ValueError,'Source annotation changed'): record(self.root,self.item,self.value)
    def test_no_empty_positive_correction(self):
        with self.assertRaises(ValueError): validate(self.item,{**self.value,'boxes':[]})
    def test_native_semantics_preserved(self):
        self.assertEqual(validate(self.item,self.value)['boxes'][0]['category'],'MILCO')

if __name__=='__main__': unittest.main()
