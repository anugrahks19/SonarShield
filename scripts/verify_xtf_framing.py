"""Full-file packet framing audit; payload semantics remain separately bounded."""
import argparse,ctypes,io,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
def verify(path):
 from pyxtf import XTFPacketStart,XTFFileHeader
 size=path.stat().st_size;types={};offset=1024
 if size>2*1024**3:raise ValueError('File exceeds supported 2 GiB bound.')
 with path.open('rb') as f:
  header=f.read(1024)
  if len(header)!=1024 or header[0]!=123:raise ValueError('Invalid XTF header.')
  parsed=XTFFileHeader.create_from_buffer(io.BytesIO(header))
  if not 1<=parsed.channel_count()<=6:raise ValueError('Unsupported channel header extent.')
  while offset<size:
   f.seek(offset);data=f.read(ctypes.sizeof(XTFPacketStart))
   if len(data)!=ctypes.sizeof(XTFPacketStart):raise ValueError('Truncated packet header.')
   start=XTFPacketStart.from_buffer_copy(data);length=int(start.NumBytesThisRecord)
   if start.MagicNumber!=0xFACE or not len(data)<=length<=8*1024**2 or offset+length>size:raise ValueError(f'Invalid packet framing at {offset}.')
   type_=str(start.HeaderType);types[type_]=types.get(type_,0)+1;offset+=length
 return {'file':path.name,'bytes':size,'status':'COMPLETE_FRAMING_VALIDATED','packet_type_counts':types,'payload_semantics':'NOT_FULLY_DECODED','unknown_types_not_interpreted':sorted(set(types)-{'0'})}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();results=[]
 for i,path in enumerate(sorted(a.directory.glob('*.xtf'))):
  try:results.append(verify(path))
  except Exception as e:results.append({'file':path.name,'status':'FAILED','reason':str(e)})
  if i%20==0:print(f'Framing checked {i+1} logs',flush=True)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps({'logs':len(results),'failed':sum(x['status']=='FAILED' for x in results)}))
