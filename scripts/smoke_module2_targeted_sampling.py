"""Real CPU train/DEV data-loader smoke test; no model fitting or inference."""
import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch, yaml
from ultralytics.cfg import get_cfg
import train_module2_submission as ft
from module2_targeted_sampling import trainer_class

root=Path(__file__).resolve().parents[1]
cls=trainer_class(root/ft.SAMPLING,ft.SAMPLING_SHA)
trainer=cls.__new__(cls)
trainer.args=get_cfg(overrides=ft.settings(root))
trainer.device=torch.device('cpu');trainer.epoch=0
trainer.model=torch.nn.Module();trainer.model.stride=torch.tensor([4,8,16,32])
trainer.data=yaml.safe_load((root/ft.DATASET/'data.yaml').read_text())
train=trainer.get_dataloader(str(root/ft.DATASET/'images/train'),8,-1,'train')
batch=next(iter(train))
assert len(train.dataset)==9369 and len(train)==1172
assert tuple(batch['img'].shape)==(8,3,640,640)
assert torch.isfinite(batch['bboxes']).all() and ((batch['bboxes']>=0)&(batch['bboxes']<=1)).all()
assert batch['bboxes'].shape[0]>0
dev=trainer.get_dataloader(str(root/ft.DATASET/'images/val'),8,-1,'val')
assert len(dev.dataset)==1129 and not hasattr(dev.sampler,'weights')
next(iter(dev))
result={'real_cpu_loader_smoke_passed':True,'train_images':len(train.dataset),'dev_images':len(dev.dataset),
    'batches_per_epoch':len(train),'batch_shape':list(batch['img'].shape),
    'valid_transformed_boxes':len(batch['bboxes']),'train_sampler':type(train.sampler).__name__,
    'dev_sampler':type(dev.sampler).__name__,'training_calls':0,'inference_calls':0}
print(json.dumps(result,indent=2))
train.close();dev.close()
out=root/'.temp/module2-experiments/m2-smalltarget-loader-smoke-20261004.json'
out.write_text(json.dumps(result,indent=2),encoding='utf-8')
