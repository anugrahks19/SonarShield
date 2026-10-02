"""Training preflight; fitting requires explicit --execute after manifest validation."""
import argparse,csv,json,sys
from pathlib import Path
CANONICAL={0:'crab_pot',1:'submarine_pipeline',2:'shipwreck',3:'ghost_net',4:'mine_cylinder'}
def preflight(data,manifest):
 import yaml
 data=Path(data).resolve();config=yaml.safe_load(data.read_text(encoding='utf-8'));names=config.get('names',{})
 if isinstance(names,list):names=dict(enumerate(names))
 if names!=CANONICAL:raise ValueError('Dataset class IDs do not match the frozen five-class identity.')
 root=Path(config.get('path',data.parent));root=root if root.is_absolute() else data.parent/root
 split_paths={}
 for split in ['train','val']:
  value=config.get(split)
  if not isinstance(value,str):raise ValueError('This preflight supports one image directory per train/val split.')
  path=Path(value);path=path if path.is_absolute() else root/path
  if not path.is_dir():raise ValueError(f'{split} image directory is missing.')
  if split=='val' and any('test' in part.lower() or 'calib' in part.lower() for part in path.parts):raise ValueError('Training validation points to a test/calibration directory. Create a separate DEV configuration.')
  split_paths[split]=path.resolve()
 with Path(manifest).open(encoding='utf-8',newline='') as stream: rows=list(csv.DictReader(stream))
 required={'image','split','acquisition_group','annotation_status','sha256'}
 if not rows or not required.issubset(rows[0]):raise ValueError('Manifest requires image, split, acquisition_group, annotation_status and sha256.')
 groups={};identities={};images={}
 for row in rows:
  role=row['split'];group=row['acquisition_group'];hash_=row['sha256']
  if role not in {'TRAIN','DEV','CALIB','FINAL_TEST','HISTORICAL_TEST'} or not group or len(hash_)!=64:raise ValueError('Invalid or unresolved split/group/source hash.')
  if len(set(hash_.lower())-set('0123456789abcdef')):raise ValueError('Invalid SHA-256.')
  if group in groups and groups[group]!=role:raise ValueError('Acquisition group crosses protected split boundaries.')
  if hash_ in identities and identities[hash_]!=role:raise ValueError('Duplicate image crosses split boundaries.')
  groups[group]=role;identities[hash_]=role
  path=Path(row['image']).resolve()
  if path in images:raise ValueError('Duplicate manifest image.')
  images[path]=row
 from hashlib import sha256
 count={}
 for split,directory in split_paths.items():
  paths=sorted(p for p in directory.rglob('*') if p.suffix.lower() in {'.jpg','.jpeg','.png'})
  if not paths:raise ValueError('Training/DEV directory is empty.')
  count[split]=len(paths)
  for image in paths:
   row=images.get(image.resolve());role='TRAIN' if split=='train' else 'DEV'
   if row is None or row['split']!=role or row['annotation_status']!='HUMAN_VERIFIED':raise ValueError(f'{split}: image lacks a human-verified manifest entry: {image.name}')
   if sha256(image.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Manifest image hash disagrees.')
   relative=image.relative_to(directory);label=directory.parent/'labels'/relative.with_suffix('.txt') if directory.name=='images' else directory.parent.parent/'labels'/split/relative.with_suffix('.txt')
   if not label.is_file():raise ValueError(f'Explicit verified label file missing: {label}')
   for line in label.read_text().splitlines():
    values=line.split()
    if len(values)!=5:raise ValueError('Only YOLO detection boxes are supported.')
    klass=int(values[0]);coords=list(map(float,values[1:]))
    if klass not in CANONICAL or not all(0<=x<=1 for x in coords) or coords[2]<=0 or coords[3]<=0:raise ValueError('Invalid annotation class/box.')
    cx,cy,w,h=coords
    if cx-w/2 < -1e-6 or cy-h/2 < -1e-6 or cx+w/2>1+1e-6 or cy+h/2>1+1e-6:raise ValueError('Annotation lies outside image.')
 return {'data':str(data),'counts':count,'acquisition_groups':len(groups),'checks':'HASH_LABEL_AND_GROUP_PREFLIGHT_NOT_FULL_PROVENANCE_CERTIFICATION'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',required=True,type=Path);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--weights',required=True,type=Path);p.add_argument('--epochs',type=int,default=80);p.add_argument('--device',default='0');p.add_argument('--project',default='models/controlled');p.add_argument('--name',default='candidate');p.add_argument('--execute',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 try:
  if a.execute and a.dry_run:raise ValueError('Choose execute OR dry-run.')
  if not a.weights.is_file():raise ValueError('Starting weights are missing.')
  if not 1<=a.epochs<=1000:raise ValueError('epochs must be 1-1000')
  result=preflight(a.data,a.manifest);print(json.dumps(result))
  if a.execute:
   from ultralytics import YOLO
   model=YOLO(str(a.weights))
   if model.names!=CANONICAL:raise ValueError('Checkpoint class IDs disagree.')
   model.train(data=str(a.data),epochs=a.epochs,device=a.device,project=a.project,name=a.name,exist_ok=False,imgsz=640,batch=8,workers=0,seed=0,deterministic=True)
  else:print('PREFLIGHT ONLY: no model fitting executed. Full provenance, near-duplicate audit and evaluation protocol remain separate gates.')
 except (ValueError,OSError) as error:p.exit(2,f'BLOCKED: {error}\n')
