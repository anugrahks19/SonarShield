"""Local survey job; source hashes, bounded progress/resume and explicit cancellation."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.runtime.survey_job import run_job
parser=argparse.ArgumentParser()
parser.add_argument('log',type=Path);parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--device',default='cpu');parser.add_argument('--max-windows',type=int,default=10)
parser.add_argument('--rows',type=int,default=512);parser.add_argument('--overlap',type=int,default=64)
parser.add_argument('--cancel-file',type=Path);parser.add_argument('--resume',action='store_true');parser.add_argument('--no-tiles',action='store_true')
parser.add_argument('--geometry-profile',type=Path,help='Reviewed source-bound xtf-flat-bottom-v1 JSON; invalid geometry fails closed.')
args=parser.parse_args()
profile=None
if args.geometry_profile:
    if args.geometry_profile.stat().st_size>65536:parser.error('Geometry profile exceeds 64 KiB.')
    profile=json.loads(args.geometry_profile.read_text(encoding='utf-8-sig'))
print(json.dumps(run_job(args.log,args.output_dir,args.device,args.max_windows,args.rows,args.overlap,not args.no_tiles,args.cancel_file,args.resume,geometry_profile=profile)))
