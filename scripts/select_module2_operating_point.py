"""M2.09 DEV threshold selection; no fitting, calibration or deployment."""
import argparse, collections, json, math, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import NAMES, parse_labels, sha

SETTINGS={'imgsz':640,'conf_floor':.001,'nms_iou':.7,'max_det':300,'half':False,'batch':1,'device':0}

def iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union>0 else 0

def score(tp,fp,support):
    p=tp/(tp+fp) if tp+fp else None
    r=tp/support if support else None
    return {'tp':tp,'fp':fp,'fn':support-tp,'precision':p,'recall':r,
            'f1':2*p*r/(p+r) if p is not None and r is not None and p+r else 0}

def events(rows):
    """Greedy per-image matches are prefix invariant under confidence filtering."""
    result=[];support=collections.Counter()
    for row in rows:
        gt=row['gt'];support.update(g['class'] for g in gt);used=set()
        for pred in sorted(row['predictions'],key=lambda p:-p['confidence']):
            overlap,j=max(((iou(pred['box'],g['box']),j) for j,g in enumerate(gt)
                          if pred['class']==g['class'] and j not in used),default=(0,-1))
            correct=overlap>=.5
            if correct:used.add(j)
            result.append((pred['confidence'],pred['class'],int(correct)))
    return result,dict(support)

def curve(event_list,support):
    groups=collections.defaultdict(lambda:[0,0])
    for confidence,c,correct in event_list:
        groups[confidence][0 if correct else 1]+=1
    tp=fp=0;points=[]
    for threshold,(t,f) in sorted(groups.items(),reverse=True):
        tp+=t;fp+=f
        points.append({'threshold':threshold,**score(tp,fp,support)})
    return points

def choose(points,precision_floor=.8):
    candidates=[p for p in points if p['precision'] is not None and p['precision']>=precision_floor]
    return max(candidates,key=lambda p:(p['tp'],-p['fp'],p['threshold'])) if candidates else None

def fixed(event_list,support,threshold=.25):
    tp=sum(correct for confidence,c,correct in event_list if confidence>=threshold)
    total=sum(confidence>=threshold for confidence,c,correct in event_list)
    return {'threshold':threshold,**score(tp,total-tp,support)}

def analyze(rows):
    event_list,support=events(rows);total=sum(support.values())
    global_curve=curve(event_list,total)
    classes={}
    for c,name in NAMES.items():
        points=curve([e for e in event_list if e[1]==c],support[c])
        classes[str(c)]={'name':name,'support':support[c],
            'best_recall_at_precision_80':choose(points),
            'best_f1':max(points,key=lambda p:(p['f1'],p['tp'],-p['fp'])) if points else None,
            'maximum_cached_recall':points[-1]['recall'] if points else 0,
            'curve':points}
    selected=[v['best_recall_at_precision_80'] for v in classes.values()]
    policy=None
    if all(p is not None for p in selected):
        policy={'thresholds':{c:v['best_recall_at_precision_80']['threshold'] for c,v in classes.items()},
                'overall':score(sum(p['tp'] for p in selected),sum(p['fp'] for p in selected),total),
                'per_class':{c:v['best_recall_at_precision_80'] for c,v in classes.items()}}
    maximum_recall=global_curve[-1]['recall'] if global_curve else 0
    best80=choose(global_curve)
    return {'ground_truth_boxes':total,'detections_above_floor':len(event_list),
        'fixed_025':fixed(event_list,total),'best_global_recall_at_precision_80':best80,
        'best_global_f1':max(global_curve,key=lambda p:(p['f1'],p['tp'],-p['fp'])) if global_curve else None,
        'maximum_cached_recall':maximum_recall,
        'global_80_80_met':bool(best80 and best80['recall']>=.8),
        'all_classes_80_80_met':bool(policy and all(p['recall']>=.8 for p in selected)),
        'class_precision_floor_policy':policy,'per_class':classes,'global_curve':global_curve}

