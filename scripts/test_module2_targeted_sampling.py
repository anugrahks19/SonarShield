import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import torch
import module2_targeted_sampling as sampling
from ai.training.candidate_data import sha

class SamplingTests(unittest.TestCase):
    def test_size_uses_letterbox(self):
        self.assertEqual(sampling.memberships([(0,.5,.5,.02,.02)],1280,640),{'small_crab'})
        self.assertEqual(sampling.memberships([(0,.5,.5,.2,.2)],640,640),set())
        self.assertEqual(sampling.memberships([(2,.5,.5,.1,.1)],640,640),{'small_medium_wreck'})
    def test_probabilities_normalize_and_keep_every_image(self):
        groups=[{g} for g in sampling.GROUPS]+[set()]*10
        weights,counts=sampling.probabilities(groups)
        self.assertAlmostEqual(sum(weights),1);self.assertTrue(all(p>0 for p in weights))
        self.assertGreater(weights[0],weights[-1]);self.assertEqual(counts['small_crab'],1)
    def test_missing_group_rejected(self):
        with self.assertRaises(ValueError):sampling.probabilities([{'small_crab'}])
    def test_align_by_path_not_manifest_order_and_reject_dev(self):
        plan={'records':[{'image':'a','probability':.7},{'image':'b','probability':.3}]}
        self.assertEqual(sampling.aligned_probabilities(plan,['b','a']),[.3,.7])
        with self.assertRaises(ValueError):sampling.aligned_probabilities(plan,['a','dev'])
        with self.assertRaises(ValueError):sampling.aligned_probabilities(plan,['a','a'])
    def test_loader_epoch_repeatability_resume_and_validation(self):
        from ultralytics.models.yolo.detect import DetectionTrainer
        with tempfile.TemporaryDirectory() as d:
            files=[str(Path(d)/f'{i}.jpg') for i in range(32)]
            plan=Path(d)/'sampling.json'
            plan.write_text(json.dumps({'records':[{'image':f,'probability':1/32} for f in files]}))
            cls=sampling.trainer_class(plan,sha(plan));trainer=cls.__new__(cls)
            trainer.args=SimpleNamespace(seed=0,workers=0);trainer.epoch=0;trainer.device=torch.device('cpu')
            class Dataset:
                im_files=files
                @staticmethod
                def collate_fn(items):return items
                def __len__(self):return 32
                def __getitem__(self,index):return index
            trainer.build_dataset=lambda *a:Dataset()
            loader=trainer.get_dataloader('fixture',8,-1,'train')
            first=[x for batch in loader for x in batch]
            self.assertEqual(len(first),32);self.assertEqual(len(loader),4)
            self.assertEqual(first,[x for batch in loader for x in batch])
            trainer.epoch=1;second=[x for batch in loader for x in batch];self.assertNotEqual(first,second)
            resumed=cls.__new__(cls);resumed.args=trainer.args;resumed.device=trainer.device;resumed.epoch=1;resumed.build_dataset=trainer.build_dataset
            self.assertEqual(second,[x for batch in resumed.get_dataloader('fixture',8,-1,'train') for x in batch])
            with patch.object(DetectionTrainer,'get_dataloader',return_value='normal_validation') as normal:
                self.assertEqual(trainer.get_dataloader('dev',8,-1,'val'),'normal_validation')
                normal.assert_called_once_with('dev',8,-1,'val')
            with self.assertRaises(ValueError):trainer.get_dataloader('fixture',8,0,'train')
            plan.write_text('{}')
            with self.assertRaises(ValueError):trainer.get_dataloader('fixture',8,-1,'train')

if __name__=='__main__':unittest.main()
