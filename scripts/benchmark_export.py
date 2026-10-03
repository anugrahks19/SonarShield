"""Export a PRIVATE checkpoint COPY and compare CPU tensor outputs, no training.

This certifies only the supplied host/input/runtime. It is not an edge-device,
power, detection accuracy, or full evidence/fusion equivalence certification.
"""
import argparse,json,platform,shutil,sys,time,statistics,os
os.environ["YOLO_AUTOINSTALL"]="false"
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
import onnxruntime as ort
import onnx  # Fail before any export if isolated ONNX dependencies are incomplete.
import cv2
from ultralytics import YOLO
from ai.runtime.pipeline import sha256_file,decode_image,MAX_IMAGE_BYTES


def benchmark(weights,image,output,runs=10):
    output=Path(output)
    if output.exists():raise ValueError('Choose a new private export directory.')
    if not 3<=runs<=100:raise ValueError('Runs must be 3-100.')
    with Path(image).open('rb') as f:data=f.read(MAX_IMAGE_BYTES+1)
    decoded=decode_image(data)
    before=sha256_file(weights);output.mkdir(parents=True)
    copied=output/'detector-copy.pt';shutil.copy2(weights,copied)
    torch.set_num_threads(2)
    model=YOLO(str(copied));model.model.eval()
    export=model.export(format='onnx',imgsz=640,opset=17,simplify=False,device='cpu',dynamic=False,batch=1,nms=False)
    exported=Path(export)
    from ultralytics.data.augment import LetterBox
    resized=LetterBox(new_shape=(640,640),auto=False,stride=32)(image=decoded)
    tensor=np.ascontiguousarray(resized[:,:,::-1].transpose(2,0,1)[None],dtype=np.float32)/255
    session_options=ort.SessionOptions();session_options.intra_op_num_threads=2;session_options.inter_op_num_threads=1
    session=ort.InferenceSession(str(exported),sess_options=session_options,providers=['CPUExecutionProvider'])
    times={'pytorch':[],'onnx':[]};native=None;actual=None
    with torch.inference_mode():
        for i in range(runs+1):
            start=time.perf_counter();pred=model.model(torch.from_numpy(tensor));native=(pred[0] if isinstance(pred,tuple) else pred).cpu().numpy();elapsed=time.perf_counter()-start
            if i:times['pytorch'].append(elapsed)
            start=time.perf_counter();actual=session.run(None,{session.get_inputs()[0].name:tensor})[0];elapsed=time.perf_counter()-start
            if i:times['onnx'].append(elapsed)
    if sha256_file(weights)!=before:raise RuntimeError('Original checkpoint changed unexpectedly.')
    same=native.shape==actual.shape
    passed=same and bool(np.allclose(native,actual,rtol=2e-4,atol=.01))
    result=dict(version=1,device='THIS_HOST_CPU_ONLY',platform=platform.platform(),processor=platform.processor(),torch=torch.__version__,onnxruntime=ort.__version__,threads=2,source_detector_sha256=before,original_weights_unchanged=True,export_sha256=sha256_file(exported),input_sha256=sha256_file(image),runs=runs,output_shapes=dict(pytorch=list(native.shape),onnx=list(actual.shape)),raw_tensor_equivalence_passed=passed,maximum_absolute_error=float(np.max(np.abs(native-actual))) if same else None,rtol=2e-4,atol=.01,warm_seconds=times,warm_median_seconds={key:statistics.median(value) for key,value in times.items()},power='NOT_MEASURED',full_pipeline_equivalence='NOT_CLAIMED',scope='ONE_INPUT_RAW_OUTPUT_EQUIVALENCE_NOT_ACCURACY_OR_TARGET_EDGE_CERTIFICATION')
    (output/'benchmark.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    if not passed:raise RuntimeError('Export output comparison failed; inspect benchmark.json. Do not promote this export.')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('image',type=Path);p.add_argument('--weights',type=Path,default=Path(__file__).resolve().parents[1]/'models/v6/detector_v6_p2_sss/weights/best.pt');p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--runs',type=int,default=10);a=p.parse_args();print(json.dumps(benchmark(a.weights,a.image,a.output_dir,a.runs)))
