"""Read-only source/split/annotation audit and bounded similarity screening."""
import argparse,collections,csv,hashlib,json,math,os,re,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.training.candidate_data import sha

RASTERS={'.jpg','.jpeg','.png','.bmp','.tif','.tiff'}
PRIMARY={'crab_pot','AI4Shipwrecks','China-Offshore-SSS-AI','MILCONOMBO Side-Scan Sonar Mine Dataset','SSS_UXO'}


def role(parts):
    for p in parts:
        s=p.lower()
        if s=='test':return 'HISTORICAL_TEST'
        if s=='benchmark_bg':return 'HISTORICAL_BACKGROUND'
        if s=='val_clean':return 'HISTORICAL_DEV'
        if s in {'val','valid','validation'}:return 'HISTORICAL_VALIDATION'
        if s in {'train','training','train_additions'}:return 'HISTORICAL_TRAIN'
    return 'UNKNOWN'


def yolo_info(path,allowed):
    if not path.is_file():return {'errors':['MISSING_LABEL'],'classes':{},'empty':False,'sha256':None}
    classes=collections.Counter();errors=[];boxes=[]
    for n,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
        if not line.strip():continue
        try:
            c,x,y,w,h=line.split();c=int(c);x,y,w,h=map(float,(x,y,w,h))
            if c not in allowed or not all(math.isfinite(v) for v in [x,y,w,h]) or w<=0 or h<=0 or x-w/2< -1e-6 or y-h/2< -1e-6 or x+w/2>1+1e-6 or y+h/2>1+1e-6:raise ValueError('invalid class/geometry')
            classes[c]+=1;boxes.append([c,x,y,w,h])
        except (ValueError,OverflowError):errors.append(f'line {n}: invalid YOLO fields/class/bounds')
    return {'errors':errors,'classes':dict(classes),'boxes':boxes,'empty':not classes and not errors,'sha256':sha(path)}


def family(name):return re.sub(r'\.rf\.[^.]+','',Path(name).stem)


def image_identity(path):
    digest=sha(path)
    return digest


def decoded(path):
    try:
        with Image.open(path) as im:
            im=im.convert('RGB');w,h=im.size
            ph=hashlib.sha256(f'{w}x{h}:RGB:'.encode()+im.tobytes()).hexdigest()
            im=im.convert('L').resize((9,8),Image.Resampling.LANCZOS)
            px=list(im.getdata());bits=0
            for y in range(8):
                for x in range(8):bits=(bits<<1)|int(px[y*9+x]>px[y*9+x+1])
        return {'width':w,'height':h,'pixel_sha256':ph,'dhash64':f'{bits:016x}'}
    except (OSError,ValueError) as e:return {'decode_error':type(e).__name__}


