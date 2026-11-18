"""Window Sudoku X, orthogonal lantern clues, Hitori and treasure statements."""
from itertools import combinations,product
import random

from .generators import cell,finish,first_solution,lines,reduce_givens,sudoku_model
from .puzzle import Puzzle
from .solver import AllDifferent,Contradiction,Model,Sum,Table,deduce,restrict


WINDOWS=tuple(tuple(cell(r,c) for r in range(br,br+3) for c in range(bc,bc+3))
              for br in (1,5) for bc in (1,5))


def window_sudoku(seed,difficulty):
    rng=random.Random(seed)
    model=sudoku_model(diagonal=True)
    model.constraints.extend(AllDifferent(group) for group in WINDOWS)
    solution=first_solution(model,rng)
    givens=reduce_givens(model,solution,rng,29 if difficulty=='mittel' else 23,budget=3)
    return finish('fensterkreuz-sudoku','Fensterkreuz Sudoku X',
        'Trage 1 bis 9 in jede Zeile, jede Spalte, jeden der neun 3×3-Blöcke, beide großen Diagonalen '
        'und jedes der vier blau hinterlegten 3×3-Fenster genau einmal ein.',
        model,solution,givens,dict(kind='grid',size=9,blocks=True,diagonals=True,
                                 windows=[list(g) for g in WINDOWS]),seed,difficulty)


def lantern_sight(houses,n):
    result={}
    for key in sorted(houses):
        r,c=map(int,key.split(','));visible=[]
        for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
            rr,cc=r+dr,c+dc
            while 0<=rr<n and 0<=cc<n:
                other=cell(rr,cc)
                if other in houses:break
                visible.append(other);rr+=dr;cc+=dc
        result[key]=tuple(visible)
    return result


class SightDifference:
    """Cancel lamps shared by two visible house counts, then apply bounds.

    This is subtraction of printed equations, without trying assignments.
    """
    def __init__(self,a,b,total):
        self.terms=tuple((k,1) for k in sorted(set(a)-set(b)))+tuple((k,-1) for k in sorted(set(b)-set(a)))
        self.keys=tuple(k for k,w in self.terms);self.total=total

    def reduce(self,domains):
        bounds=[(k,w,min(w*v for v in domains[k]),max(w*v for v in domains[k])) for k,w in self.terms]
        low=sum(a for k,w,a,b in bounds);high=sum(b for k,w,a,b in bounds)
        if not low<=self.total<=high:raise Contradiction
        for k,w,a,b in bounds:
            restrict(domains,k,{v for v in domains[k] if low-a+w*v<=self.total<=high-b+w*v})


def lantern_model(labels,n):
    sight=lantern_sight(labels,n)
    free=sorted({cell(r,c) for r in range(n) for c in range(n)}-set(labels))
    groups=[(sight[k],labels[k]) for k in sight]
    constraints=[Sum(keys,total) for keys,total in groups]
    constraints.extend(SightDifference(a,b,na-nb) for (a,na),(b,nb) in combinations(groups,2) if set(a)&set(b))
    return Model({k:{0,1} for k in free},constraints)


def lanterns(seed,difficulty):
    rng=random.Random(seed);n=6 if difficulty=='mittel' else 7
    cells=[cell(r,c) for r in range(n) for c in range(n)]
    for _ in range(60000):
        houses=set(rng.sample(cells,10 if n==6 else 15))
        sight=lantern_sight(houses,n)
        free=set(cells)-houses
        if set().union(*map(set,sight.values()))!=free:continue
        lamps=set(rng.sample(sorted(free),rng.randint(9,12) if n==6 else rng.randint(12,16)))
        labels={k:sum(c in lamps for c in seen) for k,seen in sight.items()}
        if not all(labels.values()) or max(labels.values())<3:continue
        model=lantern_model(labels,n)
        if not deduce(model,trace=False).solved:continue
        solution={k:int(k in lamps) for k in sorted(free)}
        return finish('leo-laternenmann','Leo Laternenmann',
            'Setze Laternen in die freien Straßenfelder. Die Zahl auf jedem Haus nennt genau die Anzahl '
            'Laternen, die man von dort waagerecht und senkrecht sieht; diagonal wird nicht gezählt. Ein anderes Haus beendet '
            'die Sichtlinie; Laternen verdecken einander nicht. Auf Häusern stehen keine Laternen. '
            'Klicken setzt oder entfernt eine Laterne, Notizen streicht ein Feld durch. Leere Felder zählen '
            'als frei. Mit „Fertig – prüfen“ kannst du deine Anordnung prüfen.',
            model,solution,{},dict(kind='binary-symbols',mode='lanterns',size=n,labels=labels),seed,difficulty)
    raise ValueError('Kein eindeutig logisch lösbarer Laternenplan gefunden')


class ConnectedWhites:
    def __init__(self,keys,n):
        self.keys=tuple(keys)
        self.neighbors={k:tuple(other for r,c in [map(int,k.split(','))]
            for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1))
            if (other:=cell(rr,cc)) in keys) for k in keys}

    def reduce(self,domains):
        possible={k for k in self.keys if 0 in domains[k]}
        fixed={k for k in self.keys if domains[k]=={0}}
        if not possible:raise Contradiction
        def reach(start,allowed):
            seen={start};todo=[start]
            while todo:
                for other in self.neighbors[todo.pop()]:
                    if other in allowed and other not in seen:seen.add(other);todo.append(other)
            return seen
        if fixed:
            start=min(fixed);reached=reach(start,possible)
            if not fixed<=reached:raise Contradiction
            for k in possible-reached:restrict(domains,k,{1})
            # A possible articulation point joining fixed white cells stays white.
            if len(fixed)>1:
                for k in sorted(reached-fixed):
                    if not fixed<=reach(start,reached-{k}):restrict(domains,k,{0})


