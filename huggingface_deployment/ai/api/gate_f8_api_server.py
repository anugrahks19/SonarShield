"""Local API for shared runtime. Import is safe without inference artifacts."""
import json
import os
import time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ai.runtime.pipeline import AnalysisRuntime, InputError, MAX_IMAGE_BYTES, VERSION
from ai.api.f8_api_schema import AnalyzeResponse

app=FastAPI(title='SONAR-SHIELD',version='F8.1')
origins=os.environ.get('SONAR_ALLOWED_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type','Authorization'])
from ai.runtime.records import router as records_router, identity as record_identity
from fastapi.responses import JSONResponse

@app.middleware('http')
async def protect_records(request, call_next):
    if request.method != 'OPTIONS' and (request.url.path == '/records' or request.url.path.startswith('/records/')):
        try: record_identity(request.headers.get('authorization'))
        except HTTPException as exc: return JSONResponse(status_code=exc.status_code,content={'detail':exc.detail})
        # Authenticate before parsing; enforce the body cap even without Content-Length.
        body=bytearray()
        async for chunk in request.stream():
            if len(body)+len(chunk)>2200*1024: return JSONResponse(status_code=413,content={'detail':'Record request too large.'})
            body.extend(chunk)
        request._body=bytes(body)  # Starlette cached-request replay for downstream JSON parsing.
    return await call_next(request)

app.include_router(records_router)
runtime=AnalysisRuntime(device=os.environ.get('SONAR_DEVICE','cpu'))
started=time.monotonic()

@app.get('/health')
def health():
    ready=runtime.detector is not None
    return dict(status='OK' if ready else 'NOT_INITIALIZED',schema_version='F8.1',pipeline_version=VERSION,uptime_seconds=int(time.monotonic()-started),components=dict(detector='READY' if ready else 'NOT_INITIALIZED',fusion='READY' if ready else 'NOT_INITIALIZED',decision_policy='UNVERIFIED_REVIEW_ONLY',calibration='UNAVAILABLE',unknown_detector='UNVERIFIED'))

@app.post('/analyze',response_model=AnalyzeResponse)
def analyze(file:UploadFile=File(...),run_tiled_auxiliary:bool=Form(True),return_visual_audit:bool=Form(False),metadata_json:str=Form('')):
    data=file.file.read(MAX_IMAGE_BYTES+1)
    try:
        if len(metadata_json.encode())>256*1024: raise InputError('Metadata exceeds 256 KiB.')
        metadata=json.loads(metadata_json) if metadata_json else None
        return runtime.analyze(data,file.filename or 'upload',run_tiled_auxiliary,metadata)
    except (ValueError,InputError) as exc:
        raise HTTPException(422,detail=dict(code='INVALID_INPUT',message=str(exc))) from exc
    except (FileNotFoundError,RuntimeError) as exc:
        raise HTTPException(503,detail=dict(code='ARTIFACT_UNAVAILABLE',message=str(exc))) from exc

@app.post('/detect')
def detect():
    raise HTTPException(410,detail=dict(code='ENDPOINT_DEPRECATED',message='Use /analyze; the old /detect response was a stub.'))

@app.post('/report')
def report():
    raise HTTPException(501,detail=dict(code='REPORT_ARTIFACT_UNAVAILABLE',message='Use frontend JSON/CSV/print exports. No server artifact was generated.'))
