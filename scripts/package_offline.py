"""Build a private native inference bundle with exact checksums. Never downloads artifacts."""
import argparse,hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if args.output.exists():parser.error('Choose a new output file; existing bundles are never overwritten.')
files=[]
for folder in ['api','runtime','schemas','detection','evidence']:
    files.extend(sorted((root/'ai'/folder).glob('*.py')))
files.extend([root/'scripts/offline_analyze.py',root/'scripts/benchmark_offline.py',root/'scripts/analyze_xtf.py',root/'requirements-inference.txt',root/'requirements-raw.txt',root/'requirements-benchmark.txt',root/'models/v6/detector_v6_p2_sss/weights/best.pt',root/'ai/fusion/weights/gate_d_fusion_model.pkl'])
for path in files:
    if not path.is_file():parser.error('Required local bundle component is missing: '+str(path.relative_to(root)))
manifest={'format':'SONAR_SHIELD_NATIVE_OFFLINE','version':1,'model_parameters':'UNCHANGED','calibration':'UNAVAILABLE_REVIEW_ONLY','licensing':'PRIVATE_LOCAL_BUNDLE_VERIFY_ARTIFACT_RIGHTS_BEFORE_REDISTRIBUTION','files':[]}
args.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        relative=path.relative_to(root).as_posix();data=path.read_bytes();manifest['files'].append({'path':relative,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()});archive.writestr(relative,data)
    archive.writestr('OFFLINE_MANIFEST.json',json.dumps(manifest,indent=2))
print(json.dumps({'bundle':str(args.output),'components':len(files),'secret_files_included':False}))
