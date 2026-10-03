"""Local frozen inference only after independent labels exist. No HF calls/training."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.runtime.pipeline import AnalysisRuntime,sha256_file
from ai.runtime.survey_evaluation import evaluate


def run(pool, annotation_file, output):
    pool,output=Path(pool),Path(output)
    if output.exists():raise ValueError('Use a new evidence directory; do not overwrite a test run.')
    m=json.loads((pool/'manifest.json').read_text(encoding='utf-8'))
    a=json.loads(Path(annotation_file).read_text(encoding='utf-8'))
    # Validate completeness before loading any model or running inference.
    lookup={e['image_sha256']:e for e in a['annotations']}
    if len(lookup)!=len(a['annotations']):raise ValueError('Duplicate reviews.')
    tests=[e for e in m['images'] if e['split']=='TEST']
    if not tests:raise ValueError('No TEST images.')
    for e in tests:
        label=lookup.get(e['image_sha256'],{})
        if label.get('status') not in {'TARGETS_CONFIRMED','BACKGROUND_CONFIRMED'} or label.get('qualified_review') is not True or not label.get('reviewer','').strip():
            raise ValueError('Holdout annotation incomplete; no inference was started.')
        path=(pool/e['image']).resolve()
        if path.parent!=pool.resolve() or sha256_file(path)!=e['image_sha256']:
            raise ValueError('Image path/hash mismatch.')
        from PIL import Image
        with Image.open(path) as header:
            if header.size!=(e['width'],e['height']):raise ValueError('Raster dimensions disagree with manifest.')
    rendering=Path(__file__).resolve().parents[1]/'ai/runtime/sonar_rendering.py'
    if sha256_file(rendering)!=m['rendering_source_sha256']:raise ValueError('Rendering source changed.')
    runtime=AnalysisRuntime(device='cpu');runtime.initialize()
    predictions={'artifacts':runtime.hashes,'rendering_source_sha256':m['rendering_source_sha256'],
                 'processing_source_sha256':{name:sha256_file(Path(__file__).resolve().parents[1]/name) for name in
                     ['ai/runtime/pipeline.py','ai/runtime/survey_evaluation.py','ai/detection/tiled_detector.py']},
                 'operating_point':{'detector_confidence_min':.15,'tiled':True,'matching_iou':.5},'images':[]}
    output.mkdir(parents=True)
    for e in tests:
        result=runtime.analyze((pool/e['image']).read_bytes(),e['image'],True).model_dump(mode='json')
        (output/(e['image']+'.analysis.json')).write_text(json.dumps(result,allow_nan=False),encoding='utf-8')
        predictions['images'].append({'image_sha256':e['image_sha256'],'objects':[{'class_id':c['detection']['class_id'],
           'bbox':c['detection']['bbox'],'confidence':c['detection']['confidence']} for c in result['candidates']]})
    (output/'predictions.json').write_text(json.dumps(predictions,indent=2),encoding='utf-8')
    report=evaluate(m,a,predictions)
    report['input_evidence_sha256']={'manifest':sha256_file(pool/'manifest.json'),'annotations':sha256_file(annotation_file),
                                   'predictions':sha256_file(output/'predictions.json')}
    (output/'evaluation.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pool',type=Path);p.add_argument('annotations',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.pool,a.annotations,a.output);print(json.dumps(r,indent=2))
