"""Geometry-only source-label projection; never invents semantic annotations."""
import hashlib
import math

NAMES={0:'crab_pot',1:'submarine_pipeline',2:'shipwreck',3:'ghost_net',4:'mine_cylinder'}

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def parse_labels(text):
    boxes=[]
    for line in text.splitlines():
        if not line.strip():continue
        values=line.split()
        if len(values)!=5:raise ValueError('Invalid detection annotation fields.')
        c=int(values[0]);x,y,w,h=map(float,values[1:])
        if c not in NAMES or not all(math.isfinite(v) for v in (x,y,w,h)) or w<=0 or h<=0:
            raise ValueError('Invalid class or nonpositive/nonfinite box.')
        if x-w/2 < -1e-6 or y-h/2 < -1e-6 or x+w/2>1+1e-6 or y+h/2>1+1e-6:
            raise ValueError('Source box extends outside image; exclude image rather than invent a correction.')
        boxes.append((c,x,y,w,h))
    return boxes

def crop_bounds(target,width,height):
    _,x,y,w,h=target
    cx,cy,bw,bh=int(x*width),int(y*height),int(w*width),int(h*height)
    mx,my=max(int(bw*1.5),64),max(int(bh*1.5),64)
    return max(0,cx-bw//2-mx),max(0,cy-bh//2-my),min(width,cx+bw//2+mx),min(height,cy+bh//2+my)

def project(boxes,width,height,bounds):
    left,top,right,bottom=bounds;out=[]
    if right<=left or bottom<=top:raise ValueError('Empty crop.')
    for c,x,y,w,h in boxes:
        # Keep fractional original coordinates; never round a tiny positive to zero.
        x1=max(left,(x-w/2)*width);x2=min(right,(x+w/2)*width)
        y1=max(top,(y-h/2)*height);y2=min(bottom,(y+h/2)*height)
        if x2>x1 and y2>y1:
            out.append((c,((x1+x2)/2-left)/(right-left),((y1+y2)/2-top)/(bottom-top),
                        (x2-x1)/(right-left),(y2-y1)/(bottom-top)))
    return out

def text_labels(boxes):
    return ''.join(f'{c} {x:.12f} {y:.12f} {w:.12f} {h:.12f}\n' for c,x,y,w,h in boxes)
