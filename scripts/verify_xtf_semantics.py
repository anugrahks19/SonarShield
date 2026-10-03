"""Stream every supported sonar payload. Unknown/vendor packets remain unsupported."""
import argparse,json,math,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.runtime.xtf import packets
from ai.runtime.pipeline import sha256_file


def audit(directory,output):
    entries=[];start=time.monotonic();logs=sorted(Path(directory).glob('*.xtf'))
    if not logs:raise ValueError('No XTF logs.')
    for index,path in enumerate(logs):
        entry=dict(file=path.name,bytes=path.stat().st_size,sha256=sha256_file(path),channel_rows=0,samples=0,channels={},invalid_timestamps=0,nonfinite_metadata=0)
        try:
            for row in packets(path):
                entry['channel_rows']+=1;entry['samples']+=len(row['samples'])
                channel=str(row['channel']);entry['channels'][channel]=entry['channels'].get(channel,0)+1
                if row['timestamp_raw'] is None:entry['invalid_timestamps']+=1
                if any(not math.isfinite(row[k]) for k in ['slant_range_m','sensor_x_raw','sensor_y_raw','altitude_raw','heading_raw','pitch_raw','roll_raw','heave_raw']):entry['nonfinite_metadata']+=1
            entry['status']='ALL_SUPPORTED_SONAR_PAYLOADS_DECODED' if entry['channel_rows'] else 'NO_SUPPORTED_SONAR_PAYLOAD'
        except Exception as exc:entry.update(status='FAILED',error_type=type(exc).__name__,reason=str(exc)[:300])
        entries.append(entry)
        result=dict(version=1,files_completed=len(entries),total_files=len(logs),elapsed_seconds=time.monotonic()-start,inference_calls=0,training_executed=False,scope='SUPPORTED_SONAR_PAYLOADS_ONLY_VENDOR_PACKETS_NOT_INTERPRETED',field_geometry='NOT_VALIDATED',entries=entries)
        temp=Path(output).with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8');temp.replace(output)
        print(f'Semantic decode {index+1}/{len(logs)}: {entry["status"]} ({entry["channel_rows"]} rows)',flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();audit(a.directory,a.output)
