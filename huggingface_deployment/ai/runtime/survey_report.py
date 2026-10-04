"""Portable raw-survey reports with explicit missing geometry and source labels."""
import csv
import json
from pathlib import Path

FIELDS=['analysis_id','candidate_id','bbox_x1_px','bbox_y1_px','bbox_x2_px','bbox_y2_px','bbox_width_px','bbox_height_px','detector_confidence_percent','acquisition_flags','class_id','class_name','detector_confidence','fusion_score','decision','latitude','longitude','estimated_width_m','estimated_height_m','localization_status','dimension_status','channel','source_window','source_log_sha256','source','calibration_status','geometry_status']


def write_report(output,configuration,state):
    output=Path(output);rows=[];features=[]
    for index in range(state['windows_completed']):
        response=json.loads((output/f'window-{index:05d}.json').read_text(encoding='utf-8'))
        reference=response['survey_reference']
        for c in response['candidates']:
            location=c.get('localization',{});point=location.get('coordinates',{}).get('geographic') or {};dimensions=location.get('physical_dimensions') or {}
            row=dict(candidate_id=c['candidate_id'],class_id=c['detection']['class_id'],class_name=c['detection']['class_name'],detector_confidence=c['detection']['confidence'],fusion_score=c.get('decision',{}).get('fusion_score'),decision='REVIEW',latitude=point.get('latitude'),longitude=point.get('longitude'),estimated_width_m=dimensions.get('width_m'),estimated_height_m=dimensions.get('height_m'),localization_status=location.get('metadata',{}).get('status','PIXEL_ONLY'),dimension_status=dimensions.get('status','UNAVAILABLE'),channel=reference['channel'],source_window=index,source_log_sha256=configuration['source_log_sha256'],source='LOCAL_RAW_SURVEY_INFERENCE',calibration_status='UNAVAILABLE',geometry_status=reference.get('geometry',{}).get('status','UNAVAILABLE'))
            x1,y1,x2,y2=c['detection']['bbox']
            row.update(analysis_id=response.get('analysis_id'),bbox_x1_px=x1,bbox_y1_px=y1,bbox_x2_px=x2,bbox_y2_px=y2,bbox_width_px=x2-x1,bbox_height_px=y2-y1,detector_confidence_percent=100*c['detection']['confidence'],acquisition_flags='|'.join(f['code'] for f in c.get('quality',{}).get('image',{}).get('flags',[])))
            rows.append(row)
            if point:features.append(dict(type='Feature',geometry=dict(type='Point',coordinates=[point['longitude'],point['latitude']]),properties=row))
    with (output/'report.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    report=dict(version='raw-survey-report-v1',source='LOCAL_RAW_SURVEY_INFERENCE',configuration=configuration,job_status=state['status'],windows_completed=state['windows_completed'],observation_count=len(rows),unique_contact_count=state.get('reconciled_contact_count'),rows_are='PER_WINDOW_OBSERVATIONS_OVERLAPS_MAY_REPEAT_CONTACTS',confidence_meaning='DETECTOR_SCORE_NOT_CALIBRATED_PROBABILITY_OF_CORRECTNESS',calibration='UNAVAILABLE',field_accuracy='NOT_EVALUATED',rows=rows)
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    (output/'contacts.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=features,field_accuracy='NOT_EVALUATED',source='LOCAL_RAW_SURVEY_INFERENCE'),indent=2,allow_nan=False),encoding='utf-8')
    return len(rows)
