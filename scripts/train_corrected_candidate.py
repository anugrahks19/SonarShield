"""Pinned exploratory revision only. No fitting without user --execute."""
import argparse,collections,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import yaml
from ai.training.candidate_data import NAMES,sha,parse_labels


def preflight(dataset,weights):
    dataset=Path(dataset).resolve();weights=Path(weights).resolve()
    ready=json.loads((dataset/'READY.json').read_text(encoding='utf-8'))
    if sha(dataset/'manifest.json')!=ready['manifest_sha256'] or sha(dataset/'data.yaml')!=ready['data_sha256']:
        raise ValueError('Dataset identity changed; prepare a new revision.')
    manifest=json.loads((dataset/'manifest.json').read_text(encoding='utf-8'))
    if manifest['purpose']!='CONTROLLED_EXPLORATORY_TRAINING_NOT_FINAL_ACCURACY_CERTIFICATION':raise ValueError('Wrong dataset purpose.')
    if sha(weights)!=manifest['weights_sha256'] or sha(weights)!='b5e475286d7703288719c52e0b31044588c0e114bd426d60057c0f695eaa3605':raise ValueError('Starting checkpoint changed.')
    conf=yaml.safe_load((dataset/'data.yaml').read_text(encoding='utf-8'))
    if Path(conf['path']).resolve()!=dataset or conf['train']!='images/train' or conf['val']!='images/val' or conf['names']!=NAMES or conf.get('test'):
        raise ValueError('Only the pinned TRAIN/DEV paths and canonical classes are allowed.')
    roles=collections.defaultdict(set);pixels=collections.defaultdict(set);parents=collections.defaultdict(set);counts=collections.Counter();classes=collections.defaultdict(collections.Counter)
    paths=set();labels=set()
    for r in manifest['records']:
        role=r['split'];split='train' if role=='TRAIN' else 'val' if role=='DEV' else None
        if split is None:raise ValueError('Protected role cannot enter training.')
        image=Path(r['image']).resolve();label=Path(r['label']).resolve()
        if image.parent!=dataset/'images'/split or label.parent!=dataset/'labels'/split or label.stem!=image.stem:
            raise ValueError('Image/label path pairing mismatch.')
        if image in paths or label in labels:raise ValueError('Duplicate path.')
        paths.add(image);labels.add(label)
        if sha(image)!=r['image_sha256'] or sha(label)!=r['label_sha256']:raise ValueError('Image or annotation changed.')
        if sha(r['source_image'])!=r['parent_sha256'] or sha(r['source_label'])!=r['source_label_sha256']:
            raise ValueError('Source image/annotation changed since preparation.')
        boxes=parse_labels(label.read_text(encoding='utf-8'))
        if len(boxes)!=r['box_count']:raise ValueError('Annotation count differs from manifest.')
        if 'crop_bounds_xyxy' in r and not boxes:raise ValueError('Hard-positive crop became background.')
        roles[r['image_sha256']].add(role);pixels[r['decoded_sha256']].add(role);parents[r['parent_sha256']].add(role)
        counts[role]+=1;classes[role].update(b[0] for b in boxes)
    if any(len(s)>1 for s in list(roles.values())+list(pixels.values())+list(parents.values())):raise ValueError('Exact byte/pixel/parent overlap across TRAIN/DEV.')
    actual={p.resolve() for split in ['train','val'] for p in (dataset/'images'/split).iterdir()}
    actual_labels={p.resolve() for split in ['train','val'] for p in (dataset/'labels'/split).iterdir()}
    if paths!=actual or labels!=actual_labels:raise ValueError('Unmanifested or missing image/label files.')
    if any(classes[role][c]==0 for role in ['TRAIN','DEV'] for c in NAMES):raise ValueError('A class has no TRAIN/DEV targets.')
    return {'counts':dict(counts),'class_box_counts':{k:dict(v) for k,v in classes.items()},'manifest_sha256':ready['manifest_sha256'],
            'purpose':manifest['purpose'],'final_test_independence':'NOT_CERTIFIED','xtf_accuracy':'NOT_ESTABLISHED'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,default=Path('datasets/controlled_v8a_20261003'))
    p.add_argument('--weights',type=Path,default=Path('models/v6/detector_v6_p2_sss/weights/best.pt'))
    p.add_argument('--epochs',type=int,default=80);p.add_argument('--device',default='0');p.add_argument('--batch',type=int,default=8)
    p.add_argument('--name',default='v8a_labels_fixed_01');p.add_argument('--execute',action='store_true');a=p.parse_args()
    try:
        if not 1<=a.epochs<=1000 or not 1<=a.batch<=32 or Path(a.name).name!=a.name or a.name in {'','.'}:
            raise ValueError('Invalid bounded training options.')
        result=preflight(a.dataset,a.weights);print(json.dumps(result),flush=True)
        if not a.execute:print('PREFLIGHT PASSED. No training started.');sys.exit(0)
        project=Path(__file__).resolve().parents[1]/'models/controlled'
        if (project/a.name).exists():raise ValueError('Run already exists; use a new --name.')
        from ultralytics import YOLO
        model=YOLO(str(a.weights))
        if model.names!=NAMES:raise ValueError('Checkpoint classes disagree.')
        model.train(data=str(a.dataset.resolve()/'data.yaml'),epochs=a.epochs,device=a.device,batch=a.batch,
            project=str(project),name=a.name,exist_ok=False,imgsz=640,workers=0,optimizer='AdamW',lr0=.001,lrf=.01,
            hsv_h=0.,hsv_s=0.,hsv_v=0.,degrees=5.,translate=.1,scale=.5,shear=0.,perspective=0.,
            flipud=0.,fliplr=.5,mosaic=.8,mixup=.1,auto_augment=None,erasing=0.,close_mosaic=10,
            seed=0,deterministic=True,amp=True,patience=20)
    except (ValueError,OSError,KeyError) as e:p.exit(2,f'BLOCKED: {e}\n')