def validate_rows(rows,expected):
    seen=set()
    if len(rows)!=len(expected):raise ValueError('Incomplete predictions.')
    for row in rows:
        path=Path(row['image']).resolve()
        if path not in expected or path in seen:raise ValueError('Unexpected/duplicate image.')
        seen.add(path);r=expected[path];w,h=row['width'],row['height']
        if (w,h)!=(r['width'],r['height']):raise ValueError('Cached dimensions changed.')
        truth=[{'class':c,'box':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]}
               for c,x,y,bw,bh in parse_labels(Path(r['label']).read_text(encoding='utf-8'))]
        if row['gt']!=truth or row['source_image']!=r['source_image']:raise ValueError('Cached truth/provenance mismatch.')
        for pred in row['predictions']:
            box=pred['box'];confidence=pred['confidence']
            if pred['class'] not in NAMES or not math.isfinite(confidence) or not .001<=confidence<=1:
                raise ValueError('Invalid cached class/confidence.')
            if len(box)!=4 or not all(math.isfinite(v) for v in box) or box[2]<=box[0] or box[3]<=box[1]:
                raise ValueError('Invalid cached box.')
    if seen!=set(expected):raise ValueError('Missing DEV image.')

def acquire(root,output,name,measured,expected):
    checkpoint=Path(measured['checkpoint'])
    if sha(checkpoint)!=measured['checkpoint_sha256']['best.pt']:raise ValueError('Checkpoint drift.')
    if name=='D1':
        folder=root/'.temp/module2-d1-diagnosis-20261004'
        metadata=json.loads((folder/'report.json').read_text(encoding='utf-8'))
        path=folder/'predictions.json'
        if (metadata['checkpoint_sha256']!=sha(checkpoint) or
            metadata['manifest_sha256']!=measured['dataset_manifest_sha256'] or
            metadata['settings']!=SETTINGS or metadata['predictions_sha256']!=sha(path)):
            raise ValueError('D1 cache identity/settings/hash mismatch.')
        rows=json.loads(path.read_text(encoding='utf-8'))
        new_passes=0
    else:
        from ultralytics import YOLO
        model=YOLO(str(checkpoint))
        if model.names!=NAMES:raise ValueError('Model class map mismatch.')
        rows=[]
        print('M2.08: one FP32/640 low-confidence DEV prediction pass; no training/HF.',flush=True)
        for result in model.predict(source=str(root/'datasets/mechanically_curated_r01_20261003/images/val'),
            device=0,imgsz=640,batch=1,conf=.001,iou=.7,max_det=300,half=False,save=False,verbose=False,stream=True):
            path=Path(result.path).resolve()
            if path not in expected:raise ValueError('Unknown prediction source.')
            r=expected[path];h,w=result.orig_shape
            gt=[{'class':c,'box':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]}
                for c,x,y,bw,bh in parse_labels(Path(r['label']).read_text(encoding='utf-8'))]
            predictions=[{'class':int(c),'confidence':float(s),'box':b.tolist()}
                for c,s,b in zip(result.boxes.cls.cpu(),result.boxes.conf.cpu(),result.boxes.xyxy.cpu())]
            rows.append({'image':str(path),'source_image':r['source_image'],'width':w,'height':h,'gt':gt,'predictions':predictions})
            if len(rows)%200==0:print(f'Cached {len(rows)}/{len(expected)}',flush=True)
        path=output/'m208-predictions.json';path.write_text(json.dumps(rows),encoding='utf-8');new_passes=1
    validate_rows(rows,expected)
    if sha(checkpoint)!=measured['checkpoint_sha256']['best.pt']:raise ValueError('Weights changed during inference.')
    return rows,{'checkpoint':str(checkpoint),'checkpoint_sha256':sha(checkpoint),
        'predictions_path':str(path),'predictions_sha256':sha(path),'settings':SETTINGS,
        'capped_prediction_images':sum(len(r['predictions'])>=300 for r in rows),'new_prediction_passes':new_passes}

