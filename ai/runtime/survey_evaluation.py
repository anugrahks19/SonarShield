"""Locked class-correct object evaluation; never fits a threshold or model."""
import math
from ai.schemas.class_map import CLASS_ID_TO_NAME


def iou(a, b):
    area = max(0,min(a[2],b[2])-max(a[0],b[0])) * max(0,min(a[3],b[3])-max(a[1],b[1]))
    return area/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-area)


def box(obj, width, height):
    coords = obj['bbox']
    if type(obj['class_id']) is not int or obj['class_id'] not in CLASS_ID_TO_NAME:
        raise ValueError('Unknown class ID.')
    if len(coords)!=4 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in coords):
        raise ValueError('Invalid box.')
    x1,y1,x2,y2=coords
    if not 0<=x1<x2<=width or not 0<=y1<y2<=height:
        raise ValueError('Box exceeds original image coordinates.')


def wilson(success, total):
    if total == 0: return None
    z=1.959964; p=success/total; d=1+z*z/total
    center=(p+z*z/(2*total))/d
    margin=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return [max(0,center-margin),min(1,center+margin)]


def evaluate(manifest, annotations, predictions):
    """Predeclared exploratory gate: all five classes, P/R>=.90, >=30 GT/class, >=20 negatives."""
    entries=manifest['images']; lookup={e['image_sha256']:e for e in entries}
    if len(lookup)!=len(entries): raise ValueError('Duplicate raster across splits.')
    days={}; sources={}
    for e in entries:
        if e['split'] not in {'DEV','CALIBRATION','TEST'}: raise ValueError('Invalid split.')
        for key,groups in [('day',days),('source_sha256',sources)]:
            groups.setdefault(e[key],set()).add(e['split'])
        if e['rendering_version']!='LOG1P_PERCENTILE_V1': raise ValueError('Rendering mismatch.')
    if any(len(v)>1 for v in list(days.values())+list(sources.values())):
        raise ValueError('Acquisition day/source overlaps the holdout.')
    truth={a['image_sha256']:a for a in annotations['annotations']}
    pred={p['image_sha256']:p for p in predictions['images']}
    if len(truth)!=len(annotations['annotations']) or len(pred)!=len(predictions['images']):
        raise ValueError('Duplicate annotation/prediction identity.')
    if any(k not in lookup for k in set(truth)|set(pred)): raise ValueError('Unknown image identity.')
    expected={'detector':'b5e475286d7703288719c52e0b31044588c0e114bd426d60057c0f695eaa3605',
              'fusion':'b57dc4e7c9eb713c11a716c72e1087a7f3e942811779d01978527b669ef9d02b'}
    if predictions.get('artifacts')!=expected or predictions.get('rendering_source_sha256')!=manifest['rendering_source_sha256']:
        raise ValueError('Frozen artifacts/rendering identity mismatch.')
    if predictions.get('operating_point')!={'detector_confidence_min':0.15,'tiled':True,'matching_iou':0.5}:
        raise ValueError('Operating point differs from the predeclared evaluation.')
    counts={c:{'tp':0,'fp':0,'fn':0} for c in CLASS_ID_TO_NAME}
    test=[e for e in entries if e['split']=='TEST']; negatives=0; failures=[]; observations=[]
    if not test: raise ValueError('No reserved test images.')
    for e in test:
        key=e['image_sha256']; a=truth.get(key); p=pred.get(key)
        if not a or a.get('status') not in {'TARGETS_CONFIRMED','BACKGROUND_CONFIRMED'} or not a.get('reviewer','').strip() or a.get('qualified_review') is not True:
            raise ValueError('Every TEST image needs a qualified independent confirmed review; unreviewed is not background.')
        if not p: raise ValueError('Missing TEST prediction; failed images cannot be omitted.')
        gt=a['objects']; detections=p['objects']
        if (a['status']=='BACKGROUND_CONFIRMED') != (len(gt)==0): raise ValueError('Annotation outcome disagrees with boxes.')
        if not gt: negatives+=1
        for obj in gt+detections: box(obj,e['width'],e['height'])
        for obj in detections:
            score=obj['confidence']
            if not isinstance(score,(int,float)) or isinstance(score,bool) or not math.isfinite(score) or not .15<=score<=1:
                raise ValueError('Invalid prediction score or undeclared filtering.')
        used=set(); image_tp=0
        for d in sorted(detections,key=lambda o:-o['confidence']):
            candidates=[(iou(d['bbox'],g['bbox']),j) for j,g in enumerate(gt) if j not in used and g['class_id']==d['class_id']]
            overlap,j=max(candidates,default=(0,-1))
            if overlap>=.5: used.add(j);counts[d['class_id']]['tp']+=1;image_tp+=1
            else:counts[d['class_id']]['fp']+=1
        for j,g in enumerate(gt):
            if j not in used:counts[g['class_id']]['fn']+=1
        observations.append({'image_sha256':key,'tp':image_tp,'fp':len(detections)-image_tp,'fn':len(gt)-image_tp})
    def summary(c):
        t,f,n=c['tp'],c['fp'],c['fn']
        return {**c,'support':t+n,'precision':t/(t+f) if t+f else None,'recall':t/(t+n) if t+n else None,
                'precision_wilson_95':wilson(t,t+f),'recall_wilson_95':wilson(t,t+n)}
    overall=summary({k:sum(c[k] for c in counts.values()) for k in ['tp','fp','fn']})
    classes={str(c):{'name':CLASS_ID_TO_NAME[c],**summary(v)} for c,v in counts.items()}
    for key,r in {'overall':overall,**classes}.items():
        if r['precision'] is None or r['recall'] is None or min(r['precision'],r['recall'])<.9:
            failures.append(f'{key}: precision/recall below 90% or unavailable')
    for key,r in classes.items():
        if r['support']<30: failures.append(f'class {key}: fewer than 30 confirmed targets')
    if negatives<20: failures.append('Fewer than 20 confirmed TEST background windows')
    # This day split can measure performance; it cannot independently certify a new public domain.
    if manifest.get('independent_external_validation') is not True:
        failures.append('Independent external survey validation not supplied')
    development_groups={e.get('acquisition_group') for e in entries if e['split']!='TEST'}
    test_groups={e.get('acquisition_group') for e in test}
    if None in test_groups or not test_groups or test_groups & development_groups:
        failures.append('TEST survey groups are missing or overlap DEV/CALIBRATION survey groups')
    if manifest.get('split_provenance_verified') is not True:
        failures.append('Survey-line independence and training-overlap audit not verified')
    return {'version':1,'scope':'CLASS_CORRECT_ONE_TO_ONE_OBJECTS_IOU_0.50_NOT_SYSTEM_ACCURACY',
            'public_xtf_enabled':False,'accuracy_checks_passed':not failures,
            'release_requires_reviewed_signed_evidence':True,'gate_failures':failures,
            'test_images':len(test),'confirmed_background_images':negatives,'overall':overall,
            'classes':classes,'per_image':observations,'artifacts':predictions['artifacts'],
            'operating_point':predictions['operating_point'],
            'limitations':['WILSON_INTERVALS_DO_NOT_ACCOUNT_FOR_SURVEY_CORRELATION','NO_MAP_METRICS_COMPUTED','NO_FIELD_GEOMETRY_VERIFICATION','NO_CALIBRATION_CERTIFICATION']}
