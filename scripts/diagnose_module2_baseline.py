"""DEV-only detection diagnostics. No training, calibration fitting or promotion."""
import argparse
import collections
import html
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import NAMES, parse_labels, sha
from scripts.evaluate_interrupted_run import iou

THRESHOLDS = [.001, .005, .01, .025, .05, .075, .1, .15, .2, .25, .3, .4, .5, .6, .7, .8, .9, .95]


def match(gt, predictions, threshold):
    used = set(); decisions = []
    for p in sorted((p for p in predictions if p['confidence'] >= threshold), key=lambda p: -p['confidence']):
        overlap, j = max(((iou(p['box'], g['box']), j) for j, g in enumerate(gt)
                          if p['class'] == g['class'] and j not in used), default=(0, -1))
        correct = overlap >= .5
        if correct: used.add(j)
        decisions.append((p, j if correct else None))
    return decisions, used


def metrics(counts):
    t, f, n = (counts[k] for k in ('tp', 'fp', 'fn'))
    p = t / (t + f) if t + f else 0
    r = t / (t + n) if t + n else 0
    return {**counts, 'precision': p, 'recall': r, 'f1': 2*p*r/(p+r) if p+r else 0}


def bucket(box, width, height):
    area = max(0, box[2]-box[0]) * max(0, box[3]-box[1]) * (640/max(width, height))**2
    return 'small' if area < 32**2 else 'medium' if area < 96**2 else 'large'


def aggregate(rows, threshold):
    counts = {c: dict(tp=0, fp=0, fn=0) for c in NAMES}
    for row in rows:
        decisions, used = match(row['gt'], row['predictions'], threshold)
        for p, j in decisions: counts[p['class']]['tp' if j is not None else 'fp'] += 1
        for j, g in enumerate(row['gt']):
            if j not in used: counts[g['class']]['fn'] += 1
    total = {k: sum(c[k] for c in counts.values()) for k in ('tp', 'fp', 'fn')}
    return {'threshold': threshold, 'overall': metrics(total), 'per_class': {str(c): metrics(v) for c,v in counts.items()}}