def hitori_model(numbers,n):
    constraints=[]
    for keys in lines(n):
        rows=[]
        for bits in product((0,1),repeat=n):
            white=[numbers[k] for k,b in zip(keys,bits) if b==0]
            if len(white)==len(set(white)) and not any(a and b for a,b in zip(bits,bits[1:])):
                rows.append(bits)
        constraints.append(Table(tuple(keys),tuple(rows)))
    return Model({k:{0,1} for k in numbers},constraints+[ConnectedWhites(numbers,n)])


def connected_white(black,n):
    white={cell(r,c) for r in range(n) for c in range(n)}-black
    if not white:return False
    seen={min(white)};todo=list(seen)
    while todo:
        r,c=map(int,todo.pop().split(','))
        for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            k=cell(rr,cc)
            if k in white and k not in seen:seen.add(k);todo.append(k)
    return seen==white


def hitori(seed,difficulty):
    rng=random.Random(seed);n=6 if difficulty=='mittel' else 8
    cells=[cell(r,c) for r in range(n) for c in range(n)]
    for _ in range(600):
        row_order=rng.sample(range(n),n);col_order=rng.sample(range(n),n);digits=rng.sample(range(1,n+1),n)
        numbers={cell(r,c):digits[(row_order[r]+col_order[c])%n] for r in range(n) for c in range(n)}
        black=set();order=cells.copy();rng.shuffle(order)
        for k in order:
            r,c=map(int,k.split(','))
            if any(cell(rr,cc) in black for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1))):continue
            if connected_white(black|{k},n):black.add(k)
            if len(black)>=round(n*n*.27):break
        for k in sorted(black):
            r,c=map(int,k.split(','))
            others=[cell(rr,cc) for rr in range(n) for cc in range(n)
                    if (rr==r or cc==c) and cell(rr,cc) not in black]
            numbers[k]=numbers[rng.choice(others)]
        model=hitori_model(numbers,n)
        if not deduce(model,trace=False).solved:continue
        solution={k:int(k in black) for k in cells}
        return finish('hitori','Hitori',
            'Schwärze Zahlen so, dass keine Zahl in einer Zeile oder Spalte mehrfach weiß bleibt. '
            'Schwarze Felder dürfen sich waagerecht und senkrecht nicht berühren. Alle weißen Felder '
            'müssen waagerecht oder senkrecht zusammenhängen. Klicken schwärzt ein Feld oder gibt es wieder frei. '
            'Notizen markiert vermutete weiße Felder mit einem Kreis. Mit „Fertig – prüfen“ prüfst du deine Markierungen.',
            model,solution,{},dict(kind='binary-symbols',mode='hitori',size=n,numbers=numbers,labels={}),seed,difficulty)
    raise ValueError('Kein Hitori mit vollständigem logischem Lösungsweg gefunden')


class TreasurePuzzle(Puzzle):
    @property
    def editable(self):return ['Schatz']

    def check(self,entries):
        if any(k not in self.model.domains or type(v) is not int or v not in self.model.domains[k] for k,v in entries.items()):return 'invalid',[]
        if 'Schatz' not in entries:return 'incomplete',[]
        from .treasure_statements import consistent_worlds
        worlds=[world for world in consistent_worlds(self.view['claims']) if world[0]==entries['Schatz']]
        if not worlds:return 'wrong',['Schatz']
        values=dict(zip(self.model.domains,worlds[0]))
        if any(values[k]!=v for k,v in entries.items()):return 'invalid',[]
        return super().check(values)


def treasure_logic(seed,difficulty):
    from .treasure_statements import consistent_worlds,claim_text
    rng=random.Random(seed);n=3 if difficulty=='mittel' else 5
    subsets=[tuple(group) for count in range(1,n) for group in combinations(range(n),count)]
    for _ in range(12000):
        claims=[]
        for i in range(n):
            others=[j for j in range(n) if j!=i];a,b=rng.sample(others,2)
            location=('loc',rng.choice(subsets))
            reference=('same',a,b) if n==5 and rng.random()<.65 else ('truth',a,rng.randrange(2))
            operator=rng.choice(('and','xor','if'))
            claims.append((operator,reference,location))
        worlds=consistent_worlds(claims)
        if len(worlds)!=1:continue
        needed=sum(len({world[0] for world in consistent_worlds(claims,omit=i)})>1 for i in range(n))
        if needed<(2 if n==3 else 4):continue
        keys=['Schatz']+[f'Aussage {i+1}' for i in range(n)]
        model=Model({'Schatz':set(range(n))}|{k:{0,1} for k in keys[1:]},[Table(tuple(keys),worlds)])
        p=TreasurePuzzle('schatzkisten-logik','Schatzkisten-Logik',
            f'Genau eine der {n} Personen lügt. Alle anderen Aussagen sind wahr. Genau eine Kiste enthält '
            'den Schatz. Aussagen über andere Personen beziehen sich auf deren ganze Sprechblase. '
            '„Gleich ehrlich“ heißt: beide ehrlich oder beide lügen. „Genau eines“ schließt aus, dass beides stimmt. '
            'Eine Folgerung ist nur falsch, wenn die Voraussetzung stimmt und die Folge nicht. '
            'Finde die Schatzkiste und klicke sie an.',model,dict(zip(keys,worlds[0])),{},
            dict(kind='treasure',size=n,claims=claims,statements=[claim_text(c) for c in claims],necessary_claims=needed),seed,difficulty)
        p.certify();return p
    raise ValueError('Keine eindeutige Schatzkisten-Aussage gefunden')
