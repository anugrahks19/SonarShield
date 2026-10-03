"""Deterministic acquisition warnings and survey contact reconciliation; no fitting."""
import numpy as np

def acquisition_quality(block):
    data=np.vstack([row['samples'] for row in block]); maximum=np.iinfo(data.dtype).max
    zeros=np.mean(np.all(data==0,axis=1)); saturation=float(np.mean(data==maximum))
    numbers=[row['ping_number'] for row in block]
    gaps=sum(b>a+1 for a,b in zip(numbers,numbers[1:])); reversals=sum(b<=a for a,b in zip(numbers,numbers[1:]))
    flags=[]
    if zeros: flags.append('ZERO_SAMPLE_ROWS')
    if saturation>=0.2: flags.append('HIGH_FULL_SCALE_SATURATION_HEURISTIC')
    if gaps: flags.append('PING_SEQUENCE_GAPS')
    if reversals: flags.append('PING_SEQUENCE_NONMONOTONIC')
    flags.extend(['CHANNEL_ORIENTATION_UNVERIFIED','NAVIGATION_AND_POSE_UNVERIFIED','MOTION_CORRECTION_NOT_APPLIED'])
    return dict(zero_row_fraction=float(zeros),full_scale_fraction=saturation,ping_sequence_gaps=gaps,ping_sequence_reversals=reversals,flags=flags,assessment='DETERMINISTIC_FLAGS_NOT_FIELD_VALIDATED',correction='NONE_ORIGINAL_SAMPLES_RETAINED')

def reconcile(contacts,threshold=0.7):
    # Only comparable same-channel/render-segment/sample-grid contacts can merge.
    kept=[]
    for contact in sorted(contacts,key=lambda c:(-c['confidence'],c['window'],c['candidate_id'])):
        duplicate=None
        for previous in kept:
            if (previous['channel'],previous['segment'],previous['class_id'])!=(contact['channel'],contact['segment'],contact['class_id']):continue
            if previous.get('grid_identity')!=contact.get('grid_identity'):continue
            a=previous['source_box'];b=contact['source_box']
            intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
            area=(a[2]-a[0])*(a[3]-a[1]);other=(b[2]-b[0])*(b[3]-b[1])
            if area<=0 or other<=0: continue
            if intersection/(area+other-intersection)>threshold or (intersection/min(area,other)>=0.95 and min(area,other)/max(area,other)>=0.5):duplicate=previous;break
        reference=dict(window=contact['window'],candidate_id=contact['candidate_id'])
        if duplicate: duplicate['observations'].append(reference)
        else:kept.append(dict(contact,observations=[reference]))
    return kept
