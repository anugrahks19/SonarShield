"""Pinned M2.08 exploratory D2. User --execute required; resume is separate."""
import argparse, contextlib, json, os, shutil, sys
from datetime import datetime,timezone
from importlib.metadata import version
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import NAMES,sha
from train_corrected_candidate import preflight as integrity_preflight

ROOT=Path(__file__).resolve().parents[1]
DATASET='datasets/mechanically_curated_r01_20261003'
RUN='m2_d2_curated_r01_mosaic0_640_01'
MANIFEST='f2f8fff98d631725cd3066726056943bc9b2910abce49a380cc6521f7205f796'
YAML='6a091d635edc4dce462dd7a10ca631f3c6f0c8f77c7b2e5d539f75e57ecfda33'
WEIGHTS='models/v6/detector_v6_p2_sss/weights/best.pt'
VERSIONS={'ultralytics':'8.4.163','torch':'2.4.1+cu121','numpy':'1.26.4','PyYAML':'6.0.1'}

def settings(root):
    return dict(data=str((root/DATASET/'data.yaml').resolve()),epochs=80,device='0',batch=8,
        project=str((root/'models/controlled').resolve()),name=RUN,exist_ok=False,imgsz=640,
        workers=0,optimizer='AdamW',lr0=.001,lrf=.01,hsv_h=0.,hsv_s=0.,hsv_v=0.,
        degrees=5.,translate=.1,scale=.5,shear=0.,perspective=0.,flipud=0.,fliplr=.5,
        mosaic=0.0,mixup=.1,auto_augment=None,erasing=0.,close_mosaic=10,seed=0,
        deterministic=True,amp=True,patience=20,save=True,save_period=1,cache=False)

def verify_pins(root):
    dataset=root/DATASET
    if sha(dataset/'manifest.json')!=MANIFEST or sha(dataset/'data.yaml')!=YAML:raise ValueError('D2 dataset pins changed; do not reuse this experiment identity.')
    status=json.loads((dataset/'BUILD_STATUS.json').read_text(encoding='utf-8'))
    if status['status']!='COMPLETE_INTEGRITY_VERIFIED_NOT_EXPERT_APPROVED':raise ValueError('Dataset build is incomplete.')

def validate_run(root,resume):
    run=root/'models/controlled'/RUN
    if not resume:
        if run.exists():raise ValueError('D2 run exists. Use --resume --execute after an interruption; never overwrite it.')
        return root/WEIGHTS
    checkpoint=run/'weights/last.pt'
    if not checkpoint.is_file():raise ValueError('No D2 last.pt to resume. This command cannot resume the older baseline.')
    saved=json.loads((run/'m2-experiment.json').read_text(encoding='utf-8'))
    if saved['manifest_sha256']!=MANIFEST or saved['data_sha256']!=YAML or saved['settings']!=settings(root):raise ValueError('D2 experiment settings changed.')
    return checkpoint

def validate_resume_checkpoint(checkpoint,root):
    if checkpoint.get('optimizer') is None:raise ValueError('Checkpoint optimizer missing; exact resume unavailable.')
    epoch=checkpoint.get('epoch',-1)
    if not isinstance(epoch,int) or epoch<0 or epoch>=79:raise ValueError('D2 already finished or checkpoint has no resumable epoch.')
    args=checkpoint.get('train_args',{})
    for key,value in settings(root).items():
        actual=args.get(key)
        if key in ('data','project'):
            if actual is None or Path(actual).resolve()!=Path(value).resolve():raise ValueError('Resume checkpoint path mismatch: '+key)
        elif actual!=value:raise ValueError('Resume checkpoint configuration mismatch: '+key)
    return epoch+1

