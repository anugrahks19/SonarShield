"""Recorded deterministic log/percentile conversion; not learned enhancement."""
import numpy as np


def scale_samples(raw):
    data=np.asarray(raw,dtype=np.float64)
    if data.ndim!=2 or not data.size or data.size>16_000_000 or not np.isfinite(data).all() or np.any(data<0):
        raise ValueError('Invalid bounded sonar amplitude raster.')
    transformed=np.log1p(data)
    low,high=np.percentile(transformed,[1,99.5])
    if high<=low:
        gray=np.zeros(data.shape,dtype=np.uint8) if np.max(data)==0 else np.full(data.shape,128,dtype=np.uint8)
    else:gray=np.rint(np.clip((transformed-low)/(high-low),0,1)*255).astype(np.uint8)
    gray[data==0]=0
    metadata=dict(version='LOG1P_PERCENTILE_V1',transform='LOG1P',percentiles=[1,99.5],log_low=float(low),log_high=float(high),raw_min=float(np.min(data)),raw_max=float(np.max(data)),raw_median=float(np.median(data)),output_zero_fraction=float(np.mean(gray==0)),detector_validation='UNVALIDATED_RENDERING_DOMAIN',zero_samples_preserved=True)
    return gray,metadata
