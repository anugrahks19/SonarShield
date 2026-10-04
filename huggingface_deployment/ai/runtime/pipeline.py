"""M1 shared runtime: no fitting, no fabricated calibration, CPU-safe lazy startup."""
import hashlib
import math
import platform
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import cv2
import joblib
import numpy as np
from ai.schemas.class_map import CLASS_ID_TO_NAME, CLASS_ID_TO_DISPLAY_NAME
from ai.api.f8_api_schema import AnalyzeResponse
from ai.evidence.evidence_extractor import extract_all_evidence

VERSION = 'M1-v1'
MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
ROOT = Path(__file__).resolve().parents[2]

class InputError(ValueError):
    pass

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def decode_image(data):
    if not data or len(data)>MAX_IMAGE_BYTES: raise InputError('Image must be nonempty and at most 32 MiB.')
    # Check dimensions before OpenCV allocates a decompressed image.
    from PIL import Image
    import io
    try:
        with Image.open(io.BytesIO(data)) as header:
            if header.format not in {'JPEG','PNG'}: raise InputError('Use JPEG or PNG.')
            if header.width*header.height>MAX_IMAGE_PIXELS: raise InputError('Image exceeds 16 million pixels.')
            header.verify()
    except InputError: raise
    except Exception as exc: raise InputError('Image cannot be decoded.') from exc
    image=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR)
    if image is None: raise InputError('Image cannot be decoded.')
    return image

def merge_candidates(global_preds, tiled_preds, width, height, iou_threshold=0.7):
    prepared=[]
    for mode, predictions in [('GLOBAL',global_preds),('TILED',tiled_preds)]:
        for pred in predictions:
            b=list(map(float,pred['bbox']))
            score=float(pred['detector_confidence'])
            if len(b)!=4 or not all(math.isfinite(v) for v in b+[score]): raise InputError('Invalid detector output.')
            if not 0<=score<=1 or int(pred['class']) not in CLASS_ID_TO_NAME: raise InputError('Invalid detector class/score.')
            b=[max(0,min(width,b[0])),max(0,min(height,b[1])),max(0,min(width,b[2])),max(0,min(height,b[3]))]
            if b[2]<=b[0] or b[3]<=b[1]: continue
            prepared.append(dict(pred,bbox=b,source_mode=mode))
    prepared.sort(key=lambda p:(-p['detector_confidence'],p['source_mode'],p['class'],p['bbox']))
    kept=[]
    for p in prepared:
        duplicate=False
        a=p['bbox']; area=(a[2]-a[0])*(a[3]-a[1])
        for q in kept:
            if p['class']!=q['class']: continue
            b=q['bbox']; intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
            union=area+(b[2]-b[0])*(b[3]-b[1])-intersection
            other_area=(b[2]-b[0])*(b[3]-b[1])
            contained=intersection/min(area,other_area)>=0.95 and min(area,other_area)/max(area,other_area)>=0.5
            if intersection/union>iou_threshold or contained: duplicate=True; break
        if not duplicate: kept.append(p)
    return kept

def feature_vector(ev, features):
    values={'confidence':ev['confidence'],**ev['object'],**ev['shadow'],
            **ev['seabed'], 'boundary_strength':ev['quality']['boundary_strength'],
            **{k:int(v) for k,v in ev['quality']['artifact_flags'].items()}}
    # Evidence reports object-local intensity alongside background context.
    row=np.array([[values[f] for f in features]],dtype=float)
    if not np.isfinite(row).all(): raise InputError('Evidence contains non-finite values.')
    return row

