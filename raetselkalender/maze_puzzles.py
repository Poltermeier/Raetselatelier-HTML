"""Arrow and alternating-colour chess mazes, certified by complete BFS."""
import random

from .jump_puzzle import JumpPuzzle,shortest_path_graph
from .solver import Model,Table

DIRECTIONS=((-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1))


def maze_targets(view,position):
    n=view['size']
    if position==view['goal']:return ()
    r,c=divmod(position,n)
    if view['mode']=='arrows':
        dr,dc=DIRECTIONS[view['arrows'][position]]
        return tuple(rr*n+cc for distance in range(1,n) for rr,cc in [(r+dr*distance,c+dc*distance)]
                     if 0<=rr<n and 0<=cc<n)
    piece=view['pieces'][position];kind=piece.lower();result=[]
    if kind=='n':
        vectors=((1,2),(1,-2),(-1,2),(-1,-2),(2,1),(2,-1),(-2,1),(-2,-1))
        targets=[(r+dr,c+dc) for dr,dc in vectors]
    else:
        vectors=((1,0),(-1,0),(0,1),(0,-1)) if kind=='r' else ((1,1),(1,-1),(-1,1),(-1,-1))
        targets=[(r+dr*distance,c+dc*distance) for distance in range(1,n) for dr,dc in vectors]
    for rr,cc in targets:
        if 0<=rr<n and 0<=cc<n and view['pieces'][rr*n+cc].isupper()!=piece.isupper():result.append(rr*n+cc)
    return tuple(result)


class MazePuzzle(JumpPuzzle):
    def targets(self,position):return maze_targets(self.view,position)

    def certify(self):
        v=self.view;n=v['size']
        if v['mode']=='arrows':
            if len(v['arrows'])!=n*n or any(type(d) is not int or d not in range(8) for d in v['arrows']):
                raise ValueError('Ungültiges Pfeilfeld')
        elif v['mode']=='chess-maze':
            if len(v['pieces'])!=n*n or any(p not in 'NnBbRr' for p in v['pieces']):
                raise ValueError('Ungültiges Schach-Labyrinth')
        else:raise ValueError('Unbekanntes Labyrinth')
        self.certify_path()


def make_maze(seed,difficulty,mode):
    rng=random.Random(seed);n=5
    low,high=((5,7) if difficulty=='mittel' else (8,10)) if mode=='arrows' else ((4,5) if difficulty=='mittel' else (6,8))
    for _ in range(18000):
        view=dict(kind='jump',mode=mode,size=n,start=0,goal=n*n-1,require_shortest=True)
        if mode=='arrows':view['arrows']=[rng.randrange(8) for _ in range(n*n)]
        else:view['pieces']=[rng.choice('NnBbRr') for _ in range(n*n)]
        distance,ways,route=shortest_path_graph(lambda p:maze_targets(view,p),view['start'],view['goal'])
        if view['goal'] not in distance or not low<=distance[view['goal']]<=high or ways[view['goal']]!=1:continue
        view['par']=distance[view['goal']]
        keys=tuple(f'Zug {i+1}' for i in range(view['par']))
        model=Model({key:set(range(n*n)) for key in keys},[Table(keys,(tuple(route[1:]),))])
        if mode=='arrows':
            type_id,title='pfeil-labyrinth','Pfeil-Labyrinth'
            rules=('Ziehe vom Start S zur grünen Flagge. Du darfst beliebig weit in der Richtung des '
                'Pfeils auf deinem aktuellen Feld ziehen, auch diagonal. Jeder Pfeil gilt erst ab dem Feld, '
                'auf dem du landest. Klicke ein erreichbares Feld an. Nur ein kürzester Weg zählt; die benötigte Zugzahl steht oben.')
        else:
            type_id,title='schach-labyrinth','Schach-Labyrinth'
            rules=('Erreiche die grüne Flagge. Ziehe so wie die Figur auf deinem aktuellen Feld: Springer '
                'im L, Läufer diagonal, Turm waagerecht oder senkrecht. Du musst immer auf einer Figur der '
                'anderen Farbe landen. Dazwischenliegende Figuren dürfen überquert werden; es wird keine '
                'Figur entfernt. Die Zielfigur bestimmt den nächsten Zug. Nur ein kürzester Weg zählt; die benötigte Zugzahl steht oben.')
        p=MazePuzzle(type_id,title,rules,model,dict(zip(keys,route[1:])),{},view,seed,difficulty)
        p.certify();return p
    raise ValueError('Kein Labyrinth mit passendem eindeutig kürzestem Weg gefunden')


def arrow_maze(seed,difficulty):return make_maze(seed,difficulty,'arrows')
def chess_maze(seed,difficulty):return make_maze(seed,difficulty,'chess-maze')
