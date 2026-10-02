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
args=parser.parse_args()
print(json.dumps(run_job(args.log,args.output_dir,args.device,args.max_windows,args.rows,args.overlap,not args.no_tiles,args.cancel_file,args.resume)))
