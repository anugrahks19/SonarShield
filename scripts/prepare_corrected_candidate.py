"""Prepare a NEW exploratory revision; existing data/runs remain untouched."""
import argparse,ast,collections,csv,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import yaml
from ai.training.candidate_data import NAMES,sha,parse_labels,crop_bounds,project,text_labels


def decoded_hash(path):
    image=cv2.imread(str(path),cv2.IMREAD_COLOR)
    if image is None:raise ValueError('Image cannot be decoded.')
    return hashlib.sha256(str(image.shape).encode()+image.tobytes()).hexdigest()


def prepare(root,output):
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Use a new dataset directory; never overwrite a revision.')
    source=root/'datasets/drishti_sss_v3';lineage=root/'datasets/V8-A-TARGETED-HARD-POSITIVE/v8_a_crop_lineage.csv'
    exclusions=[];records=[];protected=set();protected_pixels=set()
    # Previously used TEST/background remain regression-only, never fresh final evidence.
    for role in ['test','benchmark_bg']:
        for p in sorted((source/role/'images').glob('*')):
            if p.suffix.lower() in {'.jpg','.jpeg','.png'}:
                protected.add(sha(p));protected_pixels.add(decoded_hash(p))
    for split in ['train','val']:
        (output/'images'/split).mkdir(parents=True);(output/'labels'/split).mkdir(parents=True)
    counts=collections.Counter();seen=set();seen_pixels=set();parents={}
    for role,original in [('DEV','val_clean'),('TRAIN','train')]:
        target='val' if role=='DEV' else 'train'
        for image in sorted((source/original/'images').glob('*')):
            if image.suffix.lower() not in {'.jpg','.jpeg','.png'}:continue
            label=source/original/'labels'/image.with_suffix('.txt').name
            try:
                raw=label.read_text(encoding='utf-8');boxes=parse_labels(raw)
                image_sha=sha(image);pixels=decoded_hash(image)
                if image_sha in protected or pixels in protected_pixels:raise ValueError('Exact byte/pixel overlap with historical TEST/background.')
                if image_sha in seen or pixels in seen_pixels:raise ValueError('Duplicate image or cross-DEV overlap.')
            except (ValueError,OSError) as exc:
                exclusions.append({'image':str(image.relative_to(root)),'role':role,'reason':str(exc)});continue
            destination=output/'images'/target/image.name;annotation=output/'labels'/target/image.with_suffix('.txt').name
            shutil.copy2(image,destination);annotation.write_text(raw,encoding='utf-8')
            records.append({'image':str(destination),'label':str(annotation),'split':role,'image_sha256':image_sha,
                'label_sha256':sha(annotation),'decoded_sha256':pixels,'parent_sha256':image_sha,
                'source_image':str(image),'source_label':str(label),'source_label_sha256':sha(label),
                'annotation_basis':'INHERITED_SOURCE_LABEL_NOT_NEW_EXPERT_VERIFICATION','acquisition_group':'UNKNOWN',
                'box_count':len(boxes),'background_verification':'INHERITED_ONLY' if not boxes else None})
            seen.add(image_sha);seen_pixels.add(pixels);counts[role]+=1
            if role=='TRAIN':parents[image.name]=(image,boxes,image_sha)
        print(f'{role}: {counts[role]} accepted source images',flush=True)
    crop_count=0
    with lineage.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            try:
                if Path(row['crop_id']).name!=row['crop_id']:raise ValueError('Invalid crop path.')
                parent=parents.get(row['source_image_id'])
                if not parent:raise ValueError('Parent excluded or not in TRAIN.')
                path,boxes,parent_sha=parent
                if parent_sha!=row['source_image_sha256']:raise ValueError('Parent hash changed.')
                gt=int(row['source_gt_id'].rsplit('_gt_',1)[1]);target=boxes[gt]
                expected=list(map(float,ast.literal_eval(row['gt_bbox'])))
                if any(abs(a-b)>1e-8 for a,b in zip(target[1:],expected)) or len(expected)!=4 or NAMES[target[0]]!=row['class']:
                    raise ValueError('Selected source GT/class does not match parent annotation.')
                image=cv2.imread(str(path));height,width=image.shape[:2];bounds=crop_bounds(target,width,height)
                derived=project(boxes,width,height,bounds)
                if not derived or not any(b[0]==target[0] for b in derived):raise ValueError('No retained target.')
                # All visible source objects, not only the selected hard positive.
                label_text=text_labels(derived);parse_labels(label_text)
                left,top,right,bottom=bounds;roi=image[top:bottom,left:right]
                name=row['crop_id'];destination=output/'images/train'/name
                if destination.exists():raise ValueError('Duplicate crop filename.')
                ok,encoded=cv2.imencode('.jpg',roi)
                if not ok:raise ValueError('Crop encoding failed.')
                blob=encoded.tobytes();image_sha=hashlib.sha256(blob).hexdigest()
                pixels=hashlib.sha256(str(roi.shape).encode()+cv2.imdecode(encoded,cv2.IMREAD_COLOR).tobytes()).hexdigest()
                if image_sha in seen or pixels in seen_pixels or image_sha in protected or pixels in protected_pixels:
                    raise ValueError('Duplicate or protected crop image.')
                destination.write_bytes(blob);annotation=output/'labels/train'/Path(name).with_suffix('.txt').name
                annotation.write_text(label_text,encoding='utf-8')
                records.append({'image':str(destination),'label':str(annotation),'split':'TRAIN','image_sha256':image_sha,
                    'label_sha256':sha(annotation),'decoded_sha256':pixels,'parent_sha256':parent_sha,
                    'source_image':str(path),'source_label':str(source/'train/labels'/path.with_suffix('.txt').name),
                    'source_label_sha256':sha(source/'train/labels'/path.with_suffix('.txt').name),
                    'annotation_basis':'SOURCE_GT_GEOMETRY_DERIVED_NOT_NEW_EXPERT_VERIFICATION','acquisition_group':'UNKNOWN',
                    'crop_bounds_xyxy':list(bounds),'box_count':len(derived),'background_verification':None})
                seen.add(image_sha);seen_pixels.add(pixels);crop_count+=1
            except (ValueError,IndexError,KeyError,OSError) as exc:
                exclusions.append({'image':row['crop_id'],'role':'TRAIN_CROP','reason':str(exc)})
    config={'path':str(output),'train':'images/train','val':'images/val','names':NAMES,'nc':5,'task':'detect'}
    (output/'data.yaml').write_text(yaml.safe_dump(config,sort_keys=False),encoding='utf-8')
    summary={'purpose':'CONTROLLED_EXPLORATORY_TRAINING_NOT_FINAL_ACCURACY_CERTIFICATION','version':1,
        'source_counts':dict(counts),'corrected_positive_crops':crop_count,'total_train':counts['TRAIN']+crop_count,
        'dev_images':counts['DEV'],'excluded':len(exclusions),'unknown_site_mission_provenance':True,
        'near_duplicate_review_complete':False,'expert_annotation_certification':False,'xtf_included':False,
        'test_or_calib_used_for_training_validation':False,'records':records,
        'source_lineage_sha256':sha(lineage),'weights_sha256':sha(root/'models/v6/detector_v6_p2_sss/weights/best.pt')}
    (output/'manifest.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    (output/'exclusions.json').write_text(json.dumps(exclusions,indent=2),encoding='utf-8')
    (output/'READY.json').write_text(json.dumps({'manifest_sha256':sha(output/'manifest.json'),'data_sha256':sha(output/'data.yaml'),
        'scope':summary['purpose']}),encoding='utf-8')
    return {k:v for k,v in summary.items() if k!='records'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.root,a.output),indent=2))
