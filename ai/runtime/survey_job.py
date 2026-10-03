"""Local durable survey job. Bounded windows, progress, explicit cancellation, restart."""
import json, os
from pathlib import Path
import cv2
from ai.runtime.pipeline import AnalysisRuntime, sha256_file
from ai.runtime.xtf import packets, windows
from ai.runtime.survey import reconcile

def write_json(path,value):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8');temp.replace(path)

def run_job(log,output,device='cpu',max_windows=10,rows=512,overlap=64,tiled=True,cancel_file=None,resume=False,runtime=None,geometry_profile=None):
    log=Path(log); output=Path(output)
    if not 1<=max_windows<=1000:raise ValueError('max_windows must be 1-1000.')
    if log.stat().st_size>2*1024**3:raise ValueError('Log exceeds 2 GiB.')
    output.mkdir(parents=True,exist_ok=True)
    lock=output/'.job.lock'
    try: descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise RuntimeError('Job directory is locked. Verify its process stopped before removing a stale .job.lock.')
    os.close(descriptor)
    state_path=output/'job.json';state=None
    try:
        profile=None
        if geometry_profile is not None:
            from ai.runtime.sonar_geometry import SurveyGeometry
            profile=SurveyGeometry.model_validate(geometry_profile)
            if profile.source_log_sha256!=sha256_file(log):raise ValueError('Geometry profile does not match the source-log hash.')
        runtime=runtime or AnalysisRuntime(device=device)
        runtime.initialize()
        identity=dict(artifacts=runtime.hashes,pipeline_sha256=sha256_file(Path(__file__).with_name('pipeline.py')),source_log_sha256=sha256_file(log),device=device,max_windows=max_windows,rows=rows,overlap=overlap,tiled=tiled)
        identity['geometry_profile']=profile.model_dump(mode='json') if profile is not None else None
        identity['processing_sources']={name:sha256_file(Path(__file__).with_name(name+'.py')) for name in ['xtf','survey_job','survey','sonar_geometry','survey_report','survey_viewer']}
        old=json.loads(state_path.read_text()) if state_path.exists() else None
        if old and not resume:raise ValueError('Existing job: use resume or a new output directory.')
        if old and old['configuration']!=identity:raise ValueError('Resume configuration/source disagrees with original job.')
        done=old.get('windows_completed',0) if old else 0
        outputs=old.get('outputs',[]) if old else []
        if len(outputs)!=done:raise ValueError('Resume output manifest is incomplete.')
        state=dict(version=1,status='RUNNING',configuration=identity,windows_completed=done,outputs=outputs,geographic='UNAVAILABLE',rendering='UNVALIDATED')
        write_json(state_path,state)
        count=0
        for index,(gray,reference) in enumerate(windows(packets(log),rows=rows,overlap=overlap,profile=profile)):
            if index>=max_windows:break
            count=index+1
            if cancel_file and Path(cancel_file).exists():state['status']='CANCELLED';break
            if index<done:
                for suffix,key in [('.json','analysis_sha256'),('.png','image_sha256')]:
                    artifact=output/f'window-{index:05d}{suffix}'
                    if not artifact.is_file() or sha256_file(artifact)!=outputs[index][key]:raise ValueError('Completed window is missing or changed; resume rejected.')
                continue
            ok,encoded=cv2.imencode('.png',gray)
            if not ok:raise RuntimeError('Window encoding failed.')
            image=output/f'window-{index:05d}.png';image.write_bytes(encoded.tobytes())
            response=runtime.analyze(encoded.tobytes(),image.name,tiled).model_dump()
            response['survey_reference']=dict(source_log_sha256=identity['source_log_sha256'],window=index,**reference)
            for candidate in response['candidates']:
                if profile is not None:
                    from ai.runtime.sonar_geometry import attach_localization
                    attach_localization(candidate,reference['geometry'])
                y1,y2=candidate['detection']['bbox'][1::2]
                zero_rows=reference['acquisition_quality']['zero_sample_row_indices']
                if any(y1<=row+.5<y2 for row in zero_rows):candidate['quality']['image']['flags'].append(dict(code='CANDIDATE_INTERSECTS_ACQUISITION_DROPOUT',severity='WARNING'))
                candidate['source_ping_reference']=dict(channel=reference['channel'],row_min=y1,row_max=y2,ping_numbers=reference['ping_numbers'][max(0,int(y1)):min(len(reference['ping_numbers']),int(y2)+1)])
                for flag in reference['acquisition_quality']['flags']:candidate['quality']['image']['flags'].append(dict(code=flag,severity='WARNING'))
            write_json(output/f'window-{index:05d}.json',response)
            if 'input' in response:
                from ai.runtime.survey_viewer import write_viewer
                write_viewer(output,index,response)
            state['outputs'].append(dict(image_sha256=sha256_file(image),analysis_sha256=sha256_file(output/f'window-{index:05d}.json')))
            state['windows_completed']=index+1;write_json(state_path,state)
        if state['status']=='RUNNING':state['status']='BOUNDED_COMPLETE' if count>=max_windows else 'COMPLETE'
        contacts=[]
        for index in range(state['windows_completed']):
            response=json.loads((output/f'window-{index:05d}.json').read_text());ref=response['survey_reference']
            for candidate in response['candidates']:
                x1,y1,x2,y2=candidate['detection']['bbox'];first=ref['row_indices'][0]
                contacts.append(dict(window=index,candidate_id=candidate['candidate_id'],class_id=candidate['detection']['class_id'],class_name=candidate['detection']['class_name'],confidence=candidate['detection']['confidence'],channel=ref['channel'],segment=ref['segment'],grid_identity=([ref['geometry']['width'],ref['geometry']['ground_resolution_m'],ref['geometry']['side']] if 'geometry' in ref else 'RAW_SAMPLE_GRID'),source_box=[x1,first+y1,x2,first+y2],decision='REVIEW',geographic=candidate.get('localization',{}).get('coordinates',{}).get('geographic'),physical_dimensions=candidate.get('localization',{}).get('physical_dimensions')))
        merged=reconcile(contacts);write_json(output/'contacts.json',dict(source_log_sha256=identity['source_log_sha256'],coordinate_system='RECTIFIED_GRID_COLUMN_CHANNEL_ROW' if profile is not None else 'SAMPLE_COLUMN_CHANNEL_ROW_NOT_METRES',contacts=merged))
        state['reconciled_contact_count']=len(merged)
        state['geographic']='OPERATOR_CONFIGURED_NOT_FIELD_VALIDATED' if profile is not None else 'UNAVAILABLE'
        from ai.runtime.survey_report import write_report
        state['report_observation_count']=write_report(output,identity,state)
        links=''.join(f'<li><a href="window-{i:05d}.html">Window {i}: image, evidence, human review</a></li>' for i in range(state['windows_completed']) if (output/f'window-{i:05d}.html').exists())
        (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>SONAR-SHIELD offline survey</title><h1>LOCAL RAW SURVEY INFERENCE</h1><p>No new inference runs when opening these files. Calibration unavailable; geometry not field validated.</p><a href="report.csv">CSV report</a> | <a href="report.json">JSON report</a> | <a href="contacts.geojson">Geographic observations</a><ul>'+links+'</ul>',encoding='utf-8')
        write_json(state_path,state);return state
    except BaseException as exc:
        if state is not None:state['status']='CANCELLED' if isinstance(exc,KeyboardInterrupt) else 'FAILED';state['error_type']=type(exc).__name__;write_json(state_path,state)
        raise
    finally: lock.unlink(missing_ok=True)