def run(root, output, predictions_cache=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Fresh output directory required.')
    baseline = json.loads((root/'docs/metrics/module2-baseline-20261003.json').read_text())
    dataset = root/'datasets/controlled_v8a_20261003'
    checkpoint = root/'.temp/module2-baseline-preserved-20261003/best.pt'
    if sha(checkpoint) != baseline['archive_sha256']['best.pt'] or sha(dataset/'manifest.json') != baseline['archive_sha256']['manifest.json']:
        raise ValueError('Baseline identity mismatch.')
    manifest = json.loads((dataset/'manifest.json').read_text())
    expected = {Path(r['image']).resolve(): r for r in manifest['records'] if r['split']=='DEV'}
    print('Checking all DEV image/annotation hashes.', flush=True)
    for path,r in expected.items():
        if sha(path)!=r['image_sha256'] or sha(r['label'])!=r['label_sha256']: raise ValueError('DEV bytes changed.')
    output.mkdir(parents=True)
    rows=[];seen=set()
    if predictions_cache:
        predictions_cache=Path(predictions_cache)
        sibling=json.loads((predictions_cache.parent/'report.json').read_text())
        if sibling['checkpoint_sha256']!=sha(checkpoint) or sibling['manifest_sha256']!=sha(dataset/'manifest.json') or sibling['settings']!={'imgsz':640,'conf_floor':.001,'nms_iou':.7,'max_det':300,'half':False,'batch':1,'device':0}:
            raise ValueError('Cache settings/identities mismatch.')
        rows=json.loads(predictions_cache.read_text())
        if len(rows)!=len(expected):raise ValueError('Incomplete cache.')
        for row in rows:
            path=Path(row['image']).resolve()
            if path not in expected or path in seen:raise ValueError('Unexpected/duplicate cache image.')
            seen.add(path);w,h=row['width'],row['height']
            expected_gt=[{'class':c,'box':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]} for c,x,y,bw,bh in parse_labels(Path(expected[path]['label']).read_text())]
            if row['gt']!=expected_gt or row['source_image']!=expected[path]['source_image']:raise ValueError('Cache ground truth differs.')
        results=[]
        print('Reusing verified cached predictions; no new inference.',flush=True)
    else:
        from ultralytics import YOLO
        model=YOLO(str(checkpoint))
        if model.names!=NAMES: raise ValueError('Class map mismatch.')
        print('Caching 640px GPU predictions, confidence floor 0.001, max_det=300, FP32, batch=1.',flush=True)
        results=model.predict(source=str(dataset/'images/val'),device=0,imgsz=640,batch=1,
                                conf=.001,iou=.7,max_det=300,half=False,save=False,verbose=False,stream=True)
    for result in results:
        path=Path(result.path).resolve()
        if path not in expected or path in seen: raise ValueError('Unexpected/duplicate DEV image.')
        seen.add(path);r=expected[path];h,w=result.orig_shape
        gt=[{'class':c,'box':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]}
            for c,x,y,bw,bh in parse_labels(Path(r['label']).read_text())]
        pred=[{'class':int(c),'confidence':float(s),'box':b.tolist()} for c,s,b in
              zip(result.boxes.cls.cpu(),result.boxes.conf.cpu(),result.boxes.xyxy.cpu())]
        rows.append({'image':str(path),'source_image':r['source_image'],'width':w,'height':h,'gt':gt,'predictions':pred})
        if len(rows)%100==0: print(f'Cached {len(rows)}/{len(expected)} images',flush=True)
    if seen!=set(expected) or sha(checkpoint)!=baseline['archive_sha256']['best.pt']: raise ValueError('Incomplete/changed baseline.')
    (output/'predictions.json').write_text(json.dumps(rows),encoding='utf-8')
    curves=[aggregate(rows,t) for t in THRESHOLDS]
    fixed=next(c for c in curves if c['threshold']==.25)
    # Lower confidence candidates can compete in NMS; measure rather than assume equality with the earlier .25 pass.
    previous=baseline['baseline']['object_metrics']
    reconciliation={k:{'previous':previous[k],'cached_low_floor_at_025':fixed['overall'][k],
                      'difference':fixed['overall'][k]-previous[k]} for k in ('tp','fp','fn')}
    sizes={str(c):{s:{'gt':0,'matched':0} for s in ('small','medium','large')} for c in NAMES}
    reasons={str(c):{'miss':collections.Counter(),'fp':collections.Counter()} for c in NAMES}
    queue=[];gallery=[];namespace=collections.Counter()
    for row in rows:
        gt,pred=row['gt'],row['predictions'];decisions,used=match(gt,pred,.25)
        retained=[p for p in pred if p['confidence']>=.25]
        namespace[Path(row['source_image']).name.split('_')[0]]+=1
        for j,g in enumerate(gt):
            size=bucket(g['box'],row['width'],row['height']);stats=sizes[str(g['class'])][size];stats['gt']+=1
            if j in used: stats['matched']+=1;continue
            same=[p for p in pred if p['class']==g['class']]
            potential=max((iou(p['box'],g['box']) for p in same if p['confidence']<.25),default=0)
            same_high=max((iou(p['box'],g['box']) for p in same if p['confidence']>=.25),default=0)
            wrong=max((iou(p['box'],g['box']) for p in retained if p['class']!=g['class']),default=0)
            reason=('low_score_overlap' if potential>=.5 else 'same_class_competition' if same_high>=.5 else
                    'wrong_class_overlap' if wrong>=.5 else 'localization_overlap' if same_high>=.1 else 'no_retained_overlap')
            reasons[str(g['class'])]['miss'][reason]+=1
            queue.append({'image':row['image'],'kind':'miss','class':g['class'],'gt_index':j,'size':size,
                          'reason':reason,'best_low_score_same_class_iou':potential,'best_retained_same_class_iou':same_high})
        for p,j in decisions:
            if j is not None:continue
            same=max((iou(p['box'],g['box']) for g in gt if g['class']==p['class']),default=0)
            wrong=max((iou(p['box'],g['box']) for g in gt if g['class']!=p['class']),default=0)
            reason='duplicate_overlap' if same>=.5 else 'wrong_class_overlap' if wrong>=.5 else 'localization_overlap' if same>=.1 else 'unmatched_region'
            reasons[str(p['class'])]['fp'][reason]+=1
            queue.append({'image':row['image'],'kind':'fp','class':p['class'],'reason':reason,'confidence':p['confidence'],'box':p['box']})
    for per_class in sizes.values():
        for s in per_class.values():s['recall']=s['matched']/s['gt'] if s['gt'] else None
    best=max(curves,key=lambda c:c['overall']['f1'])
    report={'phase':'M2.02_DIAGNOSE_FAILURES','images':len(rows),'checkpoint_sha256':sha(checkpoint),
            'manifest_sha256':sha(dataset/'manifest.json'),'settings':{'imgsz':640,'conf_floor':.001,'nms_iou':.7,'max_det':300,'half':False,'batch':1,'device':0},
            'threshold_curves':curves,'best_grid_micro_f1':best,'meets_80_80_overall_on_grid':[c['threshold'] for c in curves if c['overall']['precision']>=.8 and c['overall']['recall']>=.8],
            'meets_80_80_per_class_on_grid':{str(c):[x['threshold'] for x in curves if x['per_class'][str(c)]['precision']>=.8 and x['per_class'][str(c)]['recall']>=.8] for c in NAMES},
            'fixed_025_reconciliation':reconciliation,'size_recall_at_025':sizes,'overlap_diagnostics_at_025':reasons,
            'filename_namespace_counts':dict(namespace),
            'namespace_metrics_at_025':{key:aggregate([r for r in rows if Path(r['source_image']).name.split('_')[0]==key],.25)['overall'] for key in namespace},
            'predictions_sha256':sha(output/'predictions.json'),
            'images_without_inherited_gt':sum(not r['gt'] for r in rows),
            'capped_prediction_images':sum(len(r['predictions'])==300 for r in rows),
            'source_warning':'Drishti V3 README identifies ghost_net as 100% synthetic; this class evaluation is not field evidence.',
            'limits':['DEV historically used; inherited labels are not expert-certified.','Overlap categories are diagnostic hypotheses, not verified causes.',
                      'Sizes use area after longest-side scaling to 640; no physical dimensions inferred.',
                      'Filename namespaces are not acquisition/site identifiers.','Sweep is finite, uses post-NMS predictions above 0.001, and is not calibration or final threshold selection.'],
            'training_calls':0,'hf_calls':0,'new_detector_prediction_passes':0 if predictions_cache else 1}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (output/'review-queue.json').write_text(json.dumps(queue,indent=2),encoding='utf-8')
    # Bound gallery to representative errors plus deterministic randomly selected control images.
    by_image={r['image']:r for r in rows};selected=[];selection_set=set()
    for c in (0,2,4,1,3):
        for kind in ('miss','fp'):
            for item in [q for q in queue if q['class']==c and q['kind']==kind]:
                key=(c,kind,item['image'])
                if key not in selection_set:
                    selected.append((item['image'],f'{NAMES[c]}: {kind}, {item["reason"]}'));selection_set.add(key)
                if sum(k[0]==c and k[1]==kind for k in selection_set)>=6:break
    rng=random.Random(0)
    selected.extend((r['image'],'Random control — not a certified negative') for r in rng.sample(rows,10))
    from PIL import Image,ImageDraw
    assets=output/'gallery';assets.mkdir()
    for n,(path,title) in enumerate(selected):
        row=by_image[path];image=Image.open(path).convert('RGB');image.thumbnail((1000,700))
        draw=ImageDraw.Draw(image);sx,sy=image.width/row['width'],image.height/row['height']
        for g in row['gt']:
            box=[v*(sx if i%2==0 else sy) for i,v in enumerate(g['box'])];draw.rectangle(box,outline='#53e3b4',width=2)
            draw.text((box[0],max(0,box[1]-12)),f'GT {NAMES[g["class"]]}',fill='#53e3b4',stroke_width=1,stroke_fill='black')
        for p in row['predictions']:
            if p['confidence']<.25:continue
            box=[v*(sx if i%2==0 else sy) for i,v in enumerate(p['box'])];draw.rectangle(box,outline='#ffb660',width=2)
            draw.text((box[0],box[1]+2),f'{NAMES[p["class"]]} {p["confidence"]:.2f}',fill='#ffb660',stroke_width=1,stroke_fill='black')
        image.save(assets/f'{n:03}.png')
        gallery.append(f'<article><h3>{html.escape(title)}</h3><p>{html.escape(Path(path).name)}</p><img src="gallery/{n:03}.png" alt="Ground truth and predicted boxes"></article>')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,6))
    for key,name in [('overall','overall')]+[(str(c),NAMES[c]) for c in NAMES]:
        points=[x['overall'] if key=='overall' else x['per_class'][key] for x in curves]
        points=[p for p in points if p['tp']+p['fp']>0]
        ax.plot([p['recall'] for p in points],[p['precision'] for p in points],marker='.',label=name)
    ax.axvline(.8,color='gray',linestyle=':');ax.axhline(.8,color='gray',linestyle=':');ax.set(xlim=(0,1.02),ylim=(0,1.02),xlabel='Recall',ylabel='Precision',title='DEV threshold sweep — class-correct IoU ≥ 0.50')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(output/'precision-recall.png',dpi=150);plt.close(fig)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2.02 failure diagnosis</title><style>body{background:#07151e;color:#dceaf0;font:16px system-ui;margin:0;padding:28px}main{max-width:1200px;margin:auto}h1,h2{color:#6cdaee}p{line-height:1.6}img{max-width:100%;height:auto}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:20px}article{background:#102630;border:1px solid #315461;border-radius:10px;padding:16px;overflow-wrap:anywhere}a{color:#6cdaee}</style><main><h1>M2.02 · DEV failure diagnosis</h1><p>Archived epoch-59 detector, 640px. Green: inherited ground truth. Orange: predictions at confidence ≥0.25. Overlap labels are hypotheses requiring review; these are not confirmed field errors. No training or HF calls.</p><p><a href="report.json">Metrics and threshold sweep</a> · <a href="review-queue.json">Full annotation review queue</a></p><h2>Precision / recall across thresholds</h2><img src="precision-recall.png" alt="DEV precision recall curves"><h2>Representative errors and random controls</h2><section>'''+''.join(gallery)+'</section></main></html>'
    (output/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({'images':len(rows),'best_grid_micro_f1':best,'passes_80_80':report['meets_80_80_overall_on_grid'],'reconciliation':reconciliation,'size_recall':sizes,'overlap_diagnostics':reasons,'gallery_images':len(gallery)},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--predictions-cache',type=Path)
    a=p.parse_args();run(a.root,a.output,a.predictions_cache)
