"""Local durable survey job. Bounded windows, progress, explicit cancellation, restart."""
import json, os
from pathlib import Path
import cv2
from ai.runtime.pipeline import AnalysisRuntime, sha256_file
from ai.runtime.xtf import packets, windows
from ai.runtime.survey import reconcile

def write_json(path,value):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8');temp.replace(path)

def run_job(log,output,device='cpu',max_windows=10,rows=512,overlap=64,tiled=True,cancel_file=None,resume=False,runtime=None):
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
        runtime=runtime or AnalysisRuntime(device=device)
        runtime.initialize()
        identity=dict(artifacts=runtime.hashes,pipeline_sha256=sha256_file(Path(__file__).with_name('pipeline.py')),source_log_sha256=sha256_file(log),device=device,max_windows=max_windows,rows=rows,overlap=overlap,tiled=tiled)
        old=json.loads(state_path.read_text()) if state_path.exists() else None
        if old and not resume:raise ValueError('Existing job: use resume or a new output directory.')
        if old and old['configuration']!=identity:raise ValueError('Resume configuration/source disagrees with original job.')
        done=old.get('windows_completed',0) if old else 0
        state=dict(version=1,status='RUNNING',configuration=identity,windows_completed=done,geographic='UNAVAILABLE',rendering='UNVALIDATED')
        write_json(state_path,state)
        count=0
        for index,(gray,reference) in enumerate(windows(packets(log),rows=rows,overlap=overlap)):
            if index>=max_windows:break
            count=index+1
            if cancel_file and Path(cancel_file).exists():state['status']='CANCELLED';break
            if index<done:
                if not (output/f'window-{index:05d}.json').is_file():raise ValueError('Completed window is missing; resume rejected.')
                continue
            ok,encoded=cv2.imencode('.png',gray)
            if not ok:raise RuntimeError('Window encoding failed.')
            image=output/f'window-{index:05d}.png';image.write_bytes(encoded.tobytes())
            response=runtime.analyze(encoded.tobytes(),image.name,tiled).model_dump()
            response['survey_reference']=dict(source_log_sha256=identity['source_log_sha256'],window=index,**reference)
            for candidate in response['candidates']:
                y1,y2=candidate['detection']['bbox'][1::2]
                candidate['source_ping_reference']=dict(channel=reference['channel'],row_min=y1,row_max=y2,ping_numbers=reference['ping_numbers'][max(0,int(y1)):min(len(reference['ping_numbers']),int(y2)+1)])
                for flag in reference['acquisition_quality']['flags']:candidate['quality']['image']['flags'].append(dict(code=flag,severity='WARNING'))
            write_json(output/f'window-{index:05d}.json',response)
            state['windows_completed']=index+1;write_json(state_path,state)
        if state['status']=='RUNNING':state['status']='BOUNDED_COMPLETE' if count>=max_windows else 'COMPLETE'
        contacts=[]
        for index in range(state['windows_completed']):
            response=json.loads((output/f'window-{index:05d}.json').read_text());ref=response['survey_reference']
            for candidate in response['candidates']:
                x1,y1,x2,y2=candidate['detection']['bbox'];first=ref['row_indices'][0]
                contacts.append(dict(window=index,candidate_id=candidate['candidate_id'],class_id=candidate['detection']['class_id'],class_name=candidate['detection']['class_name'],confidence=candidate['detection']['confidence'],channel=ref['channel'],segment=ref['segment'],source_box=[x1,first+y1,x2,first+y2],decision='REVIEW',geographic='UNAVAILABLE'))
        merged=reconcile(contacts);write_json(output/'contacts.json',dict(source_log_sha256=identity['source_log_sha256'],coordinate_system='SAMPLE_COLUMN_CHANNEL_ROW_NOT_METRES',contacts=merged))
        state['reconciled_contact_count']=len(merged);write_json(state_path,state);return state
    except BaseException as exc:
        if state is not None:state['status']='CANCELLED' if isinstance(exc,KeyboardInterrupt) else 'FAILED';state['error_type']=type(exc).__name__;write_json(state_path,state)
        raise
    finally: lock.unlink(missing_ok=True)
