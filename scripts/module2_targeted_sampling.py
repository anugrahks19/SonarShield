"""TRAIN-only bounded resampling. No new labels, crops, DEV sampling or fitting."""
import argparse, collections, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import parse_labels, sha

GROUPS = ('small_crab', 'small_medium_wreck', 'pipeline', 'net', 'mine')
UNIFORM_MASS = .4
GROUP_MASS = dict(small_crab=.25, small_medium_wreck=.15, pipeline=.05, net=.05, mine=.10)

def memberships(boxes, width, height):
    if width <= 0 or height <= 0: raise ValueError('Invalid image dimensions.')
    groups = set()
    gain = 640 / max(width, height)
    for c, x, y, w, h in boxes:
        area = w * width * h * height * gain * gain
        if c == 0 and area < 32 ** 2: groups.add('small_crab')
        if c == 2 and area < 96 ** 2: groups.add('small_medium_wreck')
        if c in (1, 3, 4): groups.add({1:'pipeline', 3:'net', 4:'mine'}[c])
    return groups

def probabilities(groups):
    if not groups: raise ValueError('Empty TRAIN.')
    counts = collections.Counter(g for entry in groups for g in entry)
    if any(counts[g] == 0 for g in GROUPS): raise ValueError('Missing targeted group.')
    n = len(groups)
    result = [UNIFORM_MASS / n + sum(GROUP_MASS[g] / counts[g] for g in entry) for entry in groups]
    if not math.isclose(sum(result), 1, abs_tol=1e-10): raise ValueError('Sampling mass incorrect.')
    return result, dict(counts)

def build_plan(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Sampling plan exists; never overwrite experiment evidence.')
    data = root / 'datasets/mechanically_curated_r01_20261003'
    manifest = json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    records = [r for r in manifest['records'] if r['split'] == 'TRAIN']
    images, groups, boxes_by_image = [], [], []
    for r in records:
        image, label = Path(r['image']).resolve(), Path(r['label']).resolve()
        if image.parent != data/'images/train' or label.parent != data/'labels/train':
            raise ValueError('Non-TRAIN path in sampling preparation.')
        if sha(label) != r['label_sha256']: raise ValueError('TRAIN label drift.')
        boxes = parse_labels(label.read_text(encoding='utf-8'))
        images.append(str(image)); boxes_by_image.append(boxes)
        groups.append(memberships(boxes, r['width'], r['height']))
    if len(set(images)) != len(images): raise ValueError('Duplicate image.')
    weights, counts = probabilities(groups)
    expected_images = {g:len(records)*sum(p for p, gs in zip(weights, groups) if g in gs) for g in GROUPS}
    expected_boxes = {str(c):len(records)*sum(p*sum(b[0]==c for b in bs)
                     for p, bs in zip(weights, boxes_by_image)) for c in range(5)}
    plan = {'version':1, 'scope':'TRAIN_ONLY_EXPLORATORY_NOT_EXPERT_APPROVED',
        'manifest_sha256':sha(data/'manifest.json'), 'samples_per_epoch':len(records),
        'uniform_mass':UNIFORM_MASS, 'group_mass':GROUP_MASS, 'targeted_mass':1-UNIFORM_MASS, 'group_counts':counts,
        'uniform_image_draws_by_group':counts, 'expected_image_draws_by_group':expected_images, 'expected_box_presentations_by_class':expected_boxes,
        'note':'Expectations before augmentation, not new independent samples or measured accuracy.',
        'dev_images_unchanged':manifest['dev_images'], 'source_labels_changed':0,
        'records':[{'image':i,'probability':p,'groups':sorted(gs)} for i,p,gs in zip(images,weights,groups)]}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(plan,indent=2),encoding='utf-8')
    return {k:v for k,v in plan.items() if k!='records'} | {'sampling_sha256':sha(output)}

def aligned_probabilities(plan, image_files):
    table = {str(Path(r['image']).resolve()):r['probability'] for r in plan['records']}
    keys = [str(Path(i).resolve()) for i in image_files]
    if len(table)!=len(plan['records']) or len(set(keys))!=len(keys) or set(keys)!=set(table):
        raise ValueError('Trainer image list differs from pinned TRAIN sampling plan.')
    weights = [table[k] for k in keys]
    if not all(math.isfinite(w) and w>0 for w in weights) or not math.isclose(sum(weights),1,abs_tol=1e-8):
        raise ValueError('Invalid sampling probabilities.')
    return weights

def trainer_class(plan_path, expected_sha):
    # Lazy imports: preparation does not initialize CUDA or train a model.
    import torch
    from ultralytics.models.yolo.detect import DetectionTrainer
    class EpochSampler(torch.utils.data.Sampler):
        def __init__(self,weights,trainer): self.weights=torch.tensor(weights,dtype=torch.double);self.trainer=trainer
        def __len__(self): return len(self.weights)
        def __iter__(self):
            generator=torch.Generator().manual_seed(int(self.trainer.args.seed)+int(self.trainer.epoch))
            return iter(torch.multinomial(self.weights,len(self),replacement=True,generator=generator).tolist())
    class ResettableLoader(torch.utils.data.DataLoader):
        def close(self): pass
        def reset(self): pass  # workers=0; each epoch creates a fresh iterator.
    class TargetedTrainer(DetectionTrainer):
        def get_dataloader(self,dataset_path,batch_size=16,rank=-1,mode='train'):
            if mode!='train': return super().get_dataloader(dataset_path,batch_size,rank,mode)
            if rank!=-1 or self.args.workers!=0: raise ValueError('Targeted experiment requires single GPU and workers=0.')
            if sha(plan_path)!=expected_sha: raise ValueError('Sampling plan changed before loader initialization.')
            plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
            dataset=self.build_dataset(dataset_path,mode,batch_size)
            weights=aligned_probabilities(plan,dataset.im_files)
            sampler=EpochSampler(weights,self)
            return ResettableLoader(dataset,batch_size=min(batch_size,len(dataset)),sampler=sampler,
                num_workers=0,pin_memory=self.device.type=='cuda',collate_fn=dataset.collate_fn)
    return TargetedTrainer

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build_plan(a.root,a.output),indent=2),flush=True)
