"""Gradio transport; package shared ai source before deploying."""
import os
import json
from pathlib import Path
import gradio as gr
import spaces
from ai.runtime.pipeline import AnalysisRuntime, MAX_IMAGE_BYTES

runtime=AnalysisRuntime(root=Path(__file__).parent,device=os.environ.get('SONAR_DEVICE','cuda'))

@spaces.GPU
def analyze_image_gradio(image_filepath,run_tiled_auxiliary=True,metadata_json=""):
    if len(metadata_json.encode()) > 256*1024: raise gr.Error("Metadata exceeds 256 KiB.")
    if not image_filepath: raise gr.Error('No image supplied.')
    try:
        with open(image_filepath,'rb') as stream: data=stream.read(MAX_IMAGE_BYTES+1)
        return runtime.analyze(data,Path(image_filepath).name,run_tiled_auxiliary,json.loads(metadata_json) if metadata_json else None).model_dump_json()
    except (ValueError,FileNotFoundError,RuntimeError) as exc:
        raise gr.Error(str(exc)) from exc

demo=gr.Interface(fn=analyze_image_gradio,inputs=[gr.File(type='filepath',file_types=['.jpg','.jpeg','.png'],label='Sonar image'),gr.Checkbox(value=True,label='Run tiled auxiliary'),gr.Textbox(value='',label='Optional ground-range metadata JSON')],outputs=gr.JSON(label='Analysis'),title='SONAR-SHIELD API',description='Review-only until compatible decision/calibration artifacts are validated.')
if __name__=='__main__': demo.launch()
