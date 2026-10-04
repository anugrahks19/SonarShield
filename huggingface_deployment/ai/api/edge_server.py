"""Authenticated, bounded offline image API. No vehicle-control interface."""
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from ai.runtime.pipeline import AnalysisRuntime, InputError, MAX_IMAGE_BYTES


def create_app(runtime=None, device_tokens=None):
    app = FastAPI(title='SONAR-SHIELD edge image adapter', version='1.0')
    engine = runtime or AnalysisRuntime(device=os.environ.get('SONAR_DEVICE', 'cpu'))
    tokens = device_tokens if device_tokens is not None else json.loads(os.environ.get('SONAR_EDGE_TOKENS_JSON', '{}'))
    if not isinstance(tokens, dict) or any(not isinstance(k,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', k) or not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,256}',v) for k, v in tokens.items()):
        raise ValueError('Configure device IDs and unique tokens of at least 32 characters.')
    if len(set(tokens.values())) != len(tokens):
        raise ValueError('Each device needs a unique token.')

    @app.middleware('http')
    async def protect(request, call_next):
        # No endpoint accepts unauthenticated image bytes; never logs a token.
        supplied = request.headers.get('authorization', '')
        token = supplied[7:] if supplied.startswith('Bearer ') and len(supplied) <= 512 else ''
        identity = next((device for device, secret in tokens.items() if hmac.compare_digest(token.encode('utf-8'), secret.encode('ascii'))), None)
        if identity is None:
            return JSONResponse(status_code=401, content={'detail': 'Valid device authentication required.'})
        request.state.device_id = identity
        if request.url.path == '/v1/edge/analyze' and request.method == 'POST':
            content_type = request.headers.get('content-type', '').split(';')[0]
            if content_type not in {'image/jpeg', 'image/png'}:
                return JSONResponse(status_code=415, content={'detail': 'Send raw JPEG or PNG bytes, not an XTF log.'})
            try:
                length = int(request.headers.get('content-length', '0'))
            except ValueError:
                return JSONResponse(status_code=400, content={'detail': 'Invalid Content-Length.'})
            if length < 0 or length > MAX_IMAGE_BYTES:
                return JSONResponse(status_code=413, content={'detail': 'Image exceeds 32 MiB.'})
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_IMAGE_BYTES:
                    return JSONResponse(status_code=413, content={'detail': 'Image exceeds 32 MiB.'})
                body.extend(chunk)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/v1/edge/capabilities')
    def capabilities():
        return {'version': 1, 'inputs': ['image/jpeg', 'image/png'], 'max_bytes': MAX_IMAGE_BYTES,
                'max_pixels': 16_000_000, 'runtime': 'LOCAL_OFFLINE', 'concurrent_inference': 1,
                'calibration': 'UNAVAILABLE_REVIEW_ONLY', 'vehicle_control': False,
                'raw_xtf': 'USE_LOCAL_SURVEY_ADAPTER', 'target_hardware_verified': False}

    @app.post('/v1/edge/analyze')
    async def analyze(request: Request):
        request_id = request.headers.get('x-request-id', '')
        if request_id and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', request_id):
            raise HTTPException(422, 'Invalid request ID.')
        data = await request.body()
        try:
            result = await run_in_threadpool(engine.analyze, data, 'edge-upload', True)
            analysis = result.model_dump(mode='json')
        except (InputError, ValueError) as exc:
            raise HTTPException(422, 'Invalid image input.') from exc
        except RuntimeError as exc:
            code = 'SERVICE_BUSY' if str(exc).startswith('SERVICE_BUSY') else 'RUNTIME_UNAVAILABLE'
            raise HTTPException(503, {'code': code, 'retry': 'MANUAL_ONLY'}) from exc
        except FileNotFoundError as exc:
            raise HTTPException(503, {'code': 'ARTIFACT_UNAVAILABLE'}) from exc
        return {'adapter_version': 1, 'source': 'LOCAL_EDGE_INFERENCE',
                'device_id': request.state.device_id, 'request_id': request_id or None,
                'received_at': datetime.now(timezone.utc).isoformat(),
                'input_sha256': hashlib.sha256(data).hexdigest(), 'analysis': analysis,
                'limitations': ['NOT_CALIBRATED_ACCURACY', 'NOT_VEHICLE_CONTROL', 'NO_NAVIGATION_SUPPLIED']}
    return app


app = create_app()
