"""Bounded local XTF adapter. Revision 42 structures via optional pyxtf 1.4.2.

Never uses pyxtf's pickle index reader. No unvalidated geographic conversion.
Only unsigned 8/16-bit sonar samples, <=6 channels, <=4096 samples per ping.
"""
from datetime import datetime
import ctypes
import io
from pathlib import Path
import numpy as np

def packets(path):
    try:
        from pyxtf import XTFFileHeader,XTFPacketStart,XTFPingHeader,XTFHeaderType
    except ImportError as exc:
        raise RuntimeError('XTF support requires optional pyxtf==1.4.2; install requirements-raw.txt in an isolated environment.') from exc
    path=Path(path)
    if path.suffix.lower()!='.xtf': raise ValueError('Use an XTF file.')
    size=path.stat().st_size
    if size>2*1024**3: raise ValueError('Split logs larger than 2 GiB before local processing.')
    with path.open('rb') as stream:
        header_bytes=stream.read(1024)
        if len(header_bytes)!=1024 or header_bytes[0]!=123: raise ValueError('Invalid/truncated XTF header.')
        header=XTFFileHeader.create_from_buffer(io.BytesIO(header_bytes))
        if not header.sonar_info or not 1<=header.channel_count()<=6: raise ValueError('Only 1-6 channels supported.')
        offset=1024
        while offset<size:
            start_bytes=stream.read(ctypes.sizeof(XTFPacketStart))
            if len(start_bytes)!=ctypes.sizeof(XTFPacketStart): raise ValueError('Truncated packet header.')
            start=XTFPacketStart.from_buffer_copy(start_bytes)
            length=int(start.NumBytesThisRecord)
            if int(start.MagicNumber)!=0xFACE or not ctypes.sizeof(XTFPacketStart)<=length<=8*1024**2 or offset+length>size: raise ValueError('Invalid packet framing/length.')
            tail=stream.read(length-len(start_bytes))
            if len(tail)!=length-len(start_bytes): raise ValueError('Truncated packet.')
            if int(start.HeaderType)==int(XTFHeaderType.sonar):
                ping=XTFPingHeader.create_from_buffer(io.BytesIO(start_bytes+tail),file_header=header)
                if not 1<=int(ping.NumChansToFollow)<=6: raise ValueError('Invalid channel count.')
                if len(ping.ping_chan_headers)!=int(ping.NumChansToFollow) or len(ping.data)!=int(ping.NumChansToFollow): raise ValueError('Incomplete sonar channels.')
                try:
                    timestamp=datetime(ping.Year,ping.Month,ping.Day,ping.Hour,ping.Minute,ping.Second,ping.HSeconds*10000).isoformat()
                except ValueError: timestamp=None
                for channel,samples in zip(ping.ping_chan_headers,ping.data):
                    if samples.dtype.kind!='u' or samples.dtype.itemsize not in {1,2} or not 1<=len(samples)<=4096: raise ValueError('Unsupported sample representation.')
                    if not np.isfinite(samples).all(): raise ValueError('Non-finite samples.')
                    channel_index=int(channel.ChannelNumber)
                    info=header.sonar_info[channel_index] if 0<=channel_index<len(header.sonar_info) else None
                    yield dict(timestamp_raw=timestamp,timestamp_timezone='UNVERIFIED',nav_units_code=int(header.NavUnits),channel_type_raw=int(info.TypeOfChannel) if info else None,ship_x_raw=float(ping.ShipXcoordinate),ship_y_raw=float(ping.ShipYcoordinate),sensor_depth_raw=float(ping.SensorDepth),packet_offset=offset,ping_number=int(ping.PingNumber),channel=int(channel.ChannelNumber),samples=samples.copy(),slant_range_m=float(channel.SlantRange),sensor_x_raw=float(ping.SensorXcoordinate),sensor_y_raw=float(ping.SensorYcoordinate),heading_raw=float(ping.SensorHeading),altitude_raw=float(ping.SensorPrimaryAltitude),pitch_raw=float(ping.SensorPitch),roll_raw=float(ping.SensorRoll),heave_raw=float(ping.Heave),navigation_status='UNVERIFIED_UNITS_DATUM_POSE')
            offset+=length

def windows(records,rows=512,overlap=0):
    if not 16<=rows<=512 or not 0<=overlap<rows: raise ValueError('Window rows must be 16-512; overlap must be smaller than rows.')
    buffers={};counts={};segments={};fresh={};signatures={}
    for original in records:
        record=dict(original);channel=record['channel'];block=buffers.setdefault(channel,[])
        signature=(len(record['samples']),str(record['samples'].dtype),record.get('slant_range_m'))
        if channel in signatures and signatures[channel]!=signature:
            if block and fresh.get(channel,0): yield render(block)
            block.clear();segments[channel]=segments.get(channel,0)+1;fresh[channel]=0
        signatures[channel]=signature
        record['_row_index']=counts.get(channel,0);counts[channel]=record['_row_index']+1
        record['_segment']=segments.get(channel,0);block.append(record);fresh[channel]=fresh.get(channel,0)+1
        if len(block)==rows:
            yield render(block)
            if overlap:del block[:-overlap]
            else:block.clear()
            fresh[channel]=0
    for channel,block in buffers.items():
        if block and fresh.get(channel,0):yield render(block)


def render(block):
    raw=np.vstack([record['samples'] for record in block])
    # Deterministic full-scale conversion, recorded explicitly; not a validated enhancement.
    gray=np.rint(raw.astype(np.float64)*(255/np.iinfo(raw.dtype).max)).astype(np.uint8)
    from ai.runtime.survey import acquisition_quality
    return gray,dict(row_indices=[r.get('_row_index',i) for i,r in enumerate(block)],segment=block[0].get('_segment',0),acquisition_quality=acquisition_quality(block),channel=block[0]['channel'],rendering='FULL_SCALE_LINEAR_UNVALIDATED',ping_numbers=[r['ping_number'] for r in block],packet_offsets=[r['packet_offset'] for r in block],navigation_status='UNVERIFIED_UNITS_DATUM_POSE',navigation=[{k:v for k,v in r.items() if k!='samples'} for r in block])
