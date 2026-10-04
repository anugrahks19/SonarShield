"""Freeze detector-only experimental bundle; never replace deployed artifacts."""
import argparse,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
from importlib.metadata import version
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import NAMES,sha

WEIGHTS={'D1':'models/controlled/m2_d1_curated_r01_640_01/weights/best.pt',
 'M2.08':'models/controlled/m2_submission_ft15_smalltargets_01/weights/best.pt',
 'M2.10':'models/controlled/m2_submission_ft10_warmupfix_02/weights/best.pt'}

def validate_selection(report):
    chosen=report['selected_precision_floor_candidate']
    if not chosen or chosen['model'] not in WEIGHTS or chosen['scope']!='EXPLORATORY_DEV_NOT_PRODUCTION_APPROVED':
        raise ValueError('No valid measured candidate selection.')
    if chosen['deployed'] or chosen['calibrated_probability']:raise ValueError('Unsupported deployment/calibration claim.')
    if chosen['policy']!='GLOBAL':raise ValueError('This bundle supports the measured global precision-floor protocol only.')
    thresholds=chosen['thresholds']
    if set(thresholds)!=set(map(str,NAMES)) or len(set(thresholds.values()))!=1:
        raise ValueError('Incomplete/inconsistent class thresholds.')
    threshold=next(iter(thresholds.values()))
    point=report['models'][chosen['model']]['best_global_recall_at_precision_80']
    if threshold!=point['threshold'] or chosen['metrics']!=point or point['precision']<.8:
        raise ValueError('Selected metrics/threshold mismatch.')
    if not .001<=threshold<=1:raise ValueError('Invalid confidence threshold.')
    return chosen

def freeze(root,selection_path,output):
    root,selection_path,output=map(lambda x:Path(x).resolve(),(root,selection_path,output))
    if output.exists():raise ValueError('Frozen output exists; never overwrite.')
    if not output.is_relative_to(root/'models/submission'):raise ValueError('Bundle must stay in models/submission.')
    report=json.loads(selection_path.read_text(encoding='utf-8'));chosen=validate_selection(report)
    sources={name:root/path for name,path in WEIGHTS.items()}
    for name,path in sources.items():
        if sha(path)!=report['models'][name]['evidence']['checkpoint_sha256']:raise ValueError('Checkpoint changed: '+name)
    import torch
    checks={}
    for name,path in sources.items():
        saved=torch.load(path,map_location='cpu',weights_only=False);model=saved.get('ema') or saved.get('model')
        names={int(k):v for k,v in model.names.items()};strides=[int(v) for v in model.stride.tolist()]
        if names!=NAMES or strides!=[4,8,16,32]:raise ValueError('Class/architecture mismatch: '+name)
        checks[name]={'class_ids':names,'strides':strides,'sha256':sha(path)};del model,saved
    current_runtime=root/'ai/runtime/pipeline.py'
    runtime=current_runtime.read_text(encoding='utf-8')
    if "models/v6/detector_v6_p2_sss/weights/best.pt" not in runtime or "status='REVIEW'" not in runtime or "calibration_version='UNAVAILABLE'" not in runtime:
        raise ValueError('Current deployment/runtime scope changed; audit before freezing.')
    artifacts={}
    for name,relative in {'fusion':'ai/fusion/weights/gate_d_fusion_model.pkl','fusion_manifest':'ai/fusion/weights/gate_d_manifest.json',
        'decision_policy':'ai/reliability/weights/score_policy.json','policy_manifest':'ai/reliability/weights/gate_e_manifest.json',
        'reliability_mapping':'ai/reliability/weights/reliability_mapping.json','unknown_detector':'ai/reliability/weights/unknown_detector.pkl'}.items():
        path=root/relative
        artifacts[name]={'path':relative,'exists':path.is_file(),'sha256':sha(path) if path.is_file() else None,
            'compatible_with_selected_detector':'NOT_ESTABLISHED','attached_to_frozen_bundle':False}
    manifest={'schema':'module2-detector-candidate-v1','created_at':datetime.now(timezone.utc).isoformat(),
        'status':'FROZEN_EXPERIMENTAL_DETECTOR_ONLY_NOT_DEPLOYED','selected_model':chosen['model'],
        'weights':'candidate.pt','weights_sha256':checks[chosen['model']]['sha256'],
        'class_map':NAMES,'class_map_sha256':sha(root/'ai/schemas/class_map.py'),'detector_architecture_checks':checks,
        'inference_protocol':{'imgsz':640,'batch':1,'half':False,'augment':False,'conf_floor':.001,'max_det':300,
            'nms_iou':.7,'post_nms_confidence_comparison':'>=','thresholds':chosen['thresholds'],
            'tiled_auxiliary':False,'input':'JPEG/PNG RGB/BGR interpreted using standard pinned Ultralytics loader; letterbox to 640'},
        'operating_point_metrics':chosen['metrics'],'metric_scope':'REUSED_HISTORICAL_DEV_NOT_INDEPENDENT_TEST_OR_CALIBRATION',
        'manifest_sha256':report['manifest_sha256'],'selection_evidence_sha256':sha(selection_path),
        'decision':'REVIEW_ONLY','automatic_confirmation_enabled':False,'fusion':None,'calibration':None,
        'probability_of_correctness':'UNAVAILABLE','existing_artifact_compatibility':artifacts,
        'runtime_integration':'NOT_ENABLED: current runtime uses V6/conf0.15/global+tiled and is not this detector-only measurement.',
        'current_runtime_sha256':sha(current_runtime),'current_runtime_detector_sha256':sha(root/'models/v6/detector_v6_p2_sss/weights/best.pt'),
        'rollback':{'weights':'rollback-d1.pt','sha256':checks['D1']['sha256'],'scope':'PRESERVED_LOCAL_EXPERIMENT_BASELINE_NOT_A_DEPLOYMENT_ROLLBACK'},
        'package_versions':{name:version(name) for name in ['ultralytics','torch','numpy']},
        'release_80_precision_80_recall_passed':False,'public_xtf_enabled':False,'new_training_planned':False}
    output.mkdir(parents=True)
    for name,filename in [(chosen['model'],'candidate.pt'),('D1','rollback-d1.pt')]:
        shutil.copy2(sources[name],output/filename)
        if sha(output/filename)!=checks[name]['sha256']:raise ValueError('Frozen copy hash mismatch.')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (output/'README.txt').write_text('EXPERIMENTAL DETECTOR-ONLY BUNDLE. NOT DEPLOYED.\nDo not overwrite models/v6 or attach existing fusion/policy/calibration.\nThe operating-point figures are exploratory DEV measurements, not website accuracy.\nInference recipe and identity hashes are in manifest.json. Both precision and recall >=80% were not achieved.\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--selection',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();m=freeze(a.root,a.selection,a.output);print(json.dumps({'status':m['status'],'selected':m['selected_model'],'metrics':m['operating_point_metrics'],'weights_sha256':m['weights_sha256']},indent=2))
