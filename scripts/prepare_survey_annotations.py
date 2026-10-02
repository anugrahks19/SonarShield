"""Export bounded survey windows for HUMAN annotation, never empty negatives."""
import argparse,json,sys,itertools
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.runtime.xtf import packets,windows
from ai.runtime.pipeline import sha256_file

def prepare(log,output,max_windows=4,rows=256):
 from PIL import Image
 import numpy as np
 log=Path(log);output=Path(output)
 if output.exists() and any(output.iterdir()):raise ValueError('Use a new output directory; existing annotations will not be overwritten.')
 output.mkdir(parents=True,exist_ok=True);source=sha256_file(log);manifest=[]
 for i,(gray,ref) in enumerate(itertools.islice(windows(packets(log),rows=rows),max_windows)):
  name=f'{log.stem}-window-{i:05d}.png';Image.fromarray(gray).save(output/name)
  positive=gray[gray>0];low,high=np.percentile(positive,[2,98]) if positive.size else (0,0)
  display=np.rint(np.clip((gray.astype(float)-low)/max(1,float(high-low)),0,1)*255).astype(np.uint8)
  Image.fromarray(display).save(output/f'display-{name}')
  (output/f'{name}.source.json').write_text(json.dumps(ref,indent=2,allow_nan=False),encoding='utf-8')
  manifest.append(dict(display_preview=f'display-{name}',display_transform='ANNOTATION_ONLY_8BIT_PERCENTILE_2_98_NOT_MODEL_PREPROCESSING',display_limits=[float(low),float(high)],image=name,source_file=log.name,source_sha256=source,channel=ref['channel'],segment=ref['segment'],row_indices=ref['row_indices'],ping_numbers=ref['ping_numbers'],rendering=ref['rendering'],acquisition_group='USGS_2015-315-FA_15CCT03',annotation_status='UNREVIEWED_NOT_A_NEGATIVE',split='UNASSIGNED_EXCLUDED_FROM_TRAINING'))
 (output/'annotation-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print(f'Prepared {len(manifest)} windows. No training labels or background claims were generated.')
 return manifest

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--max-windows',type=int,default=4);p.add_argument('--rows',type=int,default=256);a=p.parse_args()
 if not 1<=a.max_windows<=100:p.error('max-windows must be 1-100')
 prepare(a.log,a.output_dir,a.max_windows,a.rows)
