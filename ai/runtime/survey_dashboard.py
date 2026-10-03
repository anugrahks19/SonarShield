"""Loopback-only XTF upload and bounded CPU jobs; no cloud or training calls."""
import argparse,base64,json,re,secrets,threading,uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from ai.runtime.survey_job import run_job

MAX_UPLOAD=2*1024**3
MAX_STORED=4*1024**3


class SurveyService:
    def __init__(self,root,runner=run_job):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.runner=runner;self.token=secrets.token_urlsafe(32);self.lock=threading.Lock();self.active=None;self.jobs={}
        # Restore job listings only. Restarting never launches inference.
        for folder in sorted(self.root.iterdir()):
            if not folder.is_dir() or not re.fullmatch(r'[a-f0-9]{32}',folder.name):continue
            manifest=folder/'dashboard.json'
            if not manifest.is_file() or manifest.stat().st_size>65536:continue
            try:
                value=json.loads(manifest.read_text());state=folder/'results/job.json'
                if value.get('id')!=folder.name or not isinstance(value.get('options'),dict):continue
                if state.exists():
                    saved=json.loads(state.read_text());value.update(status=saved['status'],windows_completed=saved['windows_completed'])
                if value['status'] in ('UPLOADING','RUNNING'):value.update(status='FAILED',error='Dashboard restarted; resume explicitly after verifying the previous process stopped.')
                self.jobs[folder.name]=value
            except (OSError,ValueError,KeyError,TypeError):continue

    def reserve(self,size,options):
        if not 1024<=size<=MAX_UPLOAD:raise ValueError('XTF upload must be 1 KiB to 2 GiB.')
        if set(options)-{'rows','overlap','max_windows','geometry_profile'}:raise ValueError('Unknown job settings.')
        rows=options.get('rows',128);overlap=options.get('overlap',16);maximum=options.get('max_windows',4)
        if any(type(v) is not int for v in (rows,overlap,maximum)) or not 16<=rows<=512 or not 0<=overlap<rows or not 1<=maximum<=100:raise ValueError('Invalid bounded window settings.')
        profile=options.get('geometry_profile')
        if profile is not None:
            from ai.runtime.sonar_geometry import SurveyGeometry
            profile=SurveyGeometry.model_validate(profile).model_dump(mode='json')
        with self.lock:
            if self.active:raise RuntimeError('Another upload or CPU job is active. Cancel or wait; no job was queued.')
            if len(self.jobs)>=10:raise ValueError('This session reached ten jobs; use a new private output directory.')
            used=sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file())
            if used+size>MAX_STORED:raise ValueError('Private dashboard storage budget is 4 GiB. Archive results before another upload.')
            job=uuid.uuid4().hex;folder=self.root/job;folder.mkdir()
            value=dict(id=job,status='UPLOADING',windows_completed=0,options=dict(rows=rows,overlap=overlap,max_windows=maximum,geometry_profile=profile))
            (folder/'dashboard.json').write_text(json.dumps(value),encoding='utf-8')
            self.jobs[job]=value;self.active=job
        return job,folder/'input.xtf'

    def failed_upload(self,job):
        with self.lock:
            self.jobs[job].update(status='FAILED',error='Upload incomplete or invalid. No analysis was started.')
            (self.root/job/'input.xtf').unlink(missing_ok=True)
            if self.active==job:self.active=None

    def start(self,job,resume=False):
        def work():
            value=self.jobs[job];folder=self.root/job;value['status']='RUNNING'
            try:
                state=self.runner(folder/'input.xtf',folder/'results',device='cpu',cancel_file=folder/'cancel',resume=resume,**value['options'])
                value.update(status=state['status'],windows_completed=state['windows_completed'])
            except Exception as exc:value.update(status='FAILED',error=str(exc)[:500])
            finally:
                with self.lock:
                    if self.active==job:self.active=None
        threading.Thread(target=work,daemon=True).start()

    def status(self,job):
        value=dict(self.jobs[job]);state=self.root/job/'results/job.json'
        if state.exists():
            try:
                progress=json.loads(state.read_text());value['windows_completed']=progress['windows_completed']
            except (OSError,ValueError,KeyError):pass
        value.pop('options',None);return value

    def cancel(self,job):
        if self.active!=job:raise ValueError('Job is not active.')
        (self.root/job/'cancel').touch();return dict(status='CANCELLATION_REQUESTED',detail='Stops between windows; an in-progress CPU analysis may finish.')

    def resume(self,job):
        value=self.jobs[job];options=value['options']
        if set(options)!= {'rows','overlap','max_windows','geometry_profile'}:raise ValueError('Stored job configuration is invalid.')
        rows,overlap,maximum=options['rows'],options['overlap'],options['max_windows']
        if any(type(v) is not int for v in (rows,overlap,maximum)) or not 16<=rows<=512 or not 0<=overlap<rows or not 1<=maximum<=100:raise ValueError('Stored job bounds are invalid.')
        if options['geometry_profile'] is not None:
            from ai.runtime.sonar_geometry import SurveyGeometry
            SurveyGeometry.model_validate(options['geometry_profile'])
        source=self.root/job/'input.xtf'
        if not source.is_file() or not 1024<=source.stat().st_size<=MAX_UPLOAD:raise ValueError('Original upload is missing or incomplete; upload the log again.')
        with self.lock:
            if self.active:raise RuntimeError('Another job is active.')
            if self.jobs[job]['status'] not in ('CANCELLED','FAILED'):raise ValueError('Only cancelled/failed jobs can resume with their original settings.')
            self.active=job;(self.root/job/'cancel').unlink(missing_ok=True)
        self.start(job,resume=True)