def run(root,output):
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh output directory required.')
    dataset=root/'datasets/mechanically_curated_r01_20261003'
    manifest=json.loads((dataset/'manifest.json').read_text(encoding='utf-8'))
    ready=json.loads((dataset/'READY.json').read_text(encoding='utf-8'))
    if sha(dataset/'manifest.json')!=ready['manifest_sha256'] or sha(dataset/'data.yaml')!=ready['data_sha256']:
        raise ValueError('Dataset identity changed.')
    expected={Path(r['image']).resolve():r for r in manifest['records'] if r['split']=='DEV'}
    for path,r in expected.items():
        if sha(path)!=r['image_sha256'] or sha(r['label'])!=r['label_sha256']:raise ValueError('DEV bytes changed.')
    output.mkdir(parents=True);models={};curves={}
    for name,source in [('D1','module2-d1-evaluation-20261004.json'),('M2.08','module2-m208-evaluation-20261004.json')]:
        measured=json.loads((root/'docs/metrics'/source).read_text(encoding='utf-8'))
        if measured['dataset_manifest_sha256']!=ready['manifest_sha256']:raise ValueError('Metric split mismatch.')
        rows,evidence=acquire(root,output,name,measured,expected)
        print(f'{name}: exact sweep of all retained confidence breakpoints.',flush=True)
        result=analyze(rows)
        for k in ('tp','fp','fn'):
            if result['fixed_025'][k]!=measured['object_metrics'][k]:
                raise ValueError(f'{name} low-floor predictions did not reconcile at 0.25: {k}')
        curves[name]={'global':result.pop('global_curve'),
            'per_class':{c:v.pop('curve') for c,v in result['per_class'].items()}}
        models[name]={'evidence':evidence,**result,'mAP50':measured['mAP50'],
            'mAP50_95':measured['mAP50_95'],'mAP_scope':'Previous full validation; not recomputed after threshold filtering.'}
    candidates=[]
    for name,result in models.items():
        if result['best_global_recall_at_precision_80']:
            candidates.append((name,'GLOBAL',result['best_global_recall_at_precision_80']))
        if result['class_precision_floor_policy']:
            candidates.append((name,'PER_CLASS_PRECISION_80',result['class_precision_floor_policy']['overall']))
    selected=max(candidates,key=lambda c:(c[2]['tp'],-c[2]['fp'])) if candidates else None
    selection=None if selected is None else {'model':selected[0],'policy':selected[1],
        'metrics':selected[2],'thresholds':models[selected[0]]['class_precision_floor_policy']['thresholds']
            if selected[1]!='GLOBAL' else {str(c):selected[2]['threshold'] for c in NAMES},
        'scope':'EXPLORATORY_DEV_NOT_PRODUCTION_APPROVED','deployed':False,'calibrated_probability':False}
    report={'phase':'M2.09','images':len(expected),'manifest_sha256':ready['manifest_sha256'],
        'matching':'CLASS_CORRECT_CONFIDENCE_ORDERED_ONE_TO_ONE_IOU_GE_0.50',
        'threshold_search':'ALL_UNIQUE_RETAINED_POST_NMS_CONFIDENCES_GROUPED_TIES',
        'models':models,'selected_precision_floor_candidate':selection,
        'training_calls':0,'hf_calls':0,'deployment_changes':0,
        'limitations':['DEV reused for training validation and recipe/threshold selection; not independent evidence.',
            'Class-precision policy maximizes recall separately under >=80% precision for every class; global-micro optimum may sacrifice class precision.',
            'Prediction floor 0.001/max_det 300/NMS 0.7 bound the search; proposal changes are not searched.',
            'No confirmed natural-negative DEV images; FP count is on the existing positive-image pool.',
            'Net DEV examples are synthetic, not verified real ghost nets.']}
    (output/'curves.json').write_text(json.dumps(curves),encoding='utf-8')
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if selection:(output/'candidate-operating-settings.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
    print(json.dumps({'selected':selection,'summary':{n:{k:r[k] for k in ['best_global_recall_at_precision_80','maximum_cached_recall','global_80_80_met','all_classes_80_80_met']} for n,r in models.items()}},indent=2),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.root,a.output)
