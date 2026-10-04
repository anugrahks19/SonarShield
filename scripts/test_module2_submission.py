import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import train_module2_submission as ft

class DeadlineTests(unittest.TestCase):
    def test_bounded_settings(self):
        a=ft.settings(Path('fixture').resolve());self.assertEqual(a['epochs'],15);self.assertEqual(a['patience'],5);self.assertEqual(a['lr0'],.0001);self.assertEqual(a['mosaic'],0);self.assertEqual(a['save_period'],1);self.assertEqual(ft.BUDGET_SECONDS,4500);self.assertEqual(a['mixup'],0);self.assertEqual(a['scale'],.2);self.assertEqual(a['translate'],.05)
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'models/controlled'/ft.RUN).mkdir(parents=True)
            with self.assertRaises(ValueError):ft.validate_run(root,False)
    def test_starting_from_d1(self):self.assertEqual(ft.WEIGHTS,'models/controlled/m2_d1_curated_r01_640_01/weights/best.pt')
    def test_budget_stop_after_save_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'models/controlled'/ft.RUN;run.mkdir(parents=True)
            callbacks={};model=Mock();model.names=ft.NAMES;model.add_callback.side_effect=lambda n,c:callbacks.update({n:c})
            e={'mode':'FRESH_SUBMISSION','checkpoint':'fixture','settings':ft.settings(root),'training_started':False}
            with patch.object(ft,'validate_run'),patch.object(ft,'verify_pins'):ft.execute(root,e,lambda _:model)
            trainer=Mock();trainer.save_dir=str(run);trainer.epoch=4;trainer.stop=False
            with patch.object(ft.time,'monotonic',return_value=100):callbacks['on_train_start'](trainer)
            with patch.object(ft.time,'monotonic',return_value=4599):callbacks['on_fit_epoch_end'](trainer)
            self.assertFalse(trainer.stop)
            with patch.object(ft.time,'monotonic',return_value=4600):callbacks['on_fit_epoch_end'](trainer)
            self.assertTrue(trainer.stop);self.assertTrue((run/'budget-stop.json').exists())
    def test_completed_resume_rejected(self):
        with self.assertRaises(ValueError):ft.validate_resume_checkpoint({'optimizer':{},'epoch':14},Path('fixture'))

if __name__=='__main__':unittest.main()