def preflight(root,resume=False):
    print('1/4 Checking pinned dataset, run identity and installed versions...',flush=True)
    verify_pins(root);checkpoint=validate_run(root,resume)
    installed={name:version(name) for name in VERSIONS}
    if installed!=VERSIONS:raise ValueError('Installed package versions changed. No automatic installations are performed.')
    print('2/4 Verifying 10,498 image/label pairs and parent identities. This can take a minute...',flush=True)
    evidence=integrity_preflight(root/DATASET,root/WEIGHTS)
    print('3/4 Checking GPU and checkpoint metadata. No fitting or inference...',flush=True)
    import torch
    if not torch.cuda.is_available():raise ValueError('CUDA GPU unavailable; this experiment is pinned to GPU 0.')
    gpu=torch.cuda.get_device_name(0)
    saved=torch.load(checkpoint,map_location='cpu',weights_only=False)
    model=saved.get('ema') or saved.get('model')
    if model is None or model.names!=NAMES:raise ValueError('Checkpoint class IDs disagree.')
    strides=[int(s) for s in model.stride.tolist()]
    if strides!=[4,8,16,32]:raise ValueError('Expected P2 detector strides 4/8/16/32.')
    completed=validate_resume_checkpoint(saved,root) if resume else 0
    del model,saved
    free=shutil.disk_usage(root).free
    required=(82-completed)*(root/WEIGHTS).stat().st_size*6+2*1024**3
    if free<required:raise ValueError('Insufficient disk headroom for per-epoch checkpoints. Free disk space before launch.')
    print('4/4 PREFLIGHT PASSED. Exploratory scope; no accuracy guarantee.',flush=True)
    return {'phase':'M2.08','mode':'RESUME' if resume else 'FRESH_D2','manifest_sha256':MANIFEST,
        'data_sha256':YAML,'checkpoint':str(checkpoint),'checkpoint_sha256':sha(checkpoint),
        'completed_epochs_before_resume':completed,'settings':settings(root),'versions':installed,
        'gpu':gpu,'detector_strides':strides,'dataset_preflight':evidence,'scientifically_approved':False,
        'disk_free_bytes':free,'estimated_required_disk_bytes':required,
        'confirmed_negative_images':0,'small_target_sampling_change':False,
        'major_factor_changed':'MOSAIC_0_8_TO_0_0_ONLY_VERSUS_D1','training_started':False}

class Tee:
    def __init__(self,console,file):self.console,self.file=console,file
    def write(self,text):self.console.write(text);self.file.write(text);self.file.flush();return len(text)
    def flush(self):self.console.flush();self.file.flush()
    def __getattr__(self,key):return getattr(self.console,key)

def execute(root,evidence,model_factory=None):
    # Re-check immediately before fitting. No existing run can be silently replaced.
    resume=evidence['mode']=='RESUME';validate_run(root,resume);verify_pins(root)
    if model_factory is None:
        from ultralytics import YOLO
        model_factory=YOLO
    model=model_factory(evidence['checkpoint'])
    if model.names!=NAMES:raise ValueError('Model names changed before launch.')
    run=root/'models/controlled'/RUN
    def persist_experiment(trainer):
        save=Path(trainer.save_dir).resolve()
        if save!=run.resolve():raise ValueError('Unexpected run directory; refusing redirected experiment.')
        (save/'m2-experiment.json').write_text(json.dumps({**evidence,'launch_requested':True},indent=2),encoding='utf-8')
    def mark_training_started(trainer):
        save=Path(trainer.save_dir).resolve()
        if save!=run.resolve():raise ValueError('Unexpected run directory.')
        (save/'m2-experiment.json').write_text(json.dumps({**evidence,'launch_requested':True,'training_started':True,'received_at':datetime.now(timezone.utc).isoformat()},indent=2),encoding='utf-8')
    model.add_callback('on_pretrain_routine_start',persist_experiment)
    model.add_callback('on_train_start',mark_training_started)
    if resume:model.train(resume=True)
    else:model.train(**evidence['settings'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    if not args.resume:
        parser.exit(2, 'Superseded by the submission deadline plan. Use scripts/train_module2_submission.py; do not start the old 80-epoch D2.\n')
    log=None
    try:
        if args.execute:
            logs=ROOT/'.temp/module2-training-logs';logs.mkdir(parents=True,exist_ok=True)
            timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            path=logs/f'{RUN}-{timestamp}-{os.getpid()}.log';log=path.open('x',encoding='utf-8',buffering=1)
            print(f'Console log: {path}',flush=True)
        with contextlib.ExitStack() as stack:
            if log:
                stack.enter_context(contextlib.redirect_stdout(Tee(sys.stdout,log)))
                stack.enter_context(contextlib.redirect_stderr(Tee(sys.stderr,log)))
            evidence=preflight(ROOT,args.resume)
            out=ROOT/'.temp/module2-experiments';out.mkdir(parents=True,exist_ok=True)
            (out/(RUN+('-resume-preflight.json' if args.resume else '-preflight.json'))).write_text(json.dumps(evidence,indent=2),encoding='utf-8')
            if not args.execute:print('No training started. Add --execute only when you are ready to run D2.',flush=True);return
            print('Starting user-requested D2. Keep this terminal open; epoch checkpoints are saved each epoch.',flush=True)
            execute(ROOT,evidence)
    except KeyboardInterrupt:
        print('\nInterrupted. Resume from this D2 run using --resume --execute once the process has stopped.',flush=True);raise SystemExit(130)
    except Exception as error:
        message=f'BLOCKED/FAILED: {type(error).__name__}: {error}'
        print(message,file=sys.stderr,flush=True)
        if log:log.write(message+'\n');log.flush()
        raise SystemExit(2)
    finally:
        if log:log.close()

if __name__=='__main__':main()
