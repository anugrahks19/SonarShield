"""Fail-closed mechanical curation for M2.06; not expert annotation approval."""
import argparse, collections, hashlib, json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import sha, parse_labels

def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def exclusions(record, blocked, protected, dev, bad, families):
    reasons=[]
    identities={record['image_sha256'],record['parent_sha256']}
    if identities & protected: reasons.append('HISTORICAL_TEST_OR_BACKGROUND_IDENTITY_OR_PARENT')
    if identities & dev: reasons.append('DEV_IDENTITY_OR_PARENT')
    if identities & blocked: reasons.append('SIMILARITY_QUARANTINE_NOT_PROVEN_DUPLICATE')
    if identities & bad: reasons.append('NATIVE_ANNOTATION_ISSUE_IDENTITY_OR_PARENT')
    if identities & families: reasons.append('CRAB_FILENAME_FAMILY_WITH_PROTECTED_ROLE')
    if record.get('box_count',0)==0: reasons.append('EMPTY_LABEL_NOT_CONFIRMED_BACKGROUND')
    return reasons

def verify_record(r):
    errors=[]
    try:
        for pathkey,hashkey in [('image','image_sha256'),('label','label_sha256'),('source_image','parent_sha256'),('source_label','source_label_sha256')]:
            if sha(Path(r[pathkey]))!=r[hashkey]: errors.append('HASH_DRIFT_'+pathkey.upper())
        boxes=parse_labels(Path(r['label']).read_text(encoding='utf-8'))
        if len(boxes)!=r['box_count']: errors.append('BOX_COUNT_DRIFT')
    except (OSError,ValueError,KeyError) as e:
        errors.append('SOURCE_OR_LABEL_INVALID:'+str(e)[:200]);boxes=[]
    return errors,collections.Counter(str(b[0]) for b in boxes)

def prepare(root,audit,output):
    root,audit,output=map(Path,(root,audit,output))
    if output.exists(): raise ValueError('New output directory required; no overwrite.')
    for name,expected in load(audit/'summary.json')['metadata_hashes'].items():
        if sha(root/name)!=expected: raise ValueError('Native metadata changed since audit: '+name)
    source=root/'datasets/controlled_v8a_20261003/manifest.json'
    manifest=load(source); inventory=load(audit/'inventory.json')
    bypath={r['image']:r for r in inventory}
    protected={r['sha256'] for r in inventory if r['role'] in {'HISTORICAL_TEST','HISTORICAL_BACKGROUND'}}
    bad={r['sha256'] for r in inventory if r['dataset'] in {'crab_pot','MILCONOMBO Side-Scan Sonar Mine Dataset'} and r.get('annotation_errors')}
    dev={r['image_sha256'] for r in manifest['records'] if r['split']=='DEV'}
    blocked=set()
    for p in load(audit/'priority-near-review.json'):
        # Quarantine both ends conservatively. Similarity is never a semantic verdict.
        for path in [p['a'],p['b']]:
            if path in bypath: blocked.add(bypath[path]['sha256'])
    nativefamilies=collections.defaultdict(list)
    for r in inventory:
        if r['dataset']=='crab_pot': nativefamilies[r['family']].append(r)
    familyblocked={r['sha256'] for rs in nativefamilies.values() if any(r['role'] in {'HISTORICAL_TEST','HISTORICAL_VALIDATION'} for r in rs) for r in rs}
    eligible=[];excluded=[];devrecords=[];counts=collections.Counter();devcounts=collections.Counter();seen=set();seenpixels=set()
    metadata={}
    # Freeze native JSONL provenance at handoff, including the published category data.
    for p in (root/'datasets/crab_pot').rglob('metadata.jsonl'): metadata[str(p)]=sha(p)
    print(f'Checking {len(manifest["records"])} inherited records and source hashes; no inference.',flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n,(r,(errors,classes)) in enumerate(zip(manifest['records'],pool.map(verify_record,manifest['records']))):
            if (n+1)%2000==0: print(f'Checked {n+1}/{len(manifest["records"])}',flush=True)
            if r['split']=='DEV':
                if errors: raise ValueError('Pinned DEV changed: '+str(errors))
                devrecords.append(r);devcounts.update(classes);continue
            if r['split']!='TRAIN': errors.append('UNSUPPORTED_ROLE')
            errors+=exclusions(r,blocked,protected,dev,bad,familyblocked)
            if r['image_sha256'] in seen or r['decoded_sha256'] in seenpixels: errors.append('EXACT_OR_DECODED_DUPLICATE_IN_TRAIN')
            if errors: excluded.append({'image':r['image'],'image_sha256':r['image_sha256'],'parent_sha256':r['parent_sha256'],'reasons':sorted(set(errors))})
            else:
                eligible.append({**r,'curation_status':'MECHANICALLY_SCREENED_INHERITED_NOT_EXPERT_APPROVED'});counts.update(classes);seen.add(r['image_sha256']);seenpixels.add(r['decoded_sha256'])
    if not eligible or any(counts[str(c)]==0 for c in range(5)): raise ValueError('Insufficient five-class support; do not manufacture readiness.')
    nativecounts=collections.Counter()
    for r in inventory:
        if r['dataset']=='crab_pot' and r['role']=='HISTORICAL_TRAIN':
            nativecounts['quarantined' if r['annotation_errors'] or r['sha256'] in blocked|protected|familyblocked|dev else 'structurally_valid_unharmonized']+=1
    report={'phase':'M2.05_AUTOMATIC_TECHNICAL_CURATION','m2_06_technical_preparation_can_continue':True,'approved_dataset_ready':False,'expert_annotation_certification':False,'rights_approval_complete':False,'survey_group_independence_verified':False,'training_ready':False,'training_started':False,'inference_calls':0,'source_labels_changed':0,'source_manifest_sha256':sha(source),'audit_inventory_sha256':sha(audit/'inventory.json'),'audit_similarity_sha256':sha(audit/'priority-near-review.json'),'native_metadata_hashes':metadata,'eligible_train_images':len(eligible),'excluded_train_images':len(excluded),'historical_dev_images':len(devrecords),'eligible_train_boxes_by_class':dict(counts),'historical_dev_boxes_by_class':dict(devcounts),'native_crab_train_screen':dict(nativecounts),'exclusion_counts_nonexclusive':dict(collections.Counter(reason for r in excluded for reason in r['reasons'])),'limitations':['Mechanical checks cannot confirm object identity, missing objects, mask foreground semantics or target-free backgrounds.','Similarity screening is capped; quarantines are conservative, not proven duplicates.','Previously exposed DEV/TEST cannot become untouched final evaluation.','No new native-class mapping, mask conversion, XTF pseudo-labels, or auto-clipping.','Synthetic ghost-net performance is not real-net evidence.']}
    output.mkdir(parents=True)
    (output/'eligible-inherited-train.json').write_text(json.dumps(eligible,indent=2),encoding='utf-8')
    (output/'historical-dev.json').write_text(json.dumps(devrecords,indent=2),encoding='utf-8')
    (output/'exclusions.json').write_text(json.dumps(excluded,indent=2),encoding='utf-8')
    report['handoff_artifact_hashes']={name:sha(output/name) for name in ('eligible-inherited-train.json','historical-dev.json','exclusions.json')}
    (output/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='native_metadata_hashes'},indent=2),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.root,a.audit,a.output)
