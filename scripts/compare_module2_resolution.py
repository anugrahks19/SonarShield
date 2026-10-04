"""Compare preserved detector processing strategies on pinned DEV; never train."""
import argparse
import os
os.environ['CUDA_LAUNCH_BLOCKING']='1'
import html
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import NAMES,sha
from scripts.diagnose_module2_baseline import aggregate,bucket,match,THRESHOLDS
from scripts.evaluate_interrupted_run import iou


def starts(length,size=384,stride=288):
    if length<=size:return [0]
    return sorted(set(list(range(0,length-size+1,stride))+[length-size]))


def merge(predictions,threshold=.7,max_det=300):
    import torch
    from torchvision.ops import batched_nms
    if not predictions:return [],0
    boxes=torch.tensor([p['box'] for p in predictions],dtype=torch.float32)
    scores=torch.tensor([p['confidence'] for p in predictions],dtype=torch.float32)
    classes=torch.tensor([p['class'] for p in predictions],dtype=torch.int64)
    indices=batched_nms(boxes,scores,classes,threshold).tolist()
    return [predictions[i] for i in indices[:max_det]],max(0,len(indices)-max_det)


def diagnostic_ap(rows):
    import numpy as np
    from ultralytics.utils.metrics import ap_per_class
    tp=[];scores=[];classes=[];targets=[]
    for row in rows:
        predictions=sorted(row['predictions'],key=lambda p:-p['confidence'])
        hit=np.zeros((len(predictions),10),dtype=bool)
        for k,level in enumerate(np.linspace(.5,.95,10)):
            used=set()
            for n,p in enumerate(predictions):
                overlap,j=max(((iou(p['box'],g['box']),j) for j,g in enumerate(row['gt'])
                              if p['class']==g['class'] and j not in used),default=(0,-1))
                if overlap>=level:hit[n,k]=True;used.add(j)
        tp.extend(hit);scores.extend(p['confidence'] for p in predictions)
        classes.extend(p['class'] for p in predictions);targets.extend(g['class'] for g in row['gt'])
    result=ap_per_class(np.asarray(tp,dtype=bool).reshape(-1,10),np.asarray(scores),np.asarray(classes),np.asarray(targets),names=NAMES)
    ap=result[5]
    return {'mAP50':float(ap[:,0].mean()),'mAP50_95':float(ap.mean()),
            'per_class':{str(c):{'AP50':float(a[0]),'AP50_95':float(a.mean())} for c,a in zip(result[6],ap)},
            'definition':'101-point Ultralytics AP integration, confidence-ordered matching at each IoU; diagnostic protocol, distinct from validator matching.'}


def summarize(rows,timing):
    curves=[aggregate(rows,t) for t in THRESHOLDS]
    fixed=next(p for p in curves if p['threshold']==.25)
    sizes={str(c):{s:{'gt':0,'matched':0} for s in ('small','medium','large')} for c in NAMES}
    duplicates=0
    for row in rows:
        decisions,used=match(row['gt'],row['predictions'],.25)
        for j,g in enumerate(row['gt']):
            stat=sizes[str(g['class'])][bucket(g['box'],row['width'],row['height'])]
            stat['gt']+=1;stat['matched']+=j in used
        duplicates+=sum(j is None and any(p['class']==g['class'] and iou(p['box'],g['box'])>=.5 for g in row['gt']) for p,j in decisions)
    for values in sizes.values():
        for s in values.values():s['recall']=s['matched']/s['gt'] if s['gt'] else None
    return {'fixed_025':fixed,'threshold_curves':curves,'best_grid_f1':max(curves,key=lambda p:p['overall']['f1']),
            'passes_80_80_on_grid':[p['threshold'] for p in curves if p['overall']['precision']>=.8 and p['overall']['recall']>=.8],
            'highest_recall_at_precision_ge_80':max((p['overall']['recall'] for p in curves if p['overall']['precision']>=.8),default=None),
            'highest_precision_at_recall_ge_80':max((p['overall']['precision'] for p in curves if p['overall']['recall']>=.8),default=None),
            'duplicate_overlap_fp_at_025':duplicates,'size_recall_at_025':sizes,'diagnostic_ap':diagnostic_ap(rows),
            'timing':{'measured_images':len(timing),'warmup_excluded':True,'wall_mean_ms':statistics.mean(timing),
                      'wall_median_ms':statistics.median(timing),'wall_p95_ms':sorted(timing)[int(.95*(len(timing)-1))],
                      'scope':'Sequential local pipeline, GPU-synchronized; excludes disk decode, scoring, upload, fusion and UI.'}}


