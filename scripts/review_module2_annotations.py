"""Local, append-only annotation proposals. Never modifies source or trains a model."""
import argparse, hashlib, io, json, math, secrets, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def prepare(audit, output):
    output = Path(output)
    if output.exists(): raise ValueError('Use a new review directory; existing decisions are preserved.')
    inventory = read(Path(audit)/'inventory.json')
    native = {'crab_pot','AI4Shipwrecks','China-Offshore-SSS-AI','MILCONOMBO Side-Scan Sonar Mine Dataset','SSS_UXO'}
    items = []; native_metadata_hashes = {}
    for r in inventory:
        if r['dataset'] not in native: continue
        if r['label_type']=='NATIVE_JSONL':
            metadata=Path(r['image']).parent/'metadata.jsonl'
            if metadata.exists():
                r['native_metadata_file']=str(metadata)
                if str(metadata) not in native_metadata_hashes: native_metadata_hashes[str(metadata)]=digest(metadata)
                r['native_metadata_sha256']=native_metadata_hashes[str(metadata)]
        # Primary sonar rasters only: reference illustrations and derived audit plots excluded.
        reasons = list(r.get('annotation_errors', []))
        if r['dataset']=='AI4Shipwrecks': reasons.append('MASK_SEMANTICS_AND_INSTANCE_REVIEW')
        if r.get('empty_label_not_confirmed_background'): reasons.append('UNCONFIRMED_BACKGROUND')
        if not reasons: reasons.append('SOURCE_SEMANTICS_GROUP_AND_RIGHTS_REVIEW')
        priority = 0 if any('OUTSIDE' in x or 'INVALID' in x for x in reasons) else 1 if r['dataset']=='AI4Shipwrecks' else 2 if 'UNCONFIRMED_BACKGROUND' in reasons else 3
        items.append(dict(kind='IMAGE', priority=priority, reasons=reasons, sources=[r], proposal_status='UNREVIEWED'))
    by_path={r['image']:r for r in inventory}
    for pair in read(Path(audit)/'priority-near-review.json'):
        if pair['a'] in by_path and pair['b'] in by_path:
            items.append(dict(kind='SIMILARITY',priority=2,reasons=['PROTECTED_ROLE_SIMILARITY_NOT_PROVEN_DUPLICATE'],sources=[by_path[pair['a']],by_path[pair['b']]],distance=pair['hamming_distance'],proposal_status='UNREVIEWED'))
    for group in read(Path(audit)/'current-train-native-test-overlaps.json'):
        sources=[by_path[p] for p in group['images'] if p in by_path]
        items.append(dict(kind='KNOWN_TRAIN_TEST_OVERLAP',priority=1,reasons=['INELIGIBLE_AS_FRESH_HOLDOUT'],sources=sources,proposal_status='UNREVIEWED'))
    items.sort(key=lambda x:(x['priority'],x['sources'][0]['image']))
    for n,item in enumerate(items): item['id']=str(n)
    output.mkdir(parents=True)
    (output/'queue.json').write_text(json.dumps(items,ensure_ascii=False),encoding='utf-8')
    summary={'items':len(items),'kinds':{k:sum(i['kind']==k for i in items) for k in sorted({i['kind'] for i in items})},'status':'REVIEW_WORKSPACE_READY_NOT_APPROVED','training_started':False,'original_annotations_changed':False}
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary))
    return summary

def validate(item, value):
    if value.get('status') not in ('PROPOSE_CORRECTION','CONFIRM_EXISTING','CONFIRM_BACKGROUND','EXCLUDE','UNCERTAIN','SAME_ACQUISITION','DISTINCT_ACQUISITION'): raise ValueError('Invalid decision.')
    for field in ('reviewer','reason'):
        if not isinstance(value.get(field),str) or not 1<=len(value[field].strip())<=2000: raise ValueError('Reviewer and reason required.')
    boxes=value.get('boxes',[])
    if not isinstance(boxes,list) or len(boxes)>2000: raise ValueError('Invalid boxes.')
    width,height=item['sources'][0].get('width'),item['sources'][0].get('height')
    if value['status']=='CONFIRM_BACKGROUND' and boxes: raise ValueError('Background cannot have boxes.')
    if value['status']=='PROPOSE_CORRECTION' and not boxes: raise ValueError('Correction needs boxes; use UNCERTAIN or EXCLUDE otherwise.')
    for b in boxes:
        if not isinstance(b,dict) or not isinstance(b.get('category'),str) or not b['category'].strip() or len(b['category'])>100: raise ValueError('Named source category required.')
        coords=[b.get(k) for k in ('x','y','w','h')]
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in coords): raise ValueError('Finite pixel boxes required.')
        x,y,w,h=coords
        if width is None or height is None or x<0 or y<0 or w<=0 or h<=0 or x+w>width or y+h>height: raise ValueError('Box outside original image.')
    for field in ('acquisition_group','rights_evidence','semantic_note'):
        if not isinstance(value.get(field,''),str) or len(value.get(field,''))>4000: raise ValueError('Invalid metadata.')
    # A submitted review is a proposal; independent approval belongs to the dataset build gate.
    return {k:value.get(k,[] if k=='boxes' else '') for k in ('status','reviewer','reason','boxes','acquisition_group','rights_evidence','semantic_note')}

