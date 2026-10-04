import tempfile,unittest,hashlib
from pathlib import Path
import cv2,numpy as np
from build_module2_curated_dataset import verify_roles,copy_record,sha

class DatasetTests(unittest.TestCase):
    def records(self):
        return [{'image':'a','image_sha256':'a','decoded_sha256':'pa','parent_sha256':'a','split':'TRAIN','box_count':1,'curation_status':'MECHANICALLY_SCREENED_INHERITED_NOT_EXPERT_APPROVED'}, {'image':'b','image_sha256':'b','decoded_sha256':'pb','parent_sha256':'b','split':'DEV','box_count':1}]
    def test_valid_roles(self):self.assertEqual(dict(verify_roles(self.records())),{'TRAIN':1,'DEV':1})
    def test_parent_leakage(self):
        rows=self.records();rows[0]['parent_sha256']='b'
        with self.assertRaises(ValueError):verify_roles(rows)
    def test_pixel_leakage(self):
        rows=self.records();rows[0]['decoded_sha256']='pb'
        with self.assertRaises(ValueError):verify_roles(rows)
    def test_no_empty_unconfirmed_train(self):
        rows=self.records();rows[0]['box_count']=0
        with self.assertRaises(ValueError):verify_roles(rows)
    def test_role_and_status_guards(self):
        for key,value in [('split','TEST'),('curation_status','HUMAN_VERIFIED')]:
            rows=self.records();rows[0][key]=value
            with self.assertRaises(ValueError):verify_roles(rows)
    def test_copy_integrity_sizes_and_no_source_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);image=root/'scene.png';label=root/'scene.txt';cv2.imwrite(str(image),np.full((64,64,3),80,dtype=np.uint8));label.write_text('0 0.5 0.5 0.02 0.02\n')
            raster=cv2.imread(str(image));r={'image':str(image),'label':str(label),'source_image':str(image),'source_label':str(label),'image_sha256':sha(image),'label_sha256':sha(label),'parent_sha256':sha(image),'source_label_sha256':sha(label),'decoded_sha256':hashlib.sha256(str(raster.shape).encode()+raster.tobytes()).hexdigest(),'box_count':1,'split':'TRAIN'}
            out=root/'out';(out/'images/train').mkdir(parents=True);(out/'labels/train').mkdir(parents=True)
            new,classes,sizes=copy_record(r,out);self.assertEqual(sha(new['label']),r['label_sha256']);self.assertEqual(classes['0'],1);self.assertEqual(sizes[('0','small')],1);self.assertEqual(sha(label),r['label_sha256'])
            label.write_text('changed')
            with self.assertRaises(ValueError):copy_record(r,out)

if __name__=='__main__':unittest.main()
