"""D1 resolution probe on historical DEV only. No fitting or release."""
import os
os.environ['CUDA_LAUNCH_BLOCKING']='1'
import argparse,json,time,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import NAMES,sha,parse_labels
from scripts.diagnose_module2_baseline import aggregate,match,bucket,THRESHOLDS

def summary(rows):
    curves=[aggregate(rows,t) for t in THRESHOLDS]
    sizes={str(c):{s:{'gt':0,'matched':0} for s in ('small','medium','large')} for c in NAMES}
    for row in rows:
        _,used=match(row['gt'],row['predictions'],.25)
        for j,g in enumerate(row['gt']):
            v=sizes[str(g['class'])][bucket(g['box'],row['width'],row['height'])];v['gt']+=1;v['matched']+=int(j in used)
    for strata in sizes.values():
        for v in strata.values():v['recall']=v['matched']/v['gt'] if v['gt'] else None
    return {'fixed_025':next(r for r in curves if r['threshold']==.25),'best_grid_f1':max(curves,key=lambda r:r['overall']['f1']),'threshold_curves':curves,'sizes_at_025':sizes,'passes_80_80_on_grid':[r['threshold'] for r in curves if r['overall']['precision']>=.8 and r['overall']['recall']>=.8],'cap_images':sum(len(r['predictions'])==300 for r in rows),'cap_affects_retained_025_images':sum(len(r['predictions'])==300 and min(p['confidence'] for p in r['predictions'])>=.25 for r in rows)}

def probe(root,cache,output):
    root,cache,output=map(lambda p:Path(p).resolve(),(root,cache,output))
    if output.exists():raise ValueError('Fresh output directory required.')
    previous=json.loads((cache.parent/'report.json').read_text(encoding='utf-8'))
    modelpath=root/'models/controlled/m2_d1_curated_r01_640_01/weights/best.pt';dataset=root/'datasets/mechanically_curated_r01_20261003'
    if sha(cache)!=previous['predictions_sha256'] or sha(modelpath)!=previous['checkpoint_sha256'] or sha(dataset/'manifest.json')!=previous['manifest_sha256']:raise ValueError('Probe/cache identities changed.')
    if previous['settings']!={'imgsz':640,'conf_floor':.001,'nms_iou':.7,'max_det':300,'half':False,'batch':1,'device':0}:raise ValueError('Unexpected cache processing.')
    rows=json.loads(cache.read_text(encoding='utf-8'));manifest=json.loads((dataset/'manifest.json').read_text(encoding='utf-8'))
    records={r['image']:r for r in manifest['records'] if r['split']=='DEV'}
    if len(rows)!=1129 or {r['image'] for r in rows}!=set(records):raise ValueError('Wrong DEV cache coverage.')
    for r in rows:
        source=records[r['image']]
        if sha(r['image'])!=source['image_sha256'] or sha(source['label'])!=source['label_sha256']:raise ValueError('DEV drift.')
        gt=[{'class':c,'box':[(x-w/2)*r['width'],(y-h/2)*r['height'],(x+w/2)*r['width'],(y+h/2)*r['height']]} for c,x,y,w,h in parse_labels(Path(source['label']).read_text(encoding='utf-8'))]
        if gt!=r['gt']:raise ValueError('Cached inherited GT differs.')
    import torch
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    from ultralytics import YOLO
    model=YOLO(str(modelpath))
    if model.names!=NAMES:raise ValueError('Class map mismatch.')
    output.mkdir(parents=True);higher=[];timings=[]
    for _ in range(2):model.predict(rows[0]['image'],imgsz=960,device=0,batch=1,conf=.001,iou=.7,max_det=300,half=False,verbose=False,save=False)
    print('Probing D1 960px on all historical DEV; no training.',flush=True)
    for n,row in enumerate(rows,1):
        torch.cuda.synchronize();start=time.perf_counter()
        result=model.predict(row['image'],imgsz=960,device=0,batch=1,conf=.001,iou=.7,max_det=300,half=False,verbose=False,save=False)[0]
        torch.cuda.synchronize();elapsed=(time.perf_counter()-start)*1000
        pred=[{'class':int(c),'confidence':float(s),'box':b.tolist()} for c,s,b in zip(result.boxes.cls.cpu(),result.boxes.conf.cpu(),result.boxes.xyxy.cpu())]
        saved={**row,'predictions':pred,'serialized_local_wall_ms':elapsed};higher.append(saved);timings.append(elapsed)
        (output/f'image-{n:04}.json').write_text(json.dumps(saved),encoding='utf-8')
        if n%100==0:print(f'Probed {n}/{len(rows)}',flush=True)
    if sha(modelpath)!=previous['checkpoint_sha256']:raise ValueError('Checkpoint changed during probe.')
    (output/'960-predictions.json').write_text(json.dumps(higher),encoding='utf-8')
    report={'phase':'M2.08_D1_RESOLUTION_PROBE','checkpoint_sha256':sha(modelpath),'manifest_sha256':sha(dataset/'manifest.json'),'640_cache_sha256':sha(cache),'960_cache_sha256':sha(output/'960-predictions.json'),'images':len(rows),'strategies':{'640':summary(rows),'960':summary(higher)},'960_serialized_mean_wall_ms':statistics.mean(timings),'limits':['Historically used DEV/inherited GT; no calibration or independent-test claim.','960 inference alone does not prove 960-trained model performance.','Serialized CUDA safety mode, one CPU thread; timing cannot be compared to normal D1 model-forward latency.','0.001 floor, max 300 predictions; finite post-NMS threshold screen.','Synthetic ghost-net evidence only.'],'training_calls':0,'hf_calls':0,'production_changed':False}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,5))
    for name,strategy in report['strategies'].items():
        pts=[r['overall'] for r in strategy['threshold_curves'] if r['overall']['tp']+r['overall']['fp']]
        ax.plot([p['recall'] for p in pts],[p['precision'] for p in pts],marker='.',label=name+'px D1')
    ax.axhline(.8,color='gray',linestyle=':');ax.axvline(.8,color='gray',linestyle=':');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Object recall',ylabel='Object precision',title='M2.08 D1: historical DEV threshold screen');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(output/'resolution-probe.png',dpi=150);plt.close(fig)
    print(json.dumps({k:{'fixed':v['fixed_025'],'best_f1':v['best_grid_f1'],'passes':v['passes_80_80_on_grid'],'sizes':v['sizes_at_025']} for k,v in report['strategies'].items()},indent=2),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--cache',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();probe(a.root,a.cache,a.output)
