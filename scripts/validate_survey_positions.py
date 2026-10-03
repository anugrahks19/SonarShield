"""Evaluate explicit matched reference contacts; never select a match/threshold here."""
import argparse,csv,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.runtime.sonar_geometry import geodesic


def evaluate(report,reference):
    rows=report['rows'];lookup={r['candidate_id']:r for r in rows}
    if len(lookup)!=len(rows):raise ValueError('Duplicate candidate IDs in report.')
    used=set();results=[]
    for truth in reference:
        cid=truth['candidate_id']
        if cid in used or cid not in lookup:raise ValueError('Unknown or duplicate reference candidate.')
        used.add(cid);row=lookup[cid]
        if not truth.get('reference_source') or not truth.get('reference_uncertainty_m'):raise ValueError('Measured reference source and uncertainty are required.')
        lat,lon=float(truth['latitude']),float(truth['longitude']);uncertainty=float(truth['reference_uncertainty_m'])
        if not all(math.isfinite(v) for v in (lat,lon,uncertainty)) or not -90<=lat<=90 or not -180<=lon<=180 or uncertainty<0:raise ValueError('Invalid reference coordinate/uncertainty.')
        if row.get('latitude') is None or row.get('longitude') is None:raise ValueError('Cannot validate a pixel-only contact.')
        error=geodesic().Inverse(lat,lon,row['latitude'],row['longitude'])['s12']
        measurements={}
        for target in ('width','height'):
            value=truth.get(target+'_m')
            if value not in (None,''):
                actual=float(value);estimate=row.get('estimated_'+target+'_m')
                if not math.isfinite(actual) or actual<=0 or estimate is None:raise ValueError('Invalid/missing physical reference or estimate.')
                measurements[target+'_absolute_error_m']=abs(estimate-actual)
        results.append(dict(candidate_id=cid,position_error_m=error,reference_source=truth['reference_source'],reference_uncertainty_m=uncertainty,**measurements))
    if not results:raise ValueError('No independently measured matched reference contacts supplied.')
    errors=sorted(r['position_error_m'] for r in results)
    return dict(scope='SUPPLIED_EXPLICIT_REFERENCE_MATCHES_ONLY',count=len(results),report_observation_count=len(rows),reference_coverage=len(results)/len(rows),mean_error_m=sum(errors)/len(errors),p95_error_m=errors[math.ceil(.95*len(errors))-1],maximum_error_m=max(errors),evaluated_matches=results,not_estimated=['DETECTOR_PRECISION','DETECTOR_RECALL','UNMATCHED_TARGET_COVERAGE'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);p.add_argument('references',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with a.references.open(newline='',encoding='utf-8-sig') as f:reference=list(csv.DictReader(f))
    result=evaluate(json.loads(a.report.read_text(encoding='utf-8')),reference)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8');print(json.dumps(result))