@contextmanager
def connect(output):
    db=sqlite3.connect(Path(output)/'decisions.sqlite3')
    try:
        with db:
            db.execute('create table if not exists decisions (sequence integer primary key, item_id text, received_at text, payload text)')
            yield db
    finally: db.close()

def record(output,item,value):
    result=validate(item,value)
    for source in item['sources']:
        if digest(source['image'])!=source['sha256']: raise ValueError('Source image changed since audit; re-audit first.')
        if source.get('label_sha256') and digest(source['label'])!=source['label_sha256']: raise ValueError('Source annotation changed since audit; re-audit first.')
        if source.get('native_metadata_sha256') and digest(source['native_metadata_file'])!=source['native_metadata_sha256']: raise ValueError('Native metadata changed since preparation; re-audit first.')
    result.update(item_id=item['id'],source_hashes=[s['sha256'] for s in item['sources']],source_label_hashes=[s.get('label_sha256') for s in item['sources']],approval='PROPOSAL_NOT_DATASET_APPROVAL')
    with connect(output) as db:
        db.execute('insert into decisions(item_id,received_at,payload) values(?,?,?)',(item['id'],datetime.now(timezone.utc).isoformat(),json.dumps(result,allow_nan=False)))
    return result

def serve(output,port):
    items=read(Path(output)/'queue.json'); token=secrets.token_urlsafe(24)
    origin=f'http://127.0.0.1:{port}'
    html=Path(__file__).with_name('module2_annotation_review.html').read_text(encoding='utf-8').replace('__TOKEN__',token)
    class Handler(BaseHTTPRequestHandler):
        def respond(self,status,data,mime='application/json'):
            if not isinstance(data,bytes): data=json.dumps(data,allow_nan=False).encode() if mime=='application/json' else data.encode('utf-8')
            self.send_response(status);self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.headers.get('Host')!=f'127.0.0.1:{port}': return self.respond(403,{'error':'Local host only'})
            path=urlparse(self.path); query=parse_qs(path.query)
            try:
                if path.path=='/': return self.respond(200,html,'text/html')
                if path.path=='/queue': return self.respond(200,[{'id':i['id'],'kind':i['kind'],'priority':i['priority'],'name':Path(i['sources'][0]['image']).name,'dataset':i['sources'][0]['dataset'],'reasons':i['reasons']} for i in items])
                if path.path=='/export':
                    with connect(output) as db: rows=[{'sequence':r[0],'received_at':r[1],**json.loads(r[2])} for r in db.execute('select sequence,received_at,payload from decisions order by sequence')]
                    return self.respond(200,{'approval':'PROPOSALS_ONLY','decisions':rows})
                item=items[int(query['id'][0])]
                if path.path=='/item':
                    with connect(output) as db: row=db.execute('select payload from decisions where item_id=? order by sequence desc limit 1',(item['id'],)).fetchone()
                    return self.respond(200,{'item':item,'decision':json.loads(row[0]) if row else None})
                if path.path=='/image':
                    from PIL import Image
                    s=item['sources'][int(query.get('side',['0'])[0])]
                    file=s['label'] if query.get('mask',['0'])[0]=='1' and s['label_type']=='PIXEL_MASK_REVIEW_REQUIRED' else s['image']
                    with Image.open(file) as im:
                        im=im.convert('RGB'); im.thumbnail((1800,1800)); data=io.BytesIO();im.save(data,format='PNG')
                    return self.respond(200,data.getvalue(),'image/png')
                return self.respond(404,{'error':'Unknown route'})
            except (ValueError,KeyError,IndexError,OSError) as e: self.respond(400,{'error':str(e)[:300]})
        def do_POST(self):
            if self.headers.get('Host')!=f'127.0.0.1:{port}' or self.headers.get('Origin')!=origin or self.headers.get('X-Review-Token')!=token: return self.respond(403,{'error':'Local authenticated browser request required'})
            try:
                if self.path!='/decision': return self.respond(404,{'error':'Unknown route'})
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=262144: raise ValueError('Invalid request size')
                value=json.loads(self.rfile.read(size)); item=items[int(value['id'])]
                return self.respond(200,record(output,item,value))
            except (ValueError,KeyError,IndexError,OSError) as e: self.respond(400,{'error':str(e)[:300]})
    print(f'Review workspace: {origin}/ (proposals only; no inference)',flush=True)
    HTTPServer(('127.0.0.1',port),Handler).serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--serve',action='store_true');p.add_argument('--port',type=int,default=8771);a=p.parse_args()
    if a.serve: serve(a.output,a.port)
    elif a.audit: prepare(a.audit,a.output)
    else: p.error('--audit required for preparation, or --serve for existing workspace')
