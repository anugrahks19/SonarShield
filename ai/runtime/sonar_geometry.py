"""Bounded, operator-configured flat-bottom XTF geometry; never field certification.

Only yaw-per-ping and a pose-rotated GPS-to-sensor lever arm are supported.
Large pitch/roll, unresolved heave, invalid altitude and ambiguous orientation fail closed.
"""
import math
from datetime import datetime
from typing import Literal
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChannelGeometry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    side: Literal['PORT', 'STARBOARD']
    sample_order: Literal['NEAR_TO_FAR', 'FAR_TO_NEAR']


class SurveyGeometry(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    version: Literal['xtf-flat-bottom-v1']
    source_log_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    configuration_reference: str = Field(min_length=10, max_length=2000)
    projection_authorized: Literal[True]
    navigation_datum: Literal['WGS84']
    nav_units_code: Literal[3]
    timestamp_timezone: Literal['UTC']
    position_reference: Literal['VESSEL_GPS', 'SENSOR']
    channels: dict[int, ChannelGeometry]
    altitude_source_reference: str = Field(min_length=10, max_length=2000)
    altitude_scale: float = Field(gt=0, le=100)
    heading_source_reference: str = Field(min_length=10, max_length=2000)
    pose_alignment_reference: str = Field(min_length=10, max_length=2000)
    zero_heave_verified: Literal[True]
    forward_offset_m: float = Field(default=0, ge=-100, le=100)
    starboard_offset_m: float = Field(default=0, ge=-100, le=100)
    down_offset_m: float = Field(default=0, ge=-100, le=100)
    ground_resolution_m: float = Field(gt=0, le=10)
    max_tilt_deg: float = Field(default=2, gt=0, le=5)
    max_navigation_gap_seconds: float = Field(default=2, gt=0, le=10)
    max_speed_m_s: float = Field(default=15, gt=0, le=30)

    @model_validator(mode='after')
    def no_double_offset(self):
        if not self.channels or len(self.channels)>6 or any(k<0 or k>5 for k in self.channels):
            raise ValueError('Configure 1-6 explicit channels.')
        if self.position_reference=='SENSOR' and any((self.forward_offset_m,self.starboard_offset_m,self.down_offset_m)):
            raise ValueError('Sensor navigation must not receive a second GPS lever-arm correction.')
        return self


def geodesic():
    try:
        from geographiclib.geodesic import Geodesic
    except ImportError as exc:
        raise RuntimeError('Geometry requires geographiclib==2.1 from requirements-raw.txt.') from exc
    return Geodesic.WGS84


def offset_position(lat,lon,north,east):
    if not all(math.isfinite(v) for v in (lat,lon,north,east)) or not -90<=lat<=90 or not -180<=lon<=180:
        raise ValueError('Invalid navigation coordinates.')
    if math.hypot(north,east)>1000:
        raise ValueError('Projection is bounded to 1 km from the navigation position.')
    point=geodesic().Direct(lat,lon,math.degrees(math.atan2(east,north)),math.hypot(north,east))
    return point['lat2'],point['lon2']


def sensor_navigation(row,profile):
    if row.get('nav_units_code')!=profile.nav_units_code:
        raise ValueError('Navigation unit code disagrees with the reviewed profile.')
    channel=profile.channels.get(row['channel'])
    if channel is None:
        raise ValueError('Channel geometry is not explicitly configured.')
    if row.get('channel_type_raw')!=({'PORT':1,'STARBOARD':2}[channel.side]):
        raise ValueError('Channel side disagrees with the XTF header.')
    raw_time=row.get('timestamp_raw')
    if not raw_time:
        raise ValueError('Missing acquisition timestamp.')
    # XTF itself has no timezone; the explicit reviewed profile supplies it.
    stamp=datetime.fromisoformat(raw_time)
    if stamp.tzinfo is not None:
        raise ValueError('Unexpected timezone-bearing XTF timestamp.')
    stamp=datetime.fromisoformat(raw_time+'+00:00')
    heading=float(row['heading_raw']); pitch=float(row['pitch_raw']); roll=float(row['roll_raw'])
    altitude=float(row['altitude_raw'])*profile.altitude_scale; slant=float(row['slant_range_m'])
    if not all(math.isfinite(v) for v in (heading,pitch,roll,altitude,slant,float(row['heave_raw']))):
        raise ValueError('Non-finite pose or range.')
    if not 0<=heading<360 or abs(pitch)>profile.max_tilt_deg or abs(roll)>profile.max_tilt_deg:
        raise ValueError('Attitude exceeds the supported near-level flat-bottom model.')
    if abs(float(row['heave_raw']))>1e-6:
        raise ValueError('Nonzero heave needs an independently aligned vertical solution; no correction is guessed.')
    if not 0<altitude<slant<=1000:
        raise ValueError('Altitude must be positive and smaller than the verified slant range.')
    prefix='ship' if profile.position_reference=='VESSEL_GPS' else 'sensor'
    lat=float(row[prefix+'_y_raw']);lon=float(row[prefix+'_x_raw'])
    # Body forward/right/down to north/east/down: Rz(heading) Ry(pitch) Rx(roll).
    h,p,r=map(math.radians,(heading,pitch,roll));f,s,d=profile.forward_offset_m,profile.starboard_offset_m,profile.down_offset_m
    right=math.cos(r)*s-math.sin(r)*d; down=math.sin(r)*s+math.cos(r)*d
    forward=math.cos(p)*f+math.sin(p)*down
    north=math.cos(h)*forward-math.sin(h)*right;east=math.sin(h)*forward+math.cos(h)*right
    lat,lon=offset_position(lat,lon,north,east)
    return dict(latitude=lat,longitude=lon,heading_deg=heading,timestamp=stamp.isoformat(),altitude_m=altitude,slant_range_m=slant)


def rectify(block,profile):
    profile=profile if isinstance(profile,SurveyGeometry) else SurveyGeometry.model_validate(profile)
    nav=[sensor_navigation(row,profile) for row in block]
    if len({row['channel'] for row in block})!=1:
        raise ValueError('Mixed-channel raster.')
    side=profile.channels[block[0]['channel']]
    distances=[0.0]
    for a,b in zip(nav,nav[1:]):
        dt=(datetime.fromisoformat(b['timestamp'])-datetime.fromisoformat(a['timestamp'])).total_seconds()
        if not 0<dt<=profile.max_navigation_gap_seconds:
            raise ValueError('Navigation timestamps are nonmonotonic or contain a gap.')
        distance=geodesic().Inverse(a['latitude'],a['longitude'],b['latitude'],b['longitude'])['s12']
        if distance/dt>profile.max_speed_m_s:
            raise ValueError('Navigation jump exceeds configured vessel speed.')
        distances.append(distances[-1]+distance)
    extent=min(math.sqrt(n['slant_range_m']**2-n['altitude_m']**2) for n in nav)
    width=int(math.floor(extent/profile.ground_resolution_m))
    if not 2<=width<=4096:
        raise ValueError('Ground-range raster width must be 2-4096 pixels.')
    across=(np.arange(width)+.5)*profile.ground_resolution_m
    if side.side=='PORT': across=across[::-1]
    image=[]
    for row,n in zip(block,nav):
        samples=row['samples'] if side.sample_order=='NEAR_TO_FAR' else row['samples'][::-1]
        # Slant bins are interpreted as equal-width bin centers, per explicit profile.
        source=(np.arange(len(samples))+.5)*n['slant_range_m']/len(samples)
        query=np.sqrt(across**2+n['altitude_m']**2)
        image.append(np.interp(query,source,samples,left=np.nan,right=np.nan))
    projected=np.vstack(image)
    if not np.isfinite(projected).all():
        raise ValueError('Ground grid reaches an unsupported source sample bin.')
    gray=np.rint(projected*255/np.iinfo(block[0]['samples'].dtype).max).clip(0,255).astype(np.uint8)
    for i,n in enumerate(nav): n['track_distance_m']=distances[i]
    geometry=dict(version=profile.version,profile=profile.model_dump(mode='json'),navigation=nav,width=width,height=len(block),status='OPERATOR_CONFIGURED_NOT_FIELD_VALIDATED',model='FLAT_BOTTOM_NEAR_LEVEL',ground_resolution_m=profile.ground_resolution_m,side=side.side,supported_corrections=['SLANT_TO_GROUND_FLAT_BOTTOM','PER_PING_YAW','POSE_ROTATED_GPS_LEVER_ARM'],unsupported_corrections=['FULL_BEAM_PITCH_ROLL_FOOTPRINT','UNALIGNED_HEAVE','SLOPING_BOTTOM'],water_column_removed=True)
    return gray,geometry


def project_box(box,geometry):
    x1,y1,x2,y2=map(float,box);width=geometry['width'];height=geometry['height']
    if not 0<=x1<x2<=width or not 0<=y1<y2<=height:
        raise ValueError('Candidate outside rectified raster.')
    nav=geometry['navigation'];cy=(y1+y2)/2
    def at_y(y):
        # Navigation is attached to ping row centers, not raster boundaries.
        coordinate=max(0,min(height-1,y-.5));i=int(coordinate);j=min(i+1,height-1);fraction=coordinate-i
        a,b=nav[i],nav[j];distance=geodesic().Inverse(a['latitude'],a['longitude'],b['latitude'],b['longitude'])
        point=geodesic().Direct(a['latitude'],a['longitude'],distance['azi1'],distance['s12']*fraction)
        heading=(a['heading_deg']+fraction*((b['heading_deg']-a['heading_deg']+180)%360-180))%360
        track=a['track_distance_m']+fraction*(b['track_distance_m']-a['track_distance_m'])
        return point['lat2'],point['lon2'],heading,track
    lat,lon,heading,track=at_y(cy)
    cx=(x1+x2)/2;across=(cx if geometry['side']=='STARBOARD' else cx-width)*geometry['ground_resolution_m']
    angle=math.radians(heading);lat,lon=offset_position(lat,lon,-across*math.sin(angle),across*math.cos(angle))
    dimensions=dict(width_m=(x2-x1)*geometry['ground_resolution_m'],height_m=abs(at_y(y2)[3]-at_y(y1)[3]),method='RECTIFIED_ACROSS_RANGE_AND_SENSOR_TRACK_EXTENTS',status='ESTIMATED_NOT_FIELD_VALIDATED')
    return dict(geographic=dict(coordinate_system='WGS84',latitude=lat,longitude=lon,heading_deg=heading),sonar=dict(coordinate_system='SONAR_RELATIVE',range_m=abs(across),across_track_m=across,along_track_m=track),physical_dimensions=dimensions)


def attach_localization(candidate,geometry):
    projected=project_box(candidate['detection']['bbox'],geometry)
    localization=candidate['localization']
    localization['coordinates'].update(geographic=projected['geographic'],sonar=projected['sonar'])
    localization['physical_dimensions']=projected['physical_dimensions']
    localization['metadata'].update(status='GEOGRAPHIC',available_spaces=['IMAGE_PIXEL','SONAR_RELATIVE','GEOGRAPHIC'],unavailable_spaces=[],reason_code='OPERATOR_CONFIGURED_FLAT_BOTTOM_ESTIMATE_NOT_FIELD_VALIDATED')
    localization['coordinate_provenance']=[dict(source_space='IMAGE_PIXEL',target_space='WGS84',transform='XTF_FLAT_BOTTOM_PER_PING_WGS84_GEODESIC',geometry_version='1.0',source_dimensions=[geometry['width'],geometry['height']],target_dimensions=None)]
    candidate['quality']['localization']['flags']=[dict(code='RAW_GEOMETRY_NOT_FIELD_VALIDATED',severity='WARNING')]
    candidate['localization_uncertainty']['error_envelope'].update(status='NOT_ESTIMABLE',reason='No known-target field reference validation for this survey/profile.')