def handler(service,port):
    origin=f'http://127.0.0.1:{port}'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass # No uploaded metadata/credentials in access logs.
        def send(self,status,data,kind='application/json'):
            # Drain only small rejected bodies so Windows clients can read the response.
            # Large untrusted uploads are never buffered or drained.
            if self.command=='POST' and not getattr(self,'body_consumed',False):
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if 0<length<=65536:
                        self.connection.settimeout(2);self.rfile.read(length)
                except (ValueError,OSError):pass
                self.body_consumed=True
            body=json.dumps(data).encode() if kind=='application/json' else data
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Cross-Origin-Resource-Policy','same-origin');self.end_headers();self.wfile.write(body)
        def trusted(self,mutation=False):
            if self.headers.get('Host')!=f'127.0.0.1:{port}':self.send(403,{'error':'Use the printed loopback URL.'});return False
            if mutation and (self.headers.get('Origin')!=origin or not secrets.compare_digest(self.headers.get('X-Sonar-Session',''),service.token)):
                self.send(403,{'error':'Same-origin dashboard session required.'});return False
            return True
        def do_GET(self):
            if not self.trusted():return
            path=urlsplit(self.path).path
            if path=='/':
                html=PAGE.replace('__TOKEN__',service.token)
                self.send(200,html.encode(),'text/html; charset=utf-8');return
            if path=='/jobs':self.send(200,{'jobs':[service.status(j) for j in list(service.jobs)]});return
            match=re.fullmatch(r'/results/([a-f0-9]{32})/(index\.html|window-\d{5}\.(?:html|png|json)|report\.(?:csv|json)|contacts\.(?:json|geojson))',path)
            if match and match[1] in service.jobs:
                file=service.root/match[1]/'results'/match[2]
                if file.is_file() and file.stat().st_size<=48*1024**2:
                    kind={'.html':'text/html; charset=utf-8','.png':'image/png','.csv':'text/csv; charset=utf-8'}.get(file.suffix,'application/json')
                    self.send(200,file.read_bytes(),kind);return
            self.send(404,{'error':'Result not available.'})
        def do_POST(self):
            if not self.trusted(True):return
            path=urlsplit(self.path).path
            try:
                if path=='/jobs':
                    if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type')!='application/octet-stream':raise ValueError('Use a bounded binary XTF upload.')
                    raw=self.headers.get('X-Sonar-Options','')
                    if len(raw)>24000:raise ValueError('Job profile exceeds the dashboard limit.')
                    options=json.loads(base64.b64decode(raw,validate=True))
                    if not isinstance(options,dict):raise ValueError('Invalid job configuration.')
                    size=int(self.headers.get('Content-Length','0'));job,file=service.reserve(size,options)
                    try:
                        self.connection.settimeout(30)
                        self.body_consumed=True
                        with file.open('xb') as stream:
                            remaining=size
                            while remaining:
                                chunk=self.rfile.read(min(65536,remaining))
                                if not chunk:raise ValueError('Upload ended early.')
                                stream.write(chunk);remaining-=len(chunk)
                        with file.open('rb') as stream:header=stream.read(1024)
                        if len(header)!=1024 or header[0]!=123:raise ValueError('Invalid XTF header.')
                    except Exception:
                        service.failed_upload(job);raise
                    service.start(job);self.send(202,{'id':job,'status':'RUNNING'});return
                match=re.fullmatch(r'/jobs/([a-f0-9]{32})/(cancel|resume)',path)
                if match and match[1] in service.jobs:
                    if self.headers.get('Content-Length','0')!='0':raise ValueError('Job control has no request body.')
                    if match[2]=='cancel':self.send(200,service.cancel(match[1]))
                    else:service.resume(match[1]);self.send(202,{'status':'RUNNING'})
                    return
                self.send(404,{'error':'Unknown job.'})
            except RuntimeError as exc:self.send(409,{'error':str(exc)[:500]})
            except (ValueError,TypeError,KeyError) as exc:self.send(422,{'error':str(exc)[:500]})
            except Exception:self.send(503,{'error':'Local upload/job failed. Check disk capacity and isolated inference dependencies.'})
    return Handler


PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SONAR-SHIELD local survey workspace</title>
<style>body{font:14px system-ui;background:#08131b;color:#e9f3f6;margin:0}main{max-width:1100px;margin:auto;padding:24px}.panel{background:#0e202a;border:1px solid #2b4551;border-radius:8px;padding:20px;margin:16px 0}h1{font-size:24px}.muted{color:#a6bdc7;line-height:1.65}.tag{color:#e7bb77;font-weight:bold}.fields{display:flex;flex-wrap:wrap;gap:16px}label{display:grid;gap:8px}input,button{background:#142a35;color:#e9f3f6;border:1px solid #456b7b;padding:10px;border-radius:4px;font:inherit}button{cursor:pointer;margin:8px 8px 0 0}button:disabled{opacity:.45}a{color:#66cde2}li{margin:20px 0}#message{white-space:pre-wrap}input[type=number]{width:100px}@media(max-width:600px){main{padding:14px}.fields{display:grid}}</style>
<main><span class="tag">LOCAL CPU INFERENCE · NO HF GPU QUOTA</span><h1>SONAR-SHIELD raw survey workspace</h1><p class="muted">Upload an XTF log to this computer, process a bounded section, then inspect images, evidence, human reviews and reports. Nothing is uploaded to Vercel or Hugging Face. This is local batch processing, not guaranteed real-time inference.</p>
<section class="panel"><div class="fields"><label>Raw XTF log<input id="file" type="file" accept=".xtf"></label><label>Reviewed geometry profile (optional)<input id="profile" type="file" accept=".json"></label></div><p class="muted">Without a verified source-bound profile, results stay pixel-only. No geographic positions or object dimensions are fabricated. Calibration unavailable; raw rendering and field accuracy unverified.</p><div class="fields"><label>Rows per window<input id="rows" type="number" value="128" min="16" max="512"></label><label>Overlapping rows<input id="overlap" type="number" value="16" min="0" max="511"></label><label>Maximum windows<input id="maximum" type="number" value="4" min="1" max="100"></label></div><button id="run">Upload and run local CPU analysis</button><p id="message" role="status"></p></section><section class="panel"><h2>Local survey jobs</h2><p class="muted">One active job. Cancellation is checked between windows. Reports are retained in your private output directory; reopening them runs no inference.</p><ul id="jobs"></ul></section></main>
<script>const session='__TOKEN__',message=document.getElementById('message'),button=document.getElementById('run');let uploading=false;
function optionsHeader(value){return btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(value))))}
async function control(path){try{const r=await fetch(path,{method:'POST',headers:{'X-Sonar-Session':session}}),v=await r.json();if(!r.ok)throw Error(v.error);message.textContent=v.detail||v.status;await refresh()}catch(e){message.textContent=e.message}}
async function refresh(){try{const r=await fetch('/jobs'),v=await r.json();if(!r.ok)throw Error(v.error);const list=document.getElementById('jobs');list.replaceChildren();for(const j of v.jobs){const li=document.createElement('li'),p=document.createElement('p');p.textContent=j.id+' · '+j.status+' · '+j.windows_completed+' windows'+(j.error?' · '+j.error:'');li.append(p);if(j.windows_completed){const a=document.createElement('a');a.href='/results/'+j.id+'/index.html';a.textContent='Open viewer and reports';a.target='_blank';a.rel='noopener';li.append(a)}if(['RUNNING','UPLOADING'].includes(j.status)){const b=document.createElement('button');b.textContent='Cancel';b.onclick=()=>control('/jobs/'+j.id+'/cancel');li.append(b)}if(['CANCELLED','FAILED'].includes(j.status)){const b=document.createElement('button');b.textContent='Resume original job';b.onclick=()=>control('/jobs/'+j.id+'/resume');li.append(b)}list.append(li)}button.disabled=uploading||v.jobs.some(j=>['RUNNING','UPLOADING'].includes(j.status))}catch(e){message.textContent='Local dashboard unavailable: '+e.message}}
button.onclick=async()=>{const file=document.getElementById('file').files[0],profile=document.getElementById('profile').files[0];if(!file||!file.name.toLowerCase().endsWith('.xtf')){message.textContent='Choose a real .xtf log.';return}if(file.size>2147483648){message.textContent='Split logs larger than 2 GiB.';return}uploading=true;button.disabled=true;try{const settings={rows:Number(document.getElementById('rows').value),overlap:Number(document.getElementById('overlap').value),max_windows:Number(document.getElementById('maximum').value)};if(profile){if(profile.size>16000)throw Error('Reviewed profile exceeds 16 KiB.');settings.geometry_profile=JSON.parse(await profile.text())}message.textContent='Uploading to this computer. CPU processing starts only after upload validation.';const r=await fetch('/jobs',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Sonar-Session':session,'X-Sonar-Options':optionsHeader(settings)},body:file}),v=await r.json();if(!r.ok)throw Error(v.error);message.textContent='Local job started. No HF inference call was made.'}catch(e){message.textContent=e.message}finally{uploading=false;await refresh()}};refresh();setInterval(refresh,2000);</script></html>'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--port',type=int,default=8766);args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Use an unprivileged port.')
    service=SurveyService(args.output_dir);server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(service,args.port));server.daemon_threads=True
    print(f'Open http://127.0.0.1:{args.port}/ — CPU only, private local files, no HF quota.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:
        if service.active:(service.root/service.active/'cancel').touch()
    finally:server.server_close()
