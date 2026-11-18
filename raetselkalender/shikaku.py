"""Area-clue rectangle partitions with a complete logical cover proof."""
import random

from .extra_constraints import RectangleCover
from .generators import finish
from .solver import Model,deduce


def shikaku(seed,difficulty):
    rng=random.Random(seed)
    n,target=(8,14) if difficulty=='mittel' else (10,21)
    for _ in range(240):
        parcels=[(0,0,n,n)]
        while len(parcels)<target:
            options=[]
            for i,(r,c,h,w) in enumerate(parcels):
                for cut in range(1,h):
                    if min(cut*w,(h-cut)*w)>=2:
                        options.append((i,(r,c,cut,w),(r+cut,c,h-cut,w)))
                for cut in range(1,w):
                    if min(cut*h,(w-cut)*h)>=2:
                        options.append((i,(r,c,h,cut),(r,c+cut,h,w-cut)))
            if not options:break
            i,a,b=rng.choice(options)
            parcels[i:i+1]=[a,b]
        if len(parcels)!=target:continue
        clues=[[f'Parzelle {i+1}',r+rng.randrange(h),c+rng.randrange(w),h*w]
               for i,(r,c,h,w) in enumerate(parcels)]
        candidates,solution={},{}
        for (key,row,col,area),original in zip(clues,parcels):
            options=[]
            for h in range(1,n+1):
                if area%h:continue
                w=area//h
                if not 1<=w<=n:continue
                for r in range(max(0,row-h+1),min(row,n-h)+1):
                    for c in range(max(0,col-w+1),min(col,n-w)+1):
                        if any(other!=key and r<=rr<r+h and c<=cc<c+w for other,rr,cc,value in clues):continue
                        options.append((r,c,h,w))
            candidates[key]=options
            solution[key]=options.index(original)
        model=Model({key:set(range(len(options))) for key,options in candidates.items()},[RectangleCover(candidates,n,n)])
        if not deduce(model,trace=False).solved:continue
        return finish('shikaku','Shikaku',
            f'Zerlege das {n}×{n}-Feld vollständig in Rechtecke. Jedes Rechteck enthält genau eine '
            'Hinweiszahl. Sie nennt seinen Flächeninhalt, also die Anzahl seiner Kästchen '
            '(Breite mal Höhe). Ziehe Rechtecke mit der Maus auf; Einzelklicks schalten Kanten um.',
            model,solution,{},dict(kind='rectangles',rectangle_rule='area',rows=n,cols=n,
                                  clues=clues,candidates=candidates),seed,difficulty)
    raise ValueError('Kein eindeutig logisch lösbares Shikaku im Versuchslimit gefunden')
