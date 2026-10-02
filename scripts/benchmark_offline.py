"""Actual hardware benchmark harness; repeated native pipeline, no training/export fitting."""
import argparse,json,platform,statistics,sys,time,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil
from ai.runtime.pipeline import AnalysisRuntime,sha256_file,MAX_IMAGE_BYTES
parser=argparse.ArgumentParser();parser.add_argument('image',type=Path);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--runs',type=int,default=10);parser.add_argument('--device',default='cpu');parser.add_argument('--no-tiles',action='store_true')
args=parser.parse_args()
if not 3<=args.runs<=100:parser.error('runs must be 3-100')
with args.image.open('rb') as stream:data=stream.read(MAX_IMAGE_BYTES+1)
runtime=AnalysisRuntime(device=args.device);process=psutil.Process();peak=[0];stop=threading.Event()
def monitor():
    while not stop.wait(.02):peak[0]=max(peak[0],process.memory_info().rss)
worker=threading.Thread(target=monitor,daemon=True);worker.start();timings=[];outputs=[]
try:
    for _ in range(args.runs+1):
        start=time.perf_counter();out=runtime.analyze(data,args.image.name,not args.no_tiles);timings.append(time.perf_counter()-start);outputs.append(len(out.candidates))
finally:stop.set();worker.join()
warm=sorted(timings[1:]);p95=warm[min(len(warm)-1,__import__('math').ceil(.95*len(warm))-1)]
record=dict(version=1,device=args.device,platform=platform.platform(),processor=platform.processor(),logical_cpus=psutil.cpu_count(),total_ram_bytes=psutil.virtual_memory().total,image_sha256=sha256_file(args.image),input_bytes=len(data),tiled=not args.no_tiles,cold_seconds=timings[0],warm_seconds=timings[1:],warm_p50_seconds=statistics.median(warm),warm_p95_seconds=p95,serial_images_per_second=1/statistics.mean(warm),process_peak_rss_bytes_sampled=peak[0],memory_sampling_ms=20,power='NOT_MEASURED',export_equivalence='NOT_EVALUATED',candidate_counts=outputs,artifacts=runtime.hashes,performance_scope='THIS_DEVICE_AND_INPUT_ONLY_NOT_ACCURACY')
args.output.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