def audit(root,output):
    root,output=Path(root).resolve(),Path(output).resolve();data=root/'datasets'
    if output.exists():raise ValueError('Fresh audit output required.')
    output.mkdir(parents=True)
    metadata={};metadata_hashes={};metadata_issues=[]
    for p in (data/'crab_pot').rglob('metadata.jsonl'):
        metadata_hashes[str(p.relative_to(root))]=sha(p)
        for n,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
            try:
                r=json.loads(line);image=(p.parent/r['file_name']).resolve()
                if not image.is_relative_to(data/'crab_pot'):raise ValueError('metadata path outside source')
                if str(image) in metadata:metadata_issues.append({'file':str(p),'line':n,'reason':'duplicate metadata image'})
                metadata[str(image)]=r
            except (ValueError,KeyError):metadata_issues.append({'file':str(p),'line':n,'reason':'malformed metadata'})
    china={}
    p=data/'China-Offshore-SSS-AI/metadata/image_manifest.csv';metadata_hashes[str(p.relative_to(root))]=sha(p)
    with p.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):china[str((data/'China-Offshore-SSS-AI'/r['release_path']).resolve())]=r
    rows=[];raw_logs=0
    for folder,dirs,files in os.walk(data):
        dirs[:]=sorted(d for d in dirs if d not in {'.git','__pycache__'})
        for name in sorted(files):
            p=Path(folder)/name;relative=p.relative_to(data);dataset=relative.parts[0]
            if p.suffix.lower()=='.xtf':raw_logs+=1;continue
            if p.suffix.lower() not in RASTERS:continue
            if dataset=='AI4Shipwrecks' and 'labels' in relative.parts:continue # masks audited as paired annotations
            row={'image':str(p),'dataset':dataset,'role':role(relative.parts[1:]),'family':family(name),
                 'label_type':'UNKNOWN','annotation_errors':[],'acquisition_group':'UNKNOWN','human_verification':'NOT_NEWLY_VERIFIED'}
            if dataset=='controlled_v8a_20261003':row['role']='CURRENT_TRAIN' if 'train' in relative.parts else 'CURRENT_DEV'
            if dataset=='crab_pot':
                row['label_type']='NATIVE_JSONL';r=metadata.get(str(p.resolve()))
                row['native_annotations']=r.get('objects') if r else None
                if not r:row['annotation_errors'].append('MISSING_JSONL_ENTRY')
            elif dataset=='China-Offshore-SSS-AI':
                row['label_type']='IMAGE_LEVEL_ONLY';r=china.get(str(p.resolve()))
                row['native_category']=r.get('original_label') if r else None
                row['standard_category']=r.get('standard_label') if r else None
                row['region']=r.get('region') if r else None
                row['annotation_status']=r.get('annotation_status') if r else None
                row['declared_image_sha256']=r.get('sha256') if r else None
                row['annotation_errors'].append('DETECTION_BOXES_UNAVAILABLE')
            elif dataset=='AI4Shipwrecks':
                parts=list(p.parts)
                if 'images' in parts:
                    parts[parts.index('images')]='labels';label=Path(*parts)
                    row['label_type']='PIXEL_MASK_REVIEW_REQUIRED';row['label']=str(label)
                    row['label_sha256']=sha(label) if label.is_file() else None
                    if not label.is_file():row['annotation_errors'].append('MISSING_MASK')
                else:row['annotation_errors'].append('SOURCE_PAIRING_UNRESOLVED')
            elif dataset=='SSS_UXO':row['annotation_errors'].append('NO_LOCAL_ANNOTATIONS')
            else:
                parts=list(p.parts)
                if 'images' in parts:parts[parts.index('images')]='labels';label=Path(*parts).with_suffix('.txt')
                else:label=p.with_suffix('.txt')
                info=yolo_info(label,{0,1} if dataset.startswith('MILCONOMBO') else set(range(5)))
                row.update(label_type='YOLO_NATIVE_MILCO_NOMBO' if dataset.startswith('MILCONOMBO') else 'YOLO_CANONICAL_OR_UNVERIFIED',label=str(label),annotation_errors=info['errors'],label_sha256=info['sha256'],label_classes=info['classes'],empty_label_not_confirmed_background=info['empty'],boxes=info.get('boxes',[]))
            rows.append(row)
    print(f'Hashing {len(rows)} raster entries across source and derived folders, excluding Git internals and paired masks.',flush=True)
    by_hash=collections.defaultdict(list)
    with ThreadPoolExecutor(max_workers=6) as pool:
        for n,(row,h) in enumerate(zip(rows,pool.map(image_identity,[Path(r['image']) for r in rows]))):
            row['sha256']=h;by_hash[h].append(row)
            if (n+1)%10000==0:print(f'Hashed {n+1}/{len(rows)}',flush=True)
    selected={h:rs[0] for h,rs in by_hash.items() if any(r['dataset'] in PRIMARY or r['dataset'] in {'controlled_v8a_20261003','drishti_sss_v3'} for r in rs)}
    identities={}
    print(f'Decoding {len(selected)} unique byte identities for pixel and bounded near-duplicate screening.',flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n,((h,r),identity) in enumerate(zip(selected.items(),pool.map(decoded,[Path(r['image']) for r in selected.values()]))):
            identities[h]=identity
            if (n+1)%1000==0:print(f'Decoded {n+1}/{len(selected)}',flush=True)
    pixels=collections.defaultdict(list);review=[];categories=collections.Counter();native_crab_boxes=0
    for row in rows:
        ident=identities.get(row['sha256'],{});row.update(ident)
        if 'pixel_sha256' in ident:pixels[ident['pixel_sha256']].append(row)
        if row.get('decode_error'):row['annotation_errors'].append('RASTER_DECODE_FAILED')
        if row['dataset']=='crab_pot' and row.get('native_annotations'):
            a=row['native_annotations'];boxes=a.get('bbox',[]);cats=a.get('category',[]);areas=a.get('area',[])
            categories.update(cats);native_crab_boxes+=len(boxes)
            if len(boxes)!=len(cats) or len(boxes)!=len(areas):row['annotation_errors'].append('NATIVE_ARRAY_LENGTH_MISMATCH')
            for b in boxes:
                if len(b)!=4 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in b):row['annotation_errors'].append('INVALID_NATIVE_BOX');continue
                x,y,w,h=b
                if w<=0 or h<=0 or x<0 or y<0 or x+w>row.get('width',0)+1e-6 or y+h>row.get('height',0)+1e-6:row['annotation_errors'].append('NATIVE_BOX_OUTSIDE_IMAGE')
            if 'Maybe-Crab-Pot' in cats:row['annotation_errors'].append('AMBIGUOUS_TARGET_REQUIRES_REVIEW')
        if row.get('declared_image_sha256') and row['declared_image_sha256']!=row['sha256']:row['annotation_errors'].append('PUBLISHER_MANIFEST_HASH_MISMATCH')
        if row['annotation_errors']:review.append({'image':row['image'],'dataset':row['dataset'],'role':row['role'],'reasons':row['annotation_errors']})
    exact=[{'sha256':h,'count':len(rs),'datasets':sorted({r['dataset'] for r in rs}),'roles':sorted({r['role'] for r in rs}),'images':[r['image'] for r in rs]} for h,rs in by_hash.items() if len(rs)>1]
    cross=[g for g in exact if len(set(g['roles'])-{'UNKNOWN'})>1]
    current_native_test=[g for g in exact if any(r['dataset']=='controlled_v8a_20261003' and r['role']=='CURRENT_TRAIN' for r in by_hash[g['sha256']]) and any(r['dataset'] in PRIMARY and r['role']=='HISTORICAL_TEST' for r in by_hash[g['sha256']])]
    pixel_cross=[{'pixel_sha256':h,'byte_identities':len({r['sha256'] for r in rs}),'roles':sorted({r['role'] for r in rs}),'images':[r['image'] for r in rs]} for h,rs in pixels.items() if len({r['sha256'] for r in rs})>1 and len({r['role'] for r in rs}-{'UNKNOWN'})>1]
    families=collections.defaultdict(list)
    for r in rows:
        if r['dataset']=='crab_pot':families[r['family']].append(r)
    family_cross=[{'family':f,'roles':sorted({r['role'] for r in rs}),'images':[r['image'] for r in rs]} for f,rs in families.items() if len({r['role'] for r in rs})>1]
    # Similarity is review screening, not semantic identity: bound repetitive-background buckets.
    near=[];bands=collections.defaultdict(list);seen_pairs=set();crowded=0;candidate_cap=20000
    for h,ident in identities.items():
        if 'dhash64' not in ident:continue
        bits=int(ident['dhash64'],16);candidates=set()
        for band in range(4):
            key=(band,(bits>>(16*band))&65535);bucket= bands[key]
            if len(bucket)>32:crowded+=1
            candidates.update(bucket[:32]);bucket.append(h)
        for other in candidates:
            pair=tuple(sorted((h,other)))
            if pair in seen_pairs:continue
            seen_pairs.add(pair);distance=(bits^int(identities[other]['dhash64'],16)).bit_count()
            if distance<=4 and len(near)<candidate_cap:
                near.append({'a':selected[h]['image'],'b':selected[other]['image'],'hamming_distance':distance,'status':'VISUAL_REVIEW_NOT_VERIFIED_DUPLICATE'})
    native_by_name=collections.defaultdict(list)
    for row in rows:
        if row['dataset']=='crab_pot':native_by_name[Path(row['image']).name].append(row)
    ambiguous_current=[]
    for row in rows:
        if row['dataset']=='controlled_v8a_20261003':
            for raw in native_by_name[Path(row['image']).name]:
                cats=(raw.get('native_annotations') or {}).get('category',[])
                if 'Maybe-Crab-Pot' in cats:
                    ambiguous_current.append({'current_image':row['image'],'role':row['role'],'source_image':raw['image'],'byte_identical':row['sha256']==raw['sha256'],'native_categories':cats,'current_classes':row.get('label_classes'), 'status':'PAIR_AND_BOX_REVIEW_REQUIRED'})
    groups=[]
    for name in sorted({r['dataset'] for r in rows}):
        rs=[r for r in rows if r['dataset']==name]
        groups.append({'dataset':name,'rasters':len(rs),'unique_byte_images':len({r['sha256'] for r in rs}),'roles':dict(collections.Counter(r['role'] for r in rs)),
                       'label_types':dict(collections.Counter(r['label_type'] for r in rs)),
                       'issue_images':sum(bool(r['annotation_errors']) for r in rs),'issue_counts':dict(collections.Counter(e for r in rs for e in r['annotation_errors'])),
                       'native_or_declared_class_boxes':dict(sum((collections.Counter(r.get('label_classes',{})) for r in rs),collections.Counter())),
                       'empty_yolo_labels_not_confirmed_background':sum(r.get('empty_label_not_confirmed_background',False) for r in rs)})
    configs=[]
    for p in (root/'models').rglob('args.yaml'):
        import yaml
        c=yaml.safe_load(p.read_text(encoding='utf-8'));configs.append({'file':str(p.relative_to(root)),'sha256':sha(p),'data':c.get('data'),'epochs':c.get('epochs')})
    report={'phase':'M2.04_SOURCE_AUDIT','status':'TECHNICAL_INVENTORY_COMPLETE_SCIENTIFIC_APPROVAL_PENDING','raster_entries':len(rows),'unique_byte_images':len(by_hash),'raw_xtf_logs':raw_logs,
            'groups':groups,'crab_native_category_counts':dict(categories),'crab_native_box_count':native_crab_boxes,'metadata_issues':metadata_issues,
            'exact_duplicate_groups':len(exact),'exact_cross_role_groups':len(cross),'decoded_pixel_cross_role_groups':len(pixel_cross),
            'current_train_exact_overlap_with_native_source_test_groups':len(current_native_test),
            'crab_filename_family_cross_role_groups':len(family_cross),'controlled_images_with_native_maybe_category_by_name':len(ambiguous_current),
            'near_candidate_pairs':len(near),'near_crowded_bucket_events':crowded,'near_candidate_limit':candidate_cap,'decoded_unique_byte_images':len(identities),
            'metadata_hashes':metadata_hashes,'training_configs':configs,
            'mapping_decisions':{'Crab-Pot':'candidate class 0 only after pairing/semantic review','Maybe-Crab-Pot':'ambiguous; neither automatic positive nor background',
               'MILCO':'candidate generic mine-like contact; cylinder shape not established','NOMBO':'non-mine source category; not automatic mine_cylinder; review project debris semantics',
               'China folder labels':'classification only; detection boxes unavailable','AI4Shipwrecks masks':'review foreground semantics and instance fragmentation before boxes','ghost_net':'synthetic scope only until real labelled evidence'},
            'license_status':{'crab_pot':'CONFLICT: local and publisher card header CC-BY-SA-4.0 vs body GPL; seek maintainer clarification',
               'drishti_revisions':'local copied README claims CC-BY-SA-4.0; component licenses and modified membership not fully verified',
               'China-Offshore-SSS-AI':'local README has no explicit license grant identified; upstream clarification needed',
               'AI4Shipwrecks':'derived README claims CC-BY-4.0; primary publisher fetch 403, not verified here',
               'MILCONOMBO':'local native license unresolved; do not substitute another mine dataset license','SSS_UXO':'prior audit claims CC-BY-NC-SA; primary terms not verified here'},
            'ready_for_reviewed_training':False,'training_calls':0,'inference_calls':0,
            'limits':['Exact cross-role groups include historical aliases; counts do not all represent independent leakage.',
               'Decoded pixel and near screening covers primary sources plus controlled/Drishti V3 unique byte images; other revisions are byte-indexed only.',
               'Near screening uses dhash bands with bounded candidates; it cannot certify absence of near duplicates.',
               'Filename families/years/regions are proxies, not verified acquisition identities.',
               'Historical training/selection and upstream pretraining overlap are not fully known.',
               'No annotations, dataset files, splits or model parameters changed.']}
    for name,value in [('summary.json',report),('inventory.json',rows),('exact-duplicate-groups.json',exact),('current-train-native-test-overlaps.json',current_native_test),('decoded-cross-role.json',pixel_cross),('crab-family-cross-role.json',family_cross),('near-review-candidates.json',near),('annotation-review-queue.json',review),('ambiguous-crab-current-pairs.json',ambiguous_current)]:
        (output/name).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['raster_entries','unique_byte_images','exact_cross_role_groups','decoded_pixel_cross_role_groups','crab_filename_family_cross_role_groups','crab_native_category_counts','controlled_images_with_native_maybe_category_by_name','near_candidate_pairs','ready_for_reviewed_training']},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit(a.root,a.output)
