"""Explicit ground-range raster sidecar. Not a raw/slant-range sonar converter."""
import math
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ai.api.coordinate_schema import CoordinatesPayload, ImageCoordinates, NormalizedImageCoordinates, PixelConvention

class NavigationRow(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    row: float=Field(ge=0)
    latitude: float=Field(ge=-90,le=90)
    longitude: float=Field(ge=-180,le=180)
    heading_deg: float=Field(ge=0,lt=360)
    timestamp: str

class RasterMetadata(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    version: Literal['ground-range-raster-v1']
    image_sha256: str=Field(pattern=r'^[a-f0-9]{64}$')
    width: int=Field(gt=0,le=100000)
    height: int=Field(gt=0,le=100000)
    geometry: Literal['GROUND_RANGE_CORRECTED']
    navigation_source: str=Field(min_length=1,max_length=500)
    # Positions refer to the SENSOR, not vessel GPS without lever-arm correction.
    position_reference: Literal['SENSOR_WGS84']
    across_track_m_per_pixel: float=Field(gt=0,le=100)
    along_track_m_per_pixel: float=Field(gt=0,le=100)
    nadir_x_px: float=Field(ge=0)
    navigation: list[NavigationRow]=Field(min_length=2,max_length=100000)
    @model_validator(mode='after')
    def ordered(self):
        from datetime import datetime
        if self.nadir_x_px>self.width: raise ValueError('Nadir outside image.')
        rows=[p.row for p in self.navigation]
        if rows[0]!=0 or rows[-1]!=self.height: raise ValueError('Navigation must cover full raster boundaries.')
        if any(a>=b for a,b in zip(rows,rows[1:])): raise ValueError('Navigation rows must increase.')
        times=[datetime.fromisoformat(p.timestamp.replace('Z','+00:00')) for p in self.navigation]
        if any(t.tzinfo is None for t in times) or any(a>=b for a,b in zip(times,times[1:])): raise ValueError('Navigation timestamps must increase and have timezone.')
        if any((b-a).total_seconds()>10 for a,b in zip(times,times[1:])): raise ValueError('Navigation gap exceeds 10 seconds.')
        if any(abs(b.longitude-a.longitude)>180 for a,b in zip(self.navigation,self.navigation[1:])): raise ValueError('Dateline crossing unsupported in this adapter.')
        return self

def validate_metadata(metadata,data,width,height):
    import hashlib
    m=RasterMetadata.model_validate(metadata)
    if m.width!=width or m.height!=height or m.image_sha256!=hashlib.sha256(data).hexdigest(): raise ValueError('Metadata does not match analyzed image.')
    return m

def localize(box,width,height,metadata=None):
    x1,y1,x2,y2=box; cx=(x1+x2)/2; cy=(y1+y2)/2
    image=ImageCoordinates(x_min=x1,y_min=y1,x_max=x2,y_max=y2,center_x=cx,center_y=cy,width_px=x2-x1,height_px=y2-y1)
    coordinates=CoordinatesPayload(image=image,normalized_image=NormalizedImageCoordinates(center_x=cx/width,center_y=cy/height,width_norm=(x2-x1)/width,height_norm=(y2-y1)/height)).model_dump()
    status='PIXEL_ONLY'; reason='NO_SONAR_NAV_METADATA'; provenance=[]; physical=None
    if metadata is not None:
        m=metadata if isinstance(metadata,RasterMetadata) else RasterMetadata.model_validate(metadata)
        for a,b in zip(m.navigation,m.navigation[1:]):
            if a.row<=cy<=b.row: break
        t=(cy-a.row)/(b.row-a.row)
        lat=a.latitude+t*(b.latitude-a.latitude); lon=a.longitude+t*(b.longitude-a.longitude)
        heading=(a.heading_deg+t*((b.heading_deg-a.heading_deg+180)%360-180))%360
        across=(cx-m.nadir_x_px)*m.across_track_m_per_pixel
        # Local tangent approximation restricted to short ranges; not a geodetic survey guarantee.
        if abs(lat)>80 or abs(across)>1000: raise ValueError('Local tangent conversion outside supported range.')
        rad=math.radians(heading)
        north=-across*math.sin(rad); east=across*math.cos(rad)
        coordinates['geographic']=dict(coordinate_system='WGS84',latitude=lat+math.degrees(north/6378137),longitude=lon+math.degrees(east/(6378137*math.cos(math.radians(lat)))),heading_deg=heading)
        coordinates['sonar']=dict(coordinate_system='SONAR_RELATIVE',range_m=abs(across),across_track_m=across,along_track_m=cy*m.along_track_m_per_pixel)
        physical=dict(width_m=(x2-x1)*m.across_track_m_per_pixel,height_m=(y2-y1)*m.along_track_m_per_pixel,method='GROUND_RANGE_RASTER_EXTENTS',status='ESTIMATED_NOT_FIELD_VALIDATED')
        status='GEOGRAPHIC'; reason='GROUND_RANGE_METADATA_LOCAL_TANGENT_ESTIMATE'
        provenance=[dict(source_space='IMAGE_PIXEL',target_space='WGS84',transform='GROUND_RANGE_RASTER_LOCAL_TANGENT',geometry_version='1.0',source_dimensions=[width,height],target_dimensions=None)]
    return dict(metadata=dict(status=status,available_spaces=['IMAGE_PIXEL']+(['SONAR_RELATIVE','GEOGRAPHIC'] if status=='GEOGRAPHIC' else []),unavailable_spaces=[] if status=='GEOGRAPHIC' else ['SONAR_RELATIVE','GEOGRAPHIC'],reason_code=reason),pixel_convention=PixelConvention().model_dump(),image_geometry=None,coordinate_provenance=provenance,coordinates=coordinates,physical_dimensions=physical)
