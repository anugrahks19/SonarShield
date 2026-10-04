"""Build immutable exploratory TRAIN/DEV from M2.05; never certify or train."""
import argparse, collections, hashlib, json, shutil, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import cv2
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import NAMES,sha,parse_labels

PURPOSE='CONTROLLED_EXPLORATORY_TRAINING_NOT_FINAL_ACCURACY_CERTIFICATION'

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def verify_handoff(handoff,root):
    summary=load(handoff/'summary.json')
    if summary['phase']!='M2.05_AUTOMATIC_TECHNICAL_CURATION' or not summary['m2_06_technical_preparation_can_continue']:raise ValueError('Wrong handoff.')
    for name,expected in summary['handoff_artifact_hashes'].items():
        if Path(name).name!=name or sha(handoff/name)!=expected:raise ValueError('Handoff artifact changed: '+name)
    if sha(root/'datasets/controlled_v8a_20261003/manifest.json')!=summary['source_manifest_sha256']:raise ValueError('Pinned baseline manifest changed.')
    for path,expected in summary['native_metadata_hashes'].items():
        if sha(path)!=expected:raise ValueError('Native metadata changed since screening.')
    return summary

def verify_roles(records):
    maps=[collections.defaultdict(set) for _ in range(3)];paths=set();counts=collections.Counter()
    for r in records:
        if r['split'] not in ('TRAIN','DEV'):raise ValueError('Only TRAIN and historical DEV allowed.')
        if r['image'] in paths:raise ValueError('Duplicate source image path.')
        paths.add(r['image']);counts[r['split']]+=1
        for m,k in zip(maps,('image_sha256','decoded_sha256','parent_sha256')):m[r[k]].add(r['split'])
        if r['split']=='TRAIN' and (r['box_count']<=0 or r.get('curation_status')!='MECHANICALLY_SCREENED_INHERITED_NOT_EXPERT_APPROVED'):raise ValueError('Unscreened or unconfirmed empty TRAIN record.')
    if any(len(v)>1 for m in maps for v in m.values()):raise ValueError('TRAIN/DEV byte, pixel or parent overlap.')
    if not counts['TRAIN'] or not counts['DEV']:raise ValueError('Empty split.')
    return counts

def copy_record(r,output):
    for pathkey,hashkey in [('image','image_sha256'),('label','label_sha256'),('source_image','parent_sha256'),('source_label','source_label_sha256')]:
        if sha(r[pathkey])!=r[hashkey]:raise ValueError('Input drift: '+r[pathkey])
    image=cv2.imread(r['image'],cv2.IMREAD_COLOR)
    if image is None:raise ValueError('Cannot decode image: '+r['image'])
    pixels=hashlib.sha256(str(image.shape).encode()+image.tobytes()).hexdigest()
    if pixels!=r['decoded_sha256']:raise ValueError('Decoded identity differs from baseline.')
    boxes=parse_labels(Path(r['label']).read_text(encoding='utf-8'))
    if len(boxes)!=r['box_count']:raise ValueError('Box count mismatch.')
    split='train' if r['split']=='TRAIN' else 'val'
    destination=output/'images'/split/Path(r['image']).name
    label=output/'labels'/split/destination.with_suffix('.txt').name
    if destination.exists() or label.exists():raise ValueError('Duplicate destination.')
    shutil.copy2(r['image'],destination);shutil.copy2(r['label'],label)
    if sha(destination)!=r['image_sha256'] or sha(label)!=r['label_sha256']:raise ValueError('Copy hash mismatch.')
    sizecounts=collections.Counter()
    for c,x,y,w,h in boxes:
        gain=min(640/image.shape[1],640/image.shape[0])
        area=w*image.shape[1]*h*image.shape[0]*gain*gain
        size='small' if area<32*32 else 'medium' if area<96*96 else 'large'
        sizecounts[(str(c),size)]+=1
    return {**r,'image':str(destination),'label':str(label),'revision_input_image':r['image'],'revision_input_label':r['label'],'width':image.shape[1],'height':image.shape[0]},collections.Counter(str(b[0]) for b in boxes),sizecounts

