"""Build a bounded judge/demo package. Does not train, infer or deploy."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def build(root, output):
    root=root.resolve(); output=output.resolve()
    if not output.is_relative_to(root/'submission'):
        raise ValueError('Output must be inside this repository submission directory')
    if output.exists():
        raise ValueError('Output exists; choose a fresh directory')
    names=['README.md','docs/ARCHITECTURE.md','docs/JUDGE_WALKTHROUGH.md',
           'docs/MODULE2_M212_SUBMISSION.md','docs/MODULE2_M211_RELEASE.md',
           'docs/PS26057_COMPLIANCE.md','docs/EDGE_DEVICE_API.md','docs/XTF_ACCURACY_RELEASE.md',
           'docs/MODULE2_M208_RESULTS.md','docs/MODULE2_M210_RESULTS.md',
           'docs/metrics/module2-m211-selection-20261004.json',
           'docs/metrics/module2-m211-release-20261004.json',
           'docs/metrics/module2-m211-frozen-manifest-20261004.json',
           'submission/m212_20261004/SONAR_SHIELD_Judge_Deck.pptx']
    sources=[]
    for name in names:
        target='judge-deck.pptx' if name.endswith('.pptx') else name
        sources.append((root/name,target))
    dist=root/'frontend/dist'
    if not (dist/'index.html').is_file():
        raise ValueError('Missing release build')
    allowed={'.html','.js','.css','.svg','.jpg','.png','.json','.woff','.woff2'}
    for p in sorted(dist.rglob('*')):
        if not p.is_file():continue
        if p.is_symlink() or p.suffix not in allowed or not p.resolve().is_relative_to(dist.resolve()):
            raise ValueError('Unexpected static member')
        sources.append((p,'frontend-static/'+p.relative_to(dist).as_posix()))
    bundle=root/'models/submission/m211_detector_only_20261004'
    frozen=json.loads((bundle/'manifest.json').read_text())
    if frozen['status']!='FROZEN_EXPERIMENTAL_DETECTOR_ONLY_NOT_DEPLOYED' or frozen['fusion'] is not None or frozen['calibration'] is not None:
        raise ValueError('Experimental compatibility boundary changed')
    if frozen['public_xtf_enabled'] or frozen['automatic_confirmation_enabled']:
        raise ValueError('Unsupported public/automatic release')
    for name,expected in [('candidate.pt',frozen['weights_sha256']),('rollback-d1.pt',frozen['rollback']['sha256'])]:
        if sha(bundle/name)!=expected:raise ValueError('Frozen checkpoint hash changed')
    for name in ['candidate.pt','rollback-d1.pt','manifest.json','README.txt']:
        sources.append((bundle/name,'experimental-detector/'+name))
    secret=re.compile(rb'(?:hf_[A-Za-z0-9]{20,}|sb_secret_[A-Za-z0-9_-]{12,}|eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    records=[]
    for p,target in sources:
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root):raise ValueError('Missing/unsafe source '+target)
        if target.endswith(('.html','.js','.css','.json','.md','.txt','.svg')) and secret.search(p.read_bytes()):
            raise ValueError('Possible credential in '+target)
        if target.endswith('.pptx'):
            with zipfile.ZipFile(p) as z:
                for item in z.namelist():
                    if item.endswith('.xml') and secret.search(z.read(item)):raise ValueError('Possible credential in deck')
        records.append({'member':target,'bytes':p.stat().st_size,'sha256':sha(p),'source':p.relative_to(root).as_posix()})
    if len({v['member'] for v in records})!=len(records):raise ValueError('Duplicate member')
    manifest={'schema':'sonar-submission-package-v1','date':'2026-10-04',
        'scope':'JUDGE_EVIDENCE_STATIC_DEMO_EXPERIMENTAL_WEIGHTS_NOT_DEPLOYMENT',
        'real_hf_calls':0,'runtime_deployed':False,'accuracy_80_80_achieved':False,
        'members':records,'excluded':['secrets/env files','datasets/survey logs','private reviewer records','unverified fusion/calibration'],
        'static_start':'cd frontend-static; python -m http.server 8783 --bind 127.0.0.1; open http://127.0.0.1:8783/',
        'static_api_boundary':'No live/cloud API; examples/review/report only. External map tiles may be offline.'}
    output.mkdir(parents=True)
    archive=output/'SONAR_SHIELD_Submission.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,target in sources:z.write(p,target)
        z.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
        z.writestr('START_HERE.txt','SONAR-SHIELD PS26057\nRead docs/JUDGE_WALKTHROUGH.md and README.md.\nStatic UI: serve frontend-static over HTTP, use explicit verified examples. No live or cloud routes.\nExperimental M2.08 weights are NOT deployed and have no compatible fusion/calibration.\n80/80 is NOT achieved.\n')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for v in records:
            data=z.read(v['member'])
            assert len(data)==v['bytes'] and hashlib.sha256(data).hexdigest()==v['sha256']
    (output/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    receipt={'archive':archive.relative_to(root).as_posix(),'sha256':sha(archive),
        'bytes':archive.stat().st_size,'member_count':len(records)+2,
        'archive_crc_and_member_hashes':'PASSED','text_and_deck_credential_pattern_scan':'PASSED',
        'frozen_checkpoint_hashes':'PASSED','static_browser_verification':'NOT_RUN_BY_PACKAGER'}
    (output/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',default='submission/m212_20261004/package');args=a.parse_args()
    root=Path(__file__).resolve().parents[1]
    print(json.dumps(build(root,root/args.output),indent=2))
