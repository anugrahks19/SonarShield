"""Read-only bounded real-survey audit. Never labels data or runs a model."""
import argparse,hashlib,itertools,json,sys,ctypes,io,math
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.runtime.xtf import packets,windows

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def audit(directory,output,max_pings=32,hash_files=False):
 import pyxtf
 from PIL import Image
 directory=Path(directory);output=Path(output);output.mkdir(parents=True,exist_ok=True)
 logs=sorted(directory.glob('*.xtf'));entries=[]
 for i,log in enumerate(logs):
  entry={'file':log.name,'bytes':log.stat().st_size,'role':'DEV_SURVEY_UNLABELLED','acquisition_group':'USGS_2015-315-FA_15CCT03','labels':'NOT_PROVIDED','sha256':digest(log) if hash_files else None,'whole_file_validated':False}
  try:
   with log.open('rb') as f:header=pyxtf.XTFFileHeader.create_from_buffer(io.BytesIO(f.read(1024)))
   entry['header']={'nav_units_code':int(header.NavUnits),'sonar_name':header.SonarName.decode(errors='replace'),'recording_program':header.RecordingProgramName.decode(errors='replace'),'channel_types':[int(c.TypeOfChannel) for c in header.sonar_info],'offsets_raw':[dict(x=float(c.OffsetX),y=float(c.OffsetY),z=float(c.OffsetZ)) for c in header.sonar_info]}
   rows=list(itertools.islice(packets(log),max_pings*len(header.sonar_info)))
   if not rows:raise ValueError('No supported sonar pings in file.')
   entry['sampled_channel_rows']=len(rows);entry['sampled_ping_numbers']=sorted({x['ping_number'] for x in rows})
   entry['sample_types']=sorted({str(x['samples'].dtype) for x in rows});entry['samples_per_row']=sorted({len(x['samples']) for x in rows})
   entry['timestamps_raw']=[rows[0].get('timestamp_raw'),rows[-1].get('timestamp_raw')]
   fields=['sensor_x_raw','sensor_y_raw','heading_raw','altitude_raw','pitch_raw','roll_raw','heave_raw','slant_range_m']
   entry['sampled_raw_ranges']={k:[min(x[k] for x in rows),max(x[k] for x in rows)] for k in fields}
   entry['coordinates_plausible_degrees']=all(math.isfinite(x['sensor_x_raw']) and math.isfinite(x['sensor_y_raw']) and -180<=x['sensor_x_raw']<=180 and -90<=x['sensor_y_raw']<=90 for x in rows)
   entry['zero_heave_is_not_proof_of_no_motion']=all(x['heave_raw']==0 for x in rows)
   entry['status']='PREFIX_PARSED_NOT_FIELD_VALIDATED'
   if i in {0,len(logs)//2,len(logs)-1}:
    previews=[]
    for j,(gray,ref) in enumerate(windows(rows,rows=max(16,min(512,max_pings)))):
     name=f'{log.stem}-channel-{ref["channel"]}.png';Image.fromarray(gray).save(output/name)
     (output/f'{log.stem}-channel-{ref["channel"]}.json').write_text(json.dumps(ref,indent=2,allow_nan=False),encoding='utf-8');previews.append(name)
    entry['previews']=previews
  except Exception as error:entry['status']='UNSUPPORTED_OR_INVALID';entry['error_type']=type(error).__name__;entry['reason']=str(error)[:500]
  entries.append(entry)
  if i%20==0:print(f'Audited {i+1}/{len(logs)} logs',flush=True)
 report={'created_at':datetime.now(timezone.utc).isoformat(),'log_count':len(logs),'total_bytes':sum(x['bytes'] for x in entries),'bounded_prefix_pings_per_file':max_pings,'full_file_sha256':hash_files,'training_executed':False,'inference_executed':False,'geographic_field_accuracy':'NOT_EVALUATED','ground_truth':'NOT_PROVIDED','entries':entries}
 (output/'survey-audit.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='entries'}))
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--max-pings',type=int,default=32);p.add_argument('--hash-files',action='store_true');a=p.parse_args()
 if not 16<=a.max_pings<=512:p.error('max-pings must be 16-512')
 audit(a.directory,a.output_dir,a.max_pings,a.hash_files)
