import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import train_module2_d1 as d1

class D1Tests(unittest.TestCase):
    def test_fresh_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'models/controlled'/d1.RUN).mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'exists'):d1.validate_run(root,False)
    def test_missing_resume_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'No D1'):d1.validate_run(Path(d),True)
    def test_resume_metadata_pins(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'models/controlled'/d1.RUN;(run/'weights').mkdir(parents=True);(run/'weights/last.pt').write_bytes(b'fixture')
            saved={'manifest_sha256':d1.MANIFEST,'data_sha256':d1.YAML,'settings':d1.settings(root)}
            (run/'m2-experiment.json').write_text(json.dumps(saved));self.assertEqual(d1.validate_run(root,True),run/'weights/last.pt')
            saved['settings']['batch']=4;(run/'m2-experiment.json').write_text(json.dumps(saved))
            with self.assertRaises(ValueError):d1.validate_run(root,True)
    def test_resume_optimizer_epoch_and_config(self):
        root=Path('fixture').resolve();ckpt={'optimizer':{},'epoch':10,'train_args':d1.settings(root)}
        self.assertEqual(d1.validate_resume_checkpoint(ckpt,root),11)
        for changed in ({'optimizer':None},{'epoch':79},{'train_args':{}}):
            with self.assertRaises(ValueError):d1.validate_resume_checkpoint({**ckpt,**changed},root)
    def test_fresh_and_resume_dispatch_without_fitting(self):
        root=Path('fixture').resolve()
        for mode in ('FRESH_D1','RESUME'):
            model=Mock();model.names=d1.NAMES;factory=Mock(return_value=model)
            evidence={'mode':mode,'checkpoint':'fixture.pt','settings':d1.settings(root)}
            with patch.object(d1,'validate_run'),patch.object(d1,'verify_pins'):d1.execute(root,evidence,factory)
            if mode=='RESUME':model.train.assert_called_once_with(resume=True)
            else:model.train.assert_called_once_with(**d1.settings(root))
    def test_wrong_model_classes_prevent_train(self):
        model=Mock();model.names={0:'wrong'}
        with patch.object(d1,'validate_run'),patch.object(d1,'verify_pins'):
            with self.assertRaises(ValueError):d1.execute(Path('fixture'),{'mode':'FRESH_D1','checkpoint':'fixture'},lambda _:model)
        model.train.assert_not_called()
    def test_fixed_recovery_and_control(self):
        args=d1.settings(Path('fixture').resolve());self.assertEqual(args['save_period'],1);self.assertEqual(args['imgsz'],640);self.assertEqual(args['batch'],8);self.assertEqual(args['epochs'],80);self.assertFalse(args['exist_ok'])
    def test_callback_persists_start_state_without_fitting(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'models/controlled'/d1.RUN;run.mkdir(parents=True)
            callbacks={};model=Mock();model.names=d1.NAMES;model.add_callback.side_effect=lambda name,callback:callbacks.update({name:callback})
            evidence={'mode':'FRESH_D1','checkpoint':'fixture','settings':d1.settings(root),'training_started':False}
            with patch.object(d1,'validate_run'),patch.object(d1,'verify_pins'):d1.execute(root,evidence,lambda _:model)
            trainer=Mock();trainer.save_dir=str(run)
            callbacks['on_pretrain_routine_start'](trainer);self.assertFalse(json.loads((run/'m2-experiment.json').read_text())['training_started'])
            callbacks['on_train_start'](trainer);self.assertTrue(json.loads((run/'m2-experiment.json').read_text())['training_started'])
            trainer.save_dir=str(root/'wrong')
            with self.assertRaises(ValueError):callbacks['on_train_start'](trainer)

if __name__=='__main__':unittest.main()