def build(root,handoff,output,weights):
    root,handoff,output,weights=map(lambda p:Path(p).resolve(),(root,handoff,output,weights))
    if output.exists():raise ValueError('New dataset directory required. Existing revisions are never overwritten.')
    if not output.is_relative_to(root/'datasets'):raise ValueError('Output must be inside repository datasets.')
    handoffsummary=verify_handoff(handoff,root)
    records=load(handoff/'eligible-inherited-train.json')+load(handoff/'historical-dev.json')
    counts=verify_roles(records)
    if counts['TRAIN']!=handoffsummary['eligible_train_images'] or counts['DEV']!=handoffsummary['historical_dev_images']:raise ValueError('Handoff counts differ.')
    # Reserve all file names before any parallel copy.
    targets=set()
    for r in records:
        key=(r['split'],Path(r['image']).stem)
        if key in targets:raise ValueError('Image/label stem collision.')
        targets.add(key)
    weightsha=sha(weights)
    if weightsha!='b5e475286d7703288719c52e0b31044588c0e114bd426d60057c0f695eaa3605':raise ValueError('Expected pinned V6 reference checkpoint.')
    output.mkdir(parents=True)
    (output/'BUILD_STATUS.json').write_text(json.dumps({'status':'INCOMPLETE_NOT_READY'}),encoding='utf-8')
    for split in ('train','val'):
        (output/'images'/split).mkdir(parents=True);(output/'labels'/split).mkdir(parents=True)
    built=[];classes=collections.defaultdict(collections.Counter);sizes=collections.defaultdict(collections.Counter);sources=collections.defaultdict(collections.Counter);basis=collections.defaultdict(collections.Counter)
    print(f'Copying and decoding {len(records)} screened records into {output.name}; no training.',flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n,(r,c,size) in enumerate(pool.map(lambda r:copy_record(r,output),records),1):
            built.append(r);classes[r['split']].update(c);sizes[r['split']].update(size)
            sources[r['split']][str(Path(r['source_image']).relative_to(root/'datasets').parts[0])]+=1
            basis[r['split']][r['annotation_basis']]+=1
            if n%1000==0:print(f'Verified copies {n}/{len(records)}',flush=True)
    if any(classes[role][str(c)]==0 for role in ('TRAIN','DEV') for c in NAMES):raise ValueError('Missing class support.')
    manifest={'purpose':PURPOSE,'version':2,'revision':'M2_06_MECHANICALLY_CURATED_R01','records':built,'weights_sha256':weightsha,'handoff_summary_sha256':sha(handoff/'summary.json'),'source_counts':dict(counts),'total_train':counts['TRAIN'],'dev_images':counts['DEV'],'expert_annotation_certification':False,'rights_approval_complete':False,'unknown_site_mission_provenance':True,'near_duplicate_review_complete':False,'xtf_included':False,'test_or_calib_used_for_training_validation':False,'confirmed_negative_images':0,'missing_object_annotation_completeness_verified':False,'training_readiness':'M2_07_EXPLORATORY_EXPERIMENT_DECISION_REQUIRED'}
    config={'path':str(output),'train':'images/train','val':'images/val','names':NAMES,'nc':5,'task':'detect'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (output/'data.yaml').write_text(yaml.safe_dump(config,sort_keys=False),encoding='utf-8')
    shutil.copy2(handoff/'exclusions.json',output/'exclusions.json')
    report={'phase':'M2.06','technical_build_complete':True,'counts':dict(counts),'class_box_counts':{k:dict(v) for k,v in classes.items()},'box_size_at_640':{k:{c:{s:v[(c,s)] for s in ('small','medium','large')} for c in map(str,NAMES)} for k,v in sizes.items()},'source_revision_counts':{k:dict(v) for k,v in sources.items()},'annotation_basis_counts':{k:dict(v) for k,v in basis.items()},'confirmed_negative_images':0,'source_annotations_changed':0,'training_calls':0,'inference_calls':0,'independent_holdout_created':False,'calibration_split_created':False,'scientifically_approved_dataset':False,'weights_sha256':weightsha,'dataset':str(output),'manifest_sha256':sha(output/'manifest.json'),'data_sha256':sha(output/'data.yaml'),'limitations':['Inherited annotations, unknown acquisition groups and incomplete licensing review.','Positive-only TRAIN pool; no confirmed natural negatives. FP improvement is not established.','Historical DEV remains experiment data, not independent final evidence.','Real ghost-net and XTF accuracy unverified; no public XTF release.']}
    (output/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    # Reuse the existing strict exploratory integrity validator without importing YOLO.
    from train_corrected_candidate import preflight
    (output/'READY.json').write_text(json.dumps({'manifest_sha256':report['manifest_sha256'],'data_sha256':report['data_sha256'],'scope':PURPOSE,'meaning':'INTEGRITY_READY_NOT_EXPERT_APPROVAL'}),encoding='utf-8')
    try:verification=preflight(output,weights)
    except Exception:
        (output/'READY.json').unlink();raise
    (output/'preflight.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    (output/'BUILD_STATUS.json').write_text(json.dumps({'status':'COMPLETE_INTEGRITY_VERIFIED_NOT_EXPERT_APPROVED'}),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--handoff',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--weights',type=Path,default=Path('models/v6/detector_v6_p2_sss/weights/best.pt'));a=p.parse_args();build(a.root,a.handoff,a.output,a.weights)
