"""Read-only M2.01 audit. No inference, fitting, moving or relabeling."""
import argparse,collections,csv,hashlib,json,math,sys
from pathlib import Path
import yaml


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def label_summary(path):
    counts=collections.Counter();errors=[]
    if not path.is_file():return counts,['MISSING_LABEL'],False
    lines=path.read_text(encoding='utf-8-sig').splitlines()
    for number,line in enumerate(lines,1):
        if not line.strip():continue
        try:
            parts=line.split()
            if len(parts)!=5:raise ValueError('not five YOLO fields')
            klass=int(parts[0]);x,y,w,h=map(float,parts[1:])
            if klass not in range(5) or not all(math.isfinite(v) for v in [x,y,w,h]) or not 0<w<=1 or not 0<h<=1:
                raise ValueError('class or nonpositive/invalid extent')
            if x-w/2 < -1e-6 or y-h/2 < -1e-6 or x+w/2>1+1e-6 or y+h/2>1+1e-6:raise ValueError('box outside image')
            counts[klass]+=1
        except (ValueError,OverflowError) as error:errors.append(f'line {number}: {error}')
    return counts,errors,not any(line.strip() for line in lines)


def audit(root,output):
    root,output=Path(root).resolve(),Path(output)
    if output.exists():raise ValueError('Use a fresh audit output directory.')
    definitions=[('V8_A','datasets/V8-A-TARGETED-HARD-POSITIVE/images/train','datasets/V8-A-TARGETED-HARD-POSITIVE/labels/train','TRAIN'),
        *[('DRISHTI_V3',f'datasets/drishti_sss_v3/{s}/images',f'datasets/drishti_sss_v3/{s}/labels',role)
          for s,role in [('train','TRAIN'),('val_clean','DEV_CANDIDATE'),('val','HISTORICAL_VALIDATION'),('test','HISTORICAL_TEST'),('benchmark_bg','HISTORICAL_BACKGROUND')]]]
    rows=[];groups=[];by_hash=collections.defaultdict(list);filenames=collections.defaultdict(list)
    for dataset,images,labels,role in definitions:
        folder=root/images;label_folder=root/labels;class_counts=collections.Counter();bad=empty=missing=0
        for path in sorted(folder.rglob('*')):
            if path.suffix.lower() not in {'.jpg','.jpeg','.png','.bmp','.tif','.tiff'}:continue
            label=label_folder/path.relative_to(folder).with_suffix('.txt')
            count,errors,is_empty=label_summary(label);class_counts.update(count)
            missing+=not label.exists();bad+=bool(errors);empty+=is_empty
            row={'image':str(path.relative_to(root)),'dataset':dataset,'declared_role':role,'sha256':digest(path),
                 'label_sha256':digest(label) if label.is_file() else None,'label_errors':errors[:10],
                 'empty_label_not_verified_background':is_empty,'acquisition_group':'UNKNOWN',
                 'human_annotation_verification':'UNKNOWN','license_verification':'UNKNOWN','pretraining_overlap':'UNKNOWN'}
            rows.append(row);by_hash[row['sha256']].append(row);filenames[path.name].append(row)
        groups.append({'dataset':dataset,'role':role,'image_count':sum(r['dataset']==dataset and r['declared_role']==role for r in rows),
                       'valid_box_class_counts':dict(class_counts),'files_with_label_errors':bad,
                       'missing_labels':missing,'empty_labels_not_verified_background':empty})
        print(json.dumps(groups[-1]),flush=True)
    overlaps=[{'sha256':h,'roles':sorted({r['declared_role'] for r in records}),
               'images':[r['image'] for r in records]} for h,records in by_hash.items()
              if len({r['declared_role'] for r in records})>1]
    lineage_path=root/'datasets/V8-A-TARGETED-HARD-POSITIVE/v8_a_crop_lineage.csv'
    lineage=[]
    if lineage_path.is_file():
        with lineage_path.open(encoding='utf-8-sig',newline='') as f:
            for item in csv.DictReader(f):
                parents=by_hash.get(item['source_image_sha256'],[]);children=filenames.get(item['crop_id'],[])
                lineage.append({'crop_id':item['crop_id'],'declared_derived_from_train':item.get('derived_from_train'),
                    'parent_roles_found':sorted({r['declared_role'] for r in parents}),
                    'crop_roles_found':sorted({r['declared_role'] for r in children}),
                    'parent_identity_resolved':bool(parents),
                    'protected_parent_used_for_training':any(r['declared_role']=='TRAIN' for r in children) and
                        any(r['declared_role'] in {'DEV_CANDIDATE','HISTORICAL_TEST','HISTORICAL_VALIDATION'} for r in parents)})
    configs=[]
    for relative in ['datasets/V8-A-TARGETED-HARD-POSITIVE/dataset.yaml','datasets/drishti_sss_v3/drishti_v3.yaml','models/v8/detector_v8_a_targeted/args.yaml']:
        path=root/relative
        if path.is_file():
            conf=yaml.safe_load(path.read_text(encoding='utf-8'))
            configs.append({'file':relative,'sha256':digest(path),'train':conf.get('train'),'val':conf.get('val'),
                            'test':conf.get('test'),'data':conf.get('data'),'epochs':conf.get('epochs')})
    v8_val=str(configs[0]['val']) if configs else ''
    used_test='test' in v8_val.lower()
    report={'version':1,'scope':'V8_A_AND_DRISHTI_V3_EXACT_HASH_LABEL_LINEAGE_KICKOFF_NOT_FULL_PROVENANCE',
            'training_started':False,'inference_calls':0,'groups':groups,'image_count':len(rows),
            'exact_hash_cross_role_groups':len(overlaps),'cross_role_overlaps':overlaps,
            'lineage_rows':len(lineage),'unresolved_parent_rows':sum(not r['parent_identity_resolved'] for r in lineage),
            'protected_parent_training_rows':sum(r['protected_parent_used_for_training'] for r in lineage),
            'configs':configs,'v8_a_validation_test_informed':used_test,
            'final_test_independence_verified':False,'ready_for_new_training':False,
            'remaining':['SURVEY_SITE_MISSION_GROUPS','LICENSE_AND_LABEL_VERIFICATION','DECODED_PIXEL_AND_NEAR_DUPLICATE_REVIEW',
                         'PRIOR_SELECTION_AND_PRETRAINING_HISTORY','UNTOUCHED_EXTERNAL_CLASS_COVERAGE','OTHER_EXISTING_DATASET_REVISIONS']}
    output.mkdir(parents=True)
    for name,value in [('summary.json',report),('image-inventory.json',rows),('crop-lineage-audit.json',lineage)]:
        (output/name).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=audit(a.root,a.output);print(json.dumps({k:r[k] for k in ['image_count','exact_hash_cross_role_groups','lineage_rows','protected_parent_training_rows','ready_for_new_training']}))
