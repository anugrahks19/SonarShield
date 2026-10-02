"""Offline inference and measured runtime; never trains or changes checkpoints."""
import argparse,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.runtime.pipeline import AnalysisRuntime,MAX_IMAGE_BYTES
parser=argparse.ArgumentParser()
parser.add_argument('image',type=Path); parser.add_argument('--metadata',type=Path)
parser.add_argument('--device',default='cpu'); parser.add_argument('--no-tiles',action='store_true')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
with args.image.open('rb') as stream: data=stream.read(MAX_IMAGE_BYTES+1)
metadata=json.loads(args.metadata.read_text()) if args.metadata else None
start=time.perf_counter()
response=AnalysisRuntime(device=args.device).analyze(data,args.image.name,not args.no_tiles,metadata)
args.output.write_text(response.model_dump_json(indent=2),encoding='utf-8')
print(json.dumps(dict(device=args.device,candidates=len(response.candidates),cold_end_to_end_seconds=round(time.perf_counter()-start,3),output=str(args.output))))
