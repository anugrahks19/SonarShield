"""Evaluate completed M2.08 D2; no training or model promotion."""
import argparse,collections,csv,json,math,statistics,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from ultralytics import YOLO
from ai.training.candidate_data import sha,parse_labels,NAMES


def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union>0 else 0


def measure(root,output):
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Use a new evaluation output directory.')
    run=root/'models/controlled/m2_d2_curated_r01_mosaic0_640_01';weights=run/'weights/best.pt';last=run/'weights/last.pt'
    data=root/'datasets/mechanically_curated_r01_20261003'
    manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    ready=json.loads((data/'READY.json').read_text(encoding='utf-8'))
    if sha(data/'manifest.json')!=ready['manifest_sha256'] or sha(data/'data.yaml')!=ready['data_sha256']:
        raise ValueError('Dataset metadata changed.')
    expected={Path(r['image']).resolve():r for r in manifest['records'] if r['split']=='DEV'}
    for image,r in expected.items():
        if sha(image)!=r['image_sha256'] or sha(r['label'])!=r['label_sha256']:raise ValueError('DEV data changed.')
    with (run/'results.csv').open(encoding='utf-8') as f: epoch_rows=list(csv.DictReader(f))
    hashes={p.name:sha(p) for p in [weights,last]};states=[]
    for p in [last,weights]:
        ckpt=torch.load(p,map_location='cpu',weights_only=False)
        recorded=ckpt.get('train_metrics',{})
        keys=['metrics/precision(B)','metrics/recall(B)','metrics/mAP50(B)','metrics/mAP50-95(B)']
        matches=[int(r['epoch']) for r in epoch_rows if all(k in recorded and abs(float(r[k])-float(recorded[k]))<1e-6 for k in keys)]
        states.append({'file':p.name,'raw_checkpoint_epoch':ckpt.get('epoch'),'matching_csv_epochs':matches,
                       'run_completed_epochs':int(epoch_rows[-1]['epoch']),'target_epochs':ckpt['train_args']['epochs'],
                       'optimizer_present':ckpt.get('optimizer') is not None})
        del ckpt
    output.mkdir(parents=True)
    model=YOLO(str(weights))
    if model.names!=NAMES:raise ValueError('Checkpoint class map mismatch.')
    print('Evaluating D2 saved best.pt on preserved historical DEV; no training or historical TEST evaluation.',flush=True)
    metrics=model.val(data=str(data/'data.yaml'),split='val',device=0,imgsz=640,batch=8,workers=0,
                      conf=.001,iou=.7,half=False,plots=False,save_json=False,project=str(output),name='validation')
    map50=float(metrics.box.map50);map95=float(metrics.box.map)
    # Warm GPU forward pass separately; then batch=1 timing over the entire DEV directory.
    model.predict(source=str(next(iter(expected))),device=0,imgsz=640,conf=.25,iou=.7,half=False,verbose=False,save=False)
    totals=collections.Counter(tp=0,fp=0,fn=0);class_counts={c:collections.Counter(tp=0,fp=0,fn=0) for c in NAMES}
    timings=[];image_rows=[];seen=set();start=time.perf_counter()
    results=model.predict(source=str(data/'images/val'),device=0,imgsz=640,batch=1,conf=.25,iou=.7,
                          half=False,verbose=False,save=False,stream=True)
    for result in results:
        image=Path(result.path).resolve()
        if image not in expected or image in seen:raise ValueError('Unexpected or duplicate evaluation image.')
        seen.add(image);r=expected[image];h,w=result.orig_shape
        gt=[]
        for c,x,y,bw,bh in parse_labels(Path(r['label']).read_text(encoding='utf-8')):
            gt.append((c,[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]))
        detections=[(int(c),float(conf),box.tolist()) for c,conf,box in zip(result.boxes.cls.cpu(),result.boxes.conf.cpu(),result.boxes.xyxy.cpu())]
        used=set();tp=0;fp=0
        for c,conf,b in sorted(detections,key=lambda row:-row[1]):
            overlap,j=max(((iou(b,g),j) for j,(gc,g) in enumerate(gt) if gc==c and j not in used),default=(0,-1))
            if overlap>=.5:used.add(j);tp+=1;class_counts[c]['tp']+=1
            else:fp+=1;class_counts[c]['fp']+=1
        for j,(c,_) in enumerate(gt):
            if j not in used:class_counts[c]['fn']+=1
        totals.update(tp=tp,fp=fp,fn=len(gt)-tp)
        timings.append(float(result.speed['inference']))
        image_rows.append({'image':image.name,'tp':tp,'fp':fp,'fn':len(gt)-tp,'model_forward_ms':timings[-1]})
        if len(seen)%100==0:print(f'Measured {len(seen)}/{len(expected)} DEV images',flush=True)
    elapsed=time.perf_counter()-start
    if seen!=set(expected):raise ValueError('Missing evaluation images.')
    if any(sha(run/'weights'/name)!=value for name,value in hashes.items()):raise ValueError('Checkpoint changed during evaluation.')
    def scores(counts):
        t,f,n=counts['tp'],counts['fp'],counts['fn']
        return {**counts,'precision':t/(t+f) if t+f else None,'recall':t/(t+n) if t+n else None}
    ordered=sorted(timings)
    report={'phase':'M2.08_D2_POST_TRAINING_MEASUREMENT','run_completed_epochs':int(epoch_rows[-1]['epoch']),'scope':'HISTORICALLY_USED_DEV_INHERITED_LABELS_NOT_INDEPENDENT_TEST_OR_XTF_ACCURACY',
        'checkpoint':str(weights),'checkpoint_sha256':hashes,'checkpoint_states':states,'images':len(seen),
        'matching':'CLASS_CORRECT_CONFIDENCE_ORDERED_ONE_TO_ONE_IOU_GE_0.50','confidence_threshold':.25,
        'nms_iou':.7,'imgsz':640,'device':torch.cuda.get_device_name(0),'precision_type':'OBJECT_MICRO_AT_FIXED_CONFIDENCE',
        'object_metrics':scores(totals),'mAP50':map50,'mAP50_95':map95,
        'ultralytics_validation_mean_precision':float(metrics.box.mp),'ultralytics_validation_mean_recall':float(metrics.box.mr),
        'ultralytics_pr_scope':'MEAN_CLASS_PRECISION_RECALL_AT_VALIDATOR_SELECTED_F1_POINT_DIFFERENT_FROM_FIXED_0.25',
        'inference_time':{'batch':1,'precision':'FP32','gpu_model_forward_mean_ms':statistics.mean(timings),
            'gpu_model_forward_median_ms':statistics.median(timings),'gpu_model_forward_p95_ms':ordered[math.ceil(.95*len(ordered))-1],
            'directory_walk_wall_ms_per_image':elapsed/len(seen)*1000,'includes_fusion_or_cloud_network':False},
        'false_positives_per_image':totals['fp']/len(seen),'per_class':{str(c):{'name':NAMES[c],**scores(v)} for c,v in class_counts.items()},
        'training_restarted':False,'dataset_manifest_sha256':sha(data/'manifest.json'),'hf_inference_calls':0,'final_accuracy_claim_allowed':False}
    (output/'per-image.json').write_text(json.dumps(image_rows,indent=2),encoding='utf-8')
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();measure(a.root,a.output)
