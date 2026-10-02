"""Persistent global gateway admission. Requires a durable SQLite controller host."""
import hashlib, hmac, os, sqlite3, time, uuid
from pathlib import Path
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix='/admission')

def configured_int(name, default, low, high):
    try: value = int(os.environ.get(name, default))
    except ValueError: raise HTTPException(503, 'Admission configuration is invalid.')
    if not low <= value <= high: raise HTTPException(503, 'Admission configuration is invalid.')
    return value

def authenticate(authorization):
    token = os.environ.get('SONAR_ADMISSION_TOKEN', '')
    if len(token) < 32 or not os.environ.get('SONAR_ADMISSION_DB'):
        raise HTTPException(503, 'Admission controller is not configured.')
    supplied = authorization[7:] if authorization and authorization.startswith('Bearer ') else ''
    if not hmac.compare_digest(hashlib.sha256(token.encode()).digest(), hashlib.sha256(supplied.encode()).digest()):
        raise HTTPException(401, 'Admission authentication required.')

class Lease(BaseModel):
    model_config = ConfigDict(extra='forbid')
    lease_id: str = Field(pattern=r'^[a-f0-9]{32}$')

@router.post('/acquire')
def acquire(authorization: str | None = Header(None)):
    authenticate(authorization)
    daily = configured_int('SONAR_DAILY_RUN_LIMIT', 20, 1, 10000)
    concurrent = configured_int('SONAR_CONCURRENT_RUN_LIMIT', 1, 1, 16)
    duration = configured_int('SONAR_LEASE_SECONDS', 600, 360, 3600)
    now = time.time(); day = int(now // 86400)
    path = Path(os.environ['SONAR_ADMISSION_DB']); path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS leases(id TEXT PRIMARY KEY, expires REAL NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS usage(day INTEGER PRIMARY KEY, runs INTEGER NOT NULL)')
        conn.commit(); conn.execute('BEGIN IMMEDIATE')
        conn.execute('DELETE FROM leases WHERE expires<=?', (now,))
        conn.execute('DELETE FROM usage WHERE day<?', (day-7,))
        used = conn.execute('SELECT runs FROM usage WHERE day=?', (day,)).fetchone()
        if used and used[0] >= daily:
            raise HTTPException(429, 'The configured daily live-run budget is reached. This is a site budget, not the HF reset time.')
        if conn.execute('SELECT COUNT(*) FROM leases').fetchone()[0] >= concurrent:
            raise HTTPException(429, 'Another live analysis is active or awaiting its safety lease expiry. Try manually later.')
        key = uuid.uuid4().hex
        conn.execute('INSERT INTO leases VALUES(?,?)', (key, now+duration))
        conn.execute('INSERT INTO usage VALUES(?,1) ON CONFLICT(day) DO UPDATE SET runs=runs+1', (day,))
        conn.commit()
        return dict(lease_id=key, expires_at=now+duration, budget_remaining=daily-(used[0] if used else 0)-1)
    finally: conn.close()

@router.post('/release')
def release(value: Lease, authorization: str | None = Header(None)):
    authenticate(authorization)
    conn = sqlite3.connect(os.environ['SONAR_ADMISSION_DB'], timeout=5)
    try:
        conn.execute('DELETE FROM leases WHERE id=?', (value.lease_id,)); conn.commit()
    finally: conn.close()
    return dict(released=True)