def run(root,output,resume_from=None):
    import cv2
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    from ultralytics.utils import LOGGER
    import logging
    class OnceHalfWarning(logging.Filter):
        seen=False
        def filter(self,record):
            if "'half' is deprecated" in record.getMessage():
                if self.seen:return False
                self.seen=True
            return True
    LOGGER.addFilter(OnceHalfWarning())
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh output directory required.')
    evidence=json.loads((root/'docs/metrics/module2-diagnosis-20261003.json').read_text())
    cache=root/'.temp/module2-failure-diagnosis-final-20261003/predictions.json'
    checkpoint=root/'.temp/module2-baseline-preserved-20261003/best.pt'
    if sha(cache)!=evidence['predictions_sha256'] or sha(checkpoint)!=evidence['checkpoint_sha256']:raise ValueError('Baseline/cache changed.')
    data=root/'datasets/controlled_v8a_20261003'
    if sha(data/'manifest.json')!=evidence['manifest_sha256']:raise ValueError('Manifest changed.')
    manifest=json.loads((data/'manifest.json').read_text())
    records={str(Path(r['image']).resolve()):r for r in manifest['records'] if r['split']=='DEV'}
    rows=json.loads(cache.read_text())
    if len(rows)!=1129 or set(r['image'] for r in rows)!=set(records):raise ValueError('Wrong DEV cache.')
    print('Checking pinned DEV inputs.',flush=True)
    for r in rows:
        item=records[r['image']]
        if sha(r['image'])!=item['image_sha256'] or sha(item['label'])!=item['label_sha256']:raise ValueError('DEV bytes changed.')
    output.mkdir(parents=True)
    identity={'checkpoint_sha256':sha(checkpoint),'manifest_sha256':sha(data/'manifest.json'),
              'protocol':'640_960_TILE384_STRIDE288_NMS07_FP32_CUDA_BLOCKING_THREADS1_V1'}
    (output/'identity.json').write_text(json.dumps(identity),encoding='utf-8')
    completed={}
    if resume_from:
        resume_from=Path(resume_from)
        if json.loads((resume_from/'identity.json').read_text())!=identity:raise ValueError('Resume protocol mismatch.')
        for saved in resume_from.glob('image-*.json'):
            record=json.loads(saved.read_text())
            if record['image'] not in records or record['image'] in completed:raise ValueError('Invalid completed-image cache.')
            completed[record['image']]=record
    model=YOLO(str(checkpoint))
    print('Archived model loaded. Starting warmed inference.',flush=True)
    if model.names!=NAMES:raise ValueError('Class mismatch.')
    strategies={name:[] for name in ('global640','global960','tiles384_only','global640_plus_tiles384')}
    times={name:[] for name in strategies};tile_counts=[];truncation={name:0 for name in strategies};crop_cap=0
    def predict(image,resolution,origin=(0,0)):
        result=model.predict(image,imgsz=resolution,device=0,batch=1,conf=.001,iou=.7,max_det=300,half=False,verbose=False,save=False)[0]
        pred=[]
        for cls,score,box in zip(result.boxes.cls.cpu(),result.boxes.conf.cpu(),result.boxes.xyxy.cpu()):
            x1,y1,x2,y2=box.tolist();ox,oy=origin
            pred.append({'class':int(cls),'confidence':float(score),'box':[x1+ox,y1+oy,x2+ox,y2+oy]})
        return pred
    first=cv2.imread(rows[0]['image'])
    print('Warming duplicate merge.',flush=True)
    merge([{'class':0,'confidence':.5,'box':[0.,0.,20.,20.]}])
    for resolution in (640,960):
        print(f'Warming global {resolution}.',flush=True)
        for _ in range(3):predict(first,resolution)
    print('Warming tiles.',flush=True)
    for _ in range(3):predict(first[:384,:384],640)
    print('Comparing global640, global960, 384px tiles and global+tiles on all DEV. No training.',flush=True)
    for n,row in enumerate(rows):
        if row['image'] in completed:
            record=completed[row['image']]
            for name in strategies:
                strategies[name].append({**row,'predictions':record['predictions'][name]})
                times[name].append(record['times'][name]);truncation[name]+=record['truncation'][name]
            tile_counts.append(record['tile_count']);crop_cap+=record['crop_cap']
            (output/f'image-{n:04}.json').write_text(json.dumps(record),encoding='utf-8')
            continue
        image=cv2.imread(row['image'])
        if image is None or image.shape[:2]!=(row['height'],row['width']):raise ValueError('Decode/dimensions mismatch.')
        global_preds={};global_times={}
        for name,resolution in [('global640',640),('global960',960)]:
            torch.cuda.synchronize();t=time.perf_counter();pred=predict(image,resolution);torch.cuda.synchronize()
            elapsed=(time.perf_counter()-t)*1000;global_preds[name]=pred;global_times[name]=elapsed
            strategies[name].append({**row,'predictions':pred});times[name].append(elapsed)
            truncation[name]+=len(pred)==300
        origins=[(x,y) for y in starts(row['height']) for x in starts(row['width'])]
        if len(origins)>256:raise ValueError('Tile budget exceeded; no silent partial processing.')
        tile_counts.append(len(origins));tiled=[];this_crop_cap=0;this_truncation={name:int(len(global_preds[name])==300) if name in global_preds else 0 for name in strategies}
        torch.cuda.synchronize();t=time.perf_counter()
        for x,y in origins:
            pred=predict(image[y:min(y+384,row['height']),x:min(x+384,row['width'])],640,(x,y))
            crop_cap+=len(pred)==300;this_crop_cap+=len(pred)==300;tiled.extend(pred)
        torch.cuda.synchronize();tile_ms=(time.perf_counter()-t)*1000
        for name,candidates in [('tiles384_only',tiled),('global640_plus_tiles384',global_preds['global640']+tiled)]:
            t=time.perf_counter();merged,dropped=merge(candidates);merge_ms=(time.perf_counter()-t)*1000
            truncation[name]+=dropped>0
            this_truncation[name]=int(dropped>0)
            strategies[name].append({**row,'predictions':merged})
            times[name].append(tile_ms+merge_ms+(global_times['global640'] if name.startswith('global') else 0))
        saved={'image':row['image'],'predictions':{name:strategies[name][-1]['predictions'] for name in strategies},
               'times':{name:times[name][-1] for name in strategies},'tile_count':len(origins),'crop_cap':this_crop_cap,'truncation':this_truncation}
        (output/f'image-{n:04}.json').write_text(json.dumps(saved),encoding='utf-8')
        if (n+1)%100==0:print(f'Processed {n+1}/{len(rows)} images',flush=True)
    if sha(checkpoint)!=evidence['checkpoint_sha256']:raise ValueError('Checkpoint changed.')
    for name,predictions in strategies.items():
        (output/f'{name}-predictions.json').write_text(json.dumps(predictions),encoding='utf-8')
    print('Scoring threshold sweeps and diagnostic AP.',flush=True)
    summary={name:summarize(predictions,times[name]) for name,predictions in strategies.items()}
    prior=next(p for p in evidence['threshold_curves'] if p['threshold']==.25)['overall']
    reconciliation={k:summary['global640']['fixed_025']['overall'][k]-prior[k] for k in ('tp','fp','fn')}
    report={'phase':'M2.03_RESOLUTION_AND_TILING','images':len(rows),'checkpoint_sha256':sha(checkpoint),'manifest_sha256':sha(data/'manifest.json'),
            'settings':{'confidence_floor':.001,'nms_iou':.7,'merge_iou':.7,'max_det':300,'tile_size':384,'tile_stride':288,
                        'tile_inference_imgsz':640,'precision':'FP32','batch':1,'device':torch.cuda.get_device_name(0),
                        'cuda_launch_blocking':True,'torch_threads':1,'timing_caveat':'Serialized CUDA safety workaround; compare strategies within this run, not against normal asynchronous deployment latency.'},
            'global640_baseline_count_differences':reconciliation,'tile_count_mean':statistics.mean(tile_counts),'tile_count_max':max(tile_counts),
            'prediction_cap_images_by_strategy':truncation,'tile_prediction_cap_count':crop_cap,'strategies':summary,
            'prediction_hashes':{name:sha(output/f'{name}-predictions.json') for name in strategies},
            'limits':['Historically used inherited-label DEV, not independent field evaluation.',
                      'Ghost-net evaluation is synthetic-on-synthetic; no real net claim.',
                      'Tiles cover edges using shifted full tiles rather than padded slivers. This is an experimental strategy, not a production detector modification.',
                      'Global+tiles always runs tiles; production conditional tiling is not being certified.',
                      'Finite DEV threshold grid is exploratory selection, not deployment calibration.',
                      'Diagnostic AP uses declared confidence-ordered matching and cannot replace previous validator AP without protocol reconciliation.'],
            'training_calls':0,'hf_calls':0,'production_changed':False}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,6))
    for name,s in summary.items():
        pts=[p['overall'] for p in s['threshold_curves'] if p['overall']['tp']+p['overall']['fp']]
        ax.plot([p['recall'] for p in pts],[p['precision'] for p in pts],marker='.',label=name)
    ax.axhline(.8,linestyle=':',color='gray');ax.axvline(.8,linestyle=':',color='gray');ax.set(xlim=(0,1),ylim=(0,1.02),xlabel='Recall',ylabel='Precision',title='M2.03 DEV processing comparison');ax.legend();ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(output/'comparison.png',dpi=150);plt.close(fig)
    table=''
    for name,s in summary.items():
        m=s['fixed_025']['overall'];table+=f'<tr><td>{html.escape(name)}</td><td>{m["precision"]:.2%}</td><td>{m["recall"]:.2%}</td><td>{m["fp"]}</td><td>{s["timing"]["wall_mean_ms"]:.1f}</td></tr>'
    (output/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2.03 comparison</title><style>body{background:#07151e;color:#dceaf0;font:16px system-ui;padding:28px;max-width:1100px;margin:auto}h1{color:#6cdaee}td,th{padding:12px;border-bottom:1px solid #315461;text-align:left}table{width:100%;display:block;overflow:auto}img{max-width:100%}a{color:#6cdaee}</style><h1>M2.03 · Resolution and tiling comparison</h1><p>Preserved epoch-59 detector · 1,129 historically used DEV images · no training. Fixed confidence 0.25; timing is synchronized local prediction and merge, excluding disk decode, fusion and network. Ghost-net data is synthetic.</p><table><tr><th>Strategy</th><th>Precision</th><th>Recall</th><th>FP</th><th>Mean ms/image</th></tr>'+table+'</table><p><a href="report.json">Full class, size, threshold and timing evidence</a></p><img src="comparison.png" alt="Precision recall comparison"></html>',encoding='utf-8')
    print(json.dumps({name:{'fixed_025':s['fixed_025']['overall'],'best_f1':s['best_grid_f1']['overall'],'passes_80_80':s['passes_80_80_on_grid'],'time_ms':s['timing']['wall_mean_ms'],'ap':s['diagnostic_ap']['mAP50']} for name,s in summary.items()},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resume-from',type=Path)
    a=p.parse_args();run(a.root,a.output,a.resume_from)
