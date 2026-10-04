"""Optional local SQLite records. Disabled without database path and reviewer tokens.

Opaque per-reviewer tokens come from server environment, never HF_TOKEN. SQLite
requires durable local storage; do not claim HF/Vercel filesystem persistence.
"""
import hashlib,hmac,json,os,sqlite3,re
from datetime import datetime,timezone,timedelta
from contextlib import contextmanager
from pathlib import Path
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel,ConfigDict,Field,field_validator
from typing import Literal
from ai.api.f8_api_schema import AnalyzeResponse

router=APIRouter(prefix='/records')
def identity(authorization):
    raw=os.environ.get('SONAR_REVIEW_TOKENS_JSON','')
    if not raw or not os.environ.get('SONAR_RECORDS_DB'):raise HTTPException(503,'Shared records are not configured.')
    try: tokens=json.loads(raw)
    except ValueError:raise HTTPException(503,'Shared records configuration is invalid.')
    if not isinstance(tokens,dict):raise HTTPException(503,'Shared records configuration is invalid.')
    if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,'Reviewer authentication required.')
    supplied=hashlib.sha256(authorization[7:].encode()).digest()
    for reviewer,token in tokens.items():
        if not isinstance(reviewer,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',reviewer) or not isinstance(token,str) or len(token)<32:raise HTTPException(503,'Shared records configuration is invalid.')
        if hmac.compare_digest(supplied,hashlib.sha256(token.encode()).digest()):return reviewer
    raise HTTPException(401,'Invalid reviewer credential.')
def storage_owner(reviewer):
    try: teams=json.loads(os.environ.get('SONAR_REVIEW_TEAMS_JSON','{}'))
    except ValueError: raise HTTPException(503,'Team configuration is invalid.')
    if not isinstance(teams,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',v) for k,v in teams.items()): raise HTTPException(503,'Team configuration is invalid.')
    return 'TEAM:'+teams[reviewer] if reviewer in teams else reviewer

@contextmanager
def database():
    path=Path(os.environ['SONAR_RECORDS_DB']);path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=5)
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('CREATE TABLE IF NOT EXISTS analyses(id TEXT PRIMARY KEY, owner TEXT NOT NULL, payload TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS reviews(analysis_id TEXT NOT NULL,candidate_id TEXT NOT NULL,revision INTEGER NOT NULL,reviewer TEXT NOT NULL,status TEXT NOT NULL,note TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(analysis_id,candidate_id,revision),FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE)')
    conn.execute('CREATE TABLE IF NOT EXISTS images(analysis_id TEXT PRIMARY KEY,sha256 TEXT NOT NULL,mime TEXT NOT NULL,content BLOB NOT NULL,FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE)')
    try: days=int(os.environ.get('SONAR_RECORD_RETENTION_DAYS','30'))
    except ValueError: conn.close(); raise HTTPException(503,'Retention configuration is invalid.')
    if not 1<=days<=3650: conn.close(); raise HTTPException(503,'Retention must be 1-3650 days.')
    conn.execute('DELETE FROM analyses WHERE created_at<?',((datetime.now(timezone.utc)-timedelta(days=days)).isoformat(),))
    conn.commit()
    try:
        with conn: yield conn
    finally: conn.close()
def owned(conn,analysis_id,owner):
    row=conn.execute('SELECT payload,source FROM analyses WHERE id=? AND owner=?',(analysis_id,owner)).fetchone()
    if not row:raise HTTPException(404,'Record not found.')
    return json.loads(row[0]),row[1]
class RecordInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    analysis: dict
    @field_validator('analysis')
    @classmethod
    def valid_analysis(cls, value):
        AnalyzeResponse.model_validate(value)
        return value
    source: Literal['LIVE_ANALYSIS','PRECOMPUTED_EXAMPLE']
class ReviewInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    candidate_id: str=Field(min_length=1,max_length=200)
    previous_revision: int=Field(ge=0)
    status: Literal['CONFIRMED','FALSE_POSITIVE','NEEDS_INVESTIGATION']
    note: str=Field(max_length=20000)
@router.post('')
def create_record(record:RecordInput,authorization:str|None=Header(None)):
    owner=storage_owner(identity(authorization));payload=json.dumps(record.analysis,allow_nan=False)
    if len(payload.encode())>2*1024*1024:raise HTTPException(413,'Record exceeds 2 MiB.')
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT COUNT(*) FROM analyses WHERE owner=?',(owner,)).fetchone()[0]>=100:raise HTTPException(429,'Local record quota reached; delete older records.')
        if conn.execute('SELECT COALESCE(SUM(length(payload)),0) FROM analyses').fetchone()[0]+len(payload.encode())>128*1024*1024:raise HTTPException(429,'Shared analysis storage limit reached.')
        try:conn.execute('INSERT INTO analyses VALUES(?,?,?,?,?)',(record.analysis['analysis_id'],owner,payload,record.source,datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError:raise HTTPException(409,'Analysis is immutable or identity already exists.')
    return dict(analysis_id=record.analysis['analysis_id'],storage='LOCAL_SQLITE',origin='CLIENT_IMPORTED_UNATTESTED',source=record.source)
@router.get('/{analysis_id}')
def get_record(analysis_id:str,authorization:str|None=Header(None)):
    reviewer=identity(authorization);owner=storage_owner(reviewer)
    with database() as conn:
        payload,source=owned(conn,analysis_id,owner)
        rows=conn.execute('SELECT candidate_id,revision,reviewer,status,note,created_at FROM reviews WHERE analysis_id=? ORDER BY revision',(analysis_id,)).fetchall()
    return dict(analysis=payload,source=source,origin='CLIENT_IMPORTED_UNATTESTED',review_history=[dict(zip(['candidate_id','revision','reviewer','status','note','created_at'],row)) for row in rows])
@router.post('/{analysis_id}/reviews')
def review(analysis_id:str,value:ReviewInput,authorization:str|None=Header(None)):
    reviewer=identity(authorization);owner=storage_owner(reviewer)
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        payload,_=owned(conn,analysis_id,owner)
        if value.candidate_id not in {c['candidate_id'] for c in payload['candidates']}:raise HTTPException(422,'Candidate does not belong to analysis.')
        current=conn.execute('SELECT COALESCE(MAX(revision),0) FROM reviews WHERE analysis_id=? AND candidate_id=?',(analysis_id,value.candidate_id)).fetchone()[0]
        if current!=value.previous_revision:raise HTTPException(409,'Review changed; reload before saving.')
        if current>=1000 or conn.execute('SELECT COALESCE(SUM(length(note)),0) FROM reviews').fetchone()[0]+len(value.note.encode())>64*1024*1024:raise HTTPException(429,'Review history storage limit reached.')
        revision=current+1
        conn.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?)',(analysis_id,value.candidate_id,revision,reviewer,value.status,value.note,datetime.now(timezone.utc).isoformat()))
    return dict(revision=revision,reviewer=reviewer)
@router.delete('/{analysis_id}')
def delete(analysis_id:str,authorization:str|None=Header(None)):
    reviewer=identity(authorization);owner=storage_owner(reviewer)
    with database() as conn:
        owned(conn,analysis_id,owner)
        conn.execute('DELETE FROM analyses WHERE id=? AND owner=?',(analysis_id,owner))
    return dict(deleted=True)

@router.get('')
def list_records(authorization:str|None=Header(None)):
    reviewer=identity(authorization);owner=storage_owner(reviewer)
    with database() as conn:
        rows=conn.execute('SELECT a.id,a.source,a.created_at,EXISTS(SELECT 1 FROM images i WHERE i.analysis_id=a.id) FROM analyses a WHERE a.owner=? ORDER BY a.created_at DESC LIMIT 100',(owner,)).fetchall()
    return dict(reviewer=reviewer,scope=owner,records=[dict(analysis_id=row[0],source=row[1],created_at=row[2],has_image=bool(row[3])) for row in rows])
