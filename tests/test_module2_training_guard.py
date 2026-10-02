import csv,hashlib,tempfile,unittest
from pathlib import Path
import yaml
from scripts.train_guarded import preflight,CANONICAL
class TrainingGuardTests(unittest.TestCase):
 def fixture(self,r):
  rows=[]
  for role,split,content in [('TRAIN','train',b'train fixture'),('DEV','val',b'dev fixture')]:
   images=r/'images'/split;images.mkdir(parents=True);labels=r/'labels'/split;labels.mkdir(parents=True)
   image=images/'a.png';image.write_bytes(content);(labels/'a.txt').write_text('0 0.5 0.5 0.2 0.2')
   rows.append(dict(image=str(image),split=role,acquisition_group=role,annotation_status='HUMAN_VERIFIED',sha256=hashlib.sha256(content).hexdigest()))
  data=r/'data.yaml';data.write_text(yaml.safe_dump(dict(path=str(r),train='images/train',val='images/val',names=CANONICAL)))
  manifest=r/'manifest.csv';self.write(manifest,rows);return data,manifest,rows
 def write(self,path,rows):
  with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 def test_hash_label_group_validated_without_training(self):
  with tempfile.TemporaryDirectory() as d:
   data,manifest,rows=self.fixture(Path(d));self.assertEqual(preflight(data,manifest)['counts'],{'train':1,'val':1})
 def test_protected_validation_directory_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);data,manifest,rows=self.fixture(r);(r/'images/val').rename(r/'images/final_test');config=yaml.safe_load(data.read_text());config['val']='images/final_test';data.write_text(yaml.safe_dump(config))
   with self.assertRaisesRegex(ValueError,'test/calibration'):preflight(data,manifest)
 def test_group_leakage_and_unreviewed_images_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   data,manifest,rows=self.fixture(Path(d));rows[1]['acquisition_group']=rows[0]['acquisition_group'];self.write(manifest,rows)
   with self.assertRaisesRegex(ValueError,'group crosses'):preflight(data,manifest)
   rows[1]['acquisition_group']='DEV';rows[1]['annotation_status']='UNREVIEWED';self.write(manifest,rows)
   with self.assertRaisesRegex(ValueError,'human-verified'):preflight(data,manifest)
 def test_hash_and_invalid_box_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);data,manifest,rows=self.fixture(r);(r/'labels/train/a.txt').write_text('0 0.9 0.5 0.8 0.2')
   with self.assertRaisesRegex(ValueError,'outside'):preflight(data,manifest)
   (r/'labels/train/a.txt').write_text('0 0.5 0.5 0.2 0.2');(r/'images/train/a.png').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'hash disagrees'):preflight(data,manifest)
