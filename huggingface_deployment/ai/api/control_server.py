"""Lightweight records/admission service. Never imports detector, torch or OpenCV."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from ai.runtime.records import router as records, identity
from ai.runtime.record_images import router as images
from ai.runtime.admission import router as admission, authenticate

app=FastAPI(title='SONAR-SHIELD records and usage control',version='M1-v2')
origins=os.environ.get('SONAR_ALLOWED_ORIGINS','http://127.0.0.1:4182,http://127.0.0.1:5173').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type','Authorization'])

@app.middleware('http')
async def bounded_auth(request,call_next):
    path=request.url.path
    if request.method=='OPTIONS': return await call_next(request)
    if path=='/records' or path.startswith('/records/') or path.startswith('/admission/'):
        try:
            if path.startswith('/admission/'): authenticate(request.headers.get('authorization')); limit=2048
            else: identity(request.headers.get('authorization')); limit=32*1024*1024 if path.endswith('/image') else 2200*1024
        except HTTPException as exc: return JSONResponse(status_code=exc.status_code,content={'detail':exc.detail})
        try: length=int(request.headers.get('content-length','0') or 0)
        except ValueError: return JSONResponse(status_code=400,content={'detail':'Invalid Content-Length.'})
        if length<0: return JSONResponse(status_code=400,content={'detail':'Invalid Content-Length.'})
        if length>limit: return JSONResponse(status_code=413,content={'detail':'Request too large.'})
        # Image endpoint consumes bounded stream directly; JSON must be capped before parser.
        if not path.endswith('/image'):
            body=bytearray()
            async for chunk in request.stream():
                if len(body)+len(chunk)>limit: return JSONResponse(status_code=413,content={'detail':'Request too large.'})
                body.extend(chunk)
            request._body=bytes(body)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    return response

app.include_router(records);app.include_router(images);app.include_router(admission)

@app.get('/health')
def health(): return dict(status='REACHABLE',inference='NOT_HOSTED',records_configured=bool(os.environ.get('SONAR_RECORDS_DB') and os.environ.get('SONAR_REVIEW_TOKENS_JSON')),admission_configured=bool(os.environ.get('SONAR_ADMISSION_DB') and os.environ.get('SONAR_ADMISSION_TOKEN')))
