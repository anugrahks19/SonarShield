"""Authenticated paired image storage, in the same durable SQLite backup as records."""
import hashlib, io
from fastapi import APIRouter, Header, HTTPException, Request, Response
from PIL import Image
from ai.runtime.records import database, identity, owned, storage_owner

router=APIRouter(prefix='/records')
MAX_BYTES=32*1024*1024

@router.post('/{analysis_id}/image')
async def put_image(analysis_id: str, request: Request, authorization: str | None=Header(None)):
    owner=storage_owner(identity(authorization))
    chunks=bytearray()
    async for chunk in request.stream():
        if len(chunks)+len(chunk)>MAX_BYTES: raise HTTPException(413, 'Image exceeds 32 MiB.')
        chunks.extend(chunk)
    data=bytes(chunks)
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in {'JPEG','PNG'} or image.width*image.height>16_000_000: raise ValueError()
            mime='image/jpeg' if image.format=='JPEG' else 'image/png'
            width,height=image.size; image.verify()
    except Exception: raise HTTPException(422, 'Use a decodable JPEG/PNG within 16 million pixels.')
    digest=hashlib.sha256(data).hexdigest()
    with database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        analysis,source=owned(conn,analysis_id,owner)
        if source=='PRECOMPUTED_EXAMPLE' or analysis['schema_version']=='F8.1':
            if digest!=analysis['input']['sha256']: raise HTTPException(422, 'Image hash does not match analysis.')
        if [analysis['input']['width'],analysis['input']['height']]!=[width,height]: raise HTTPException(422, 'Image dimensions do not match analysis.')
        existing=conn.execute('SELECT sha256 FROM images WHERE analysis_id=?',(analysis_id,)).fetchone()
        if existing:
            if existing[0]!=digest: raise HTTPException(409, 'Paired image is immutable.')
            return dict(image_sha256=digest,stored=True)
        usage=conn.execute('SELECT COALESCE(SUM(length(content)),0) FROM images').fetchone()[0]
        if usage+len(data)>256*1024*1024: raise HTTPException(429,'Shared image storage limit reached; delete expired records.')
        conn.execute('INSERT INTO images VALUES(?,?,?,?)',(analysis_id,digest,mime,data))
    return dict(image_sha256=digest,stored=True)

@router.get('/{analysis_id}/image')
def get_image(analysis_id: str, authorization: str | None=Header(None)):
    owner=storage_owner(identity(authorization))
    with database() as conn:
        owned(conn,analysis_id,owner)
        row=conn.execute('SELECT mime,content FROM images WHERE analysis_id=?',(analysis_id,)).fetchone()
        if not row: raise HTTPException(404, 'Paired image has not been stored.')
    return Response(content=row[1],media_type=row[0],headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