class AnalysisRuntime:
    def __init__(self, root=ROOT, detector=None, fusion=None, features=None, hashes=None, device='cpu'):
        self.root=Path(root); self.detector=detector; self.fusion=fusion; self.features=features
        self.hashes=hashes or {}; self.device=device; self.lock=threading.Lock(); self.admission=threading.BoundedSemaphore(1)
    def initialize(self):
        if self.detector is not None: return
        with self.lock:
            if self.detector is not None: return
            detector_path=self.root/'models/v6/detector_v6_p2_sss/weights/best.pt'
            fusion_path=self.root/'ai/fusion/weights/gate_d_fusion_model.pkl'
            for path in [detector_path,fusion_path]:
                if not path.is_file(): raise FileNotFoundError(f'Required inference artifact missing: {path}')
            from ai.detection.tiled_detector import TiledDetector
            detector=TiledDetector(str(detector_path),conf=0.15,iou=0.7,device=self.device)
            actual={int(k):v for k,v in detector.model.names.items()}
            if actual!=CLASS_ID_TO_NAME: raise RuntimeError('Checkpoint class map disagrees with canonical map.')
            data=joblib.load(fusion_path) # Trusted local artifact only; never accept user pickle.
            if not {'pipeline','features'}.issubset(data): raise RuntimeError('Incomplete fusion artifact.')
            self.fusion=data['pipeline']; self.features=data['features']
            self.hashes={'detector':sha256_file(detector_path),'fusion':sha256_file(fusion_path)}
            self.detector=detector
    def analyze(self,data,filename,tiled=True,metadata=None):
        if not self.admission.acquire(blocking=False): raise RuntimeError('SERVICE_BUSY: one analysis is already running.')
        try: return self._analyze(data,filename,tiled,metadata)
        finally: self.admission.release()
    def _analyze(self,data,filename,tiled=True,metadata=None):
        start=time.perf_counter(); image=decode_image(data)
        height,width=image.shape[:2]
        if metadata is not None:
            from ai.runtime.localization import validate_metadata
            metadata=validate_metadata(metadata,data,width,height)
        self.initialize()
        # Serialize access to mutable predictor state; deployment limits handled separately.
        with self.lock:
            gp=self.detector.predict(image,trigger_conf=-1,pure_tiled=False)
            tp=self.detector.predict(image,pure_tiled=True) if tiled else []
        raw=merge_candidates(gp,tp,width,height)
        image_hash=hashlib.sha256(data).hexdigest(); input_id='IMG-'+uuid.uuid4().hex
        candidates=[]
        from ai.runtime.localization import localize
        # Existing class-specific policy/calibration artifacts have no compatible identity manifest.
        # Do not reuse wrong-ID thresholds or pretend correcting labels validates learned decisions.
        for pred in raw:
            ev=extract_all_evidence(image,pred)
            score=float(self.fusion.predict_proba(feature_vector(ev,self.features))[0][1])
            if not math.isfinite(score) or not 0<=score<=1: raise InputError('Fusion returned an invalid score.')
            cid='CAND-'+uuid.uuid4().hex; class_name=CLASS_ID_TO_DISPLAY_NAME[pred['class']]
            coords=localize(pred['bbox'],width,height,metadata)
            flags=[{'code':k.upper(),'severity':'WARNING'} for k,v in ev['quality']['artifact_flags'].items() if v]
            shadow=dict(ev['shadow']); shadow.pop('shadow_bbox',None)
            shadow['shadow_area_px']=shadow['area_ratio']*ev['object']['bbox_area_px']
            candidates.append({
                'schema_version':'F7.1','candidate_id':cid,
                'detection':dict(class_id=pred['class'],class_name=class_name,confidence=pred['detector_confidence'],bbox=pred['bbox'],source_mode=pred['source_mode']),
                'classification':dict(class_id=pred['class'],class_name=class_name,reliability=None,presentation=dict(reliability_band='UNCALIBRATED',uncertainty_level='UNKNOWN')),
                'decision':dict(status='REVIEW',fusion_score=score,reason_codes=['POLICY_COMPATIBILITY_UNVERIFIED','UNCALIBRATED_CLASS_FORCED_REVIEW']),
                'evidence':dict(ai_confidence=ev['confidence'],bbox=ev['bbox'],geometry=ev['object'],seabed=dict(background_mean=ev['seabed']['mean_intensity'],background_std=ev['seabed']['std_intensity'],local_contrast=ev['seabed']['local_contrast']),shadow=shadow,quality=dict(boundary_strength=ev['quality']['boundary_strength'],artifact_flags=ev['quality']['artifact_flags'])),
                'localization':coords,
                'localization_uncertainty':dict(validation_reference=None,error_envelope=dict(status='NOT_ESTIMABLE',scope='UNAVAILABLE',method='NONE',reason='No compatible validated error calibration.')),
                'quality':dict(image=dict(flags=[dict(code='ACQUISITION_QUALITY_NOT_ASSESSED',severity='INFO')]),detection=dict(flags=[]),evidence=dict(completeness=dict(available=['geometry','seabed','shadow','artifact_flags'],missing=[]),flags=flags),localization=dict(flags=[dict(code='FIELD_LOCALIZATION_UNVERIFIED' if coords['metadata']['status']=='GEOGRAPHIC' else 'PIXEL_ONLY',severity='INFO')]),metadata=dict(flags=[] if metadata else [dict(code='NAV_METADATA_UNAVAILABLE',severity='INFO')])),
                'provenance':dict(candidate_id=cid,input_id=input_id,source_dataset='USER_UPLOAD',image_sha256=image_hash,pipeline_version=VERSION,detector_version='V6-P2',fusion_version='D2-v1',decision_policy_version='UNVERIFIED_REVIEW_ONLY',calibration_version='UNAVAILABLE',preprocessing_version='NONE',coordinate_contract_version='M1-ground-raster-v1',detector_artifact_sha256=self.hashes['detector'],fusion_artifact_sha256=self.hashes['fusion'],processing_timestamp=datetime.now(timezone.utc).isoformat(),runtime_version=platform.python_version())
            })
        response=dict(schema_version='F8.1',analysis_id='ANL-'+uuid.uuid4().hex,status='COMPLETED',input=dict(input_id=input_id,filename=Path(filename).name,sha256=image_hash,width=width,height=height),summary=dict(candidate_count=len(candidates),confirmed_count=0,review_count=len(candidates),rejected_count=0,unknown_count=0),candidates=candidates,artifacts={},processing=dict(status='COMPLETED',pipeline_version=VERSION,processing_time_ms=round((time.perf_counter()-start)*1000)))
        return AnalyzeResponse.model_validate(response)
