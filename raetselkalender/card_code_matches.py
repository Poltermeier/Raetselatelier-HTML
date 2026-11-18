"""Rule-checked Sets, feedback-based Superhirn and enumerated match equations."""
from collections import Counter
from functools import lru_cache
from itertools import combinations,product
import random

from .puzzle import Puzzle
from .solver import Model,Table


def valid_set(cards):
    return len(cards)==3 and len(set(cards))==3 and all(len({card[i] for card in cards}) in (1,3) for i in range(4))


def find_sets(cards):
    return tuple(group for group in combinations(range(len(cards)),3) if valid_set([cards[i] for i in group]))


def validate_entries(puzzle,entries):
    if any(k not in puzzle.model.domains or type(v) is not int or v not in puzzle.model.domains[k] for k,v in entries.items()):
        return 'invalid'
    return 'incomplete' if any(k not in entries for k in puzzle.editable) else None


class SetsPuzzle(Puzzle):
    def check_cards(self,groups):
        required=self.view['required_sets']
        if len(groups)<required:return 'incomplete'
        if len(groups)!=required:return 'invalid'
        used=set()
        for group in groups:
            if len(group)!=3 or any(type(i) is not int or not 0<=i<len(self.view['cards']) for i in group):return 'invalid'
            if len(set(group))!=3 or used.intersection(group):return 'wrong'
            if not valid_set([tuple(self.view['cards'][i]) for i in group]):return 'wrong'
            used.update(group)
        return 'correct'

    def check(self,entries):
        pending=validate_entries(self,entries)
        if pending:return pending,[]
        groups=[self.sets[entries[k]] for k in self.editable]
        state=self.check_cards(groups)
        return ('correct',[]) if state=='correct' else ('wrong',self.editable)

    def certify(self):
        self.sets=find_sets([tuple(c) for c in self.view['cards']])
        n=self.view['required_sets']
        rows=tuple((i,) for i in range(len(self.sets))) if n==1 else tuple(
            (i,j) for i in range(len(self.sets)) for j in range(len(self.sets)) if set(self.sets[i]).isdisjoint(self.sets[j]))
        if not rows or set(self.model.constraints[0].rows)!=set(rows):raise ValueError('Unvollständige Set-Prüfung')
        if self.check(self.solution)[0]!='correct':raise ValueError('Ungültige Set-Lösung')
        self.analysis.update(unique=False,logical_solvable=False,rules_verified=True,solution_method='complete_set_enumeration',
            model_role='accepted_answers',set_count=len(self.sets),search_branches=None)


def sets_puzzle(seed,difficulty):
    rng=random.Random(seed);count=12 if difficulty=='mittel' else 15;required=1 if count==12 else 2
    deck=list(product(range(3),repeat=4))
    for _ in range(500):
        cards=rng.sample(deck,count);found=find_sets(cards)
        if not 2<=len(found)<=8:continue
        rows=tuple((i,) for i in range(len(found))) if required==1 else tuple(
            (i,j) for i in range(len(found)) for j in range(len(found)) if set(found[i]).isdisjoint(found[j]))
        if not rows:continue
        keys=tuple(f'Set {i+1}' for i in range(required))
        p=SetsPuzzle('sets','Sets',
            'Drei Karten bilden ein Set, wenn jedes Merkmal für sich entweder auf allen drei Karten gleich '
            'oder auf allen drei verschieden ist. Merkmale: Anzahl (1–3), Form (Oval, Raute, Welle), '
            'Füllung (leer, gestreift, voll) und Farbe (Rot, Grün, Violett). '
            +('Finde ein Set aus den zwölf Karten.' if required==1 else
              'Finde zwei Sets aus den fünfzehn Karten. Keine Karte darf zu beiden Sets gehören.')+
            ' Klicke drei Karten an und bestätige das Set. Jede regelkonforme Auswahl zählt.',
            Model({k:set(range(len(found))) for k in keys},[Table(keys,rows)]),dict(zip(keys,rows[0])),{},
            dict(kind='activity',mode='sets',cards=[list(c) for c in cards],required_sets=required),seed,difficulty)
        p.certify();return p
    raise ValueError('Keine geeignete Set-Auslage gefunden')


def code_feedback(secret,guess):
    placed=sum(a==b for a,b in zip(secret,guess))
    total=sum((Counter(secret)&Counter(guess)).values())
    return placed,total-placed


class MastermindPuzzle(Puzzle):
    def feedback(self,guess):
        if len(guess)!=4 or any(type(c) is not int or not 0<=c<6 for c in guess):raise ValueError('Vier gültige Farben wählen')
        return code_feedback(tuple(self.solution.values()),guess)

    def certify(self):
        secret=tuple(self.solution.values())
        if not self.view['duplicates'] and len(set(secret))!=4:raise ValueError('Der mittlere Code muss vier verschiedene Farben enthalten')
        if self.feedback(secret)!=(4,0):raise ValueError('Ungültiger Superhirn-Code')
        if self.model.constraints[0].rows!=(secret,):raise ValueError('Ungültiges Code-Prüfmodell')
        self.analysis.update(unique=False,logical_solvable=False,rules_verified=True,
            solution_method='interactive_code_feedback',model_role='secret_validation',search_branches=None)


def mastermind(seed,difficulty):
    rng=random.Random(seed);duplicates=difficulty=='schwer'
    secret=tuple(rng.randrange(6) for _ in range(4)) if duplicates else tuple(rng.sample(range(6),4))
    if duplicates and len(set(secret))==4:secret=secret[:3]+(secret[0],)
    keys=tuple(f'Stelle {i+1}' for i in range(4));limit=8 if duplicates else 10
    p=MastermindPuzzle('superhirn','Superhirn',
        f'Finde den geheimen vierfarbigen Code aus sechs Farben in höchstens {limit} Versuchen. '
        +('Im geheimen Code dürfen Farben mehrfach vorkommen.' if duplicates else 'Der geheime Code hat vier verschiedene Farben.')+
        ' Nach jedem bestätigten Versuch erfährst du, wie viele Farben stimmen und wie viele davon an der richtigen '
        'Position stehen. Die Rückmeldung verrät keine einzelnen Positionen. Wähle vier Farben und drücke „Versuch abgeben“.',
        Model({k:set(range(6)) for k in keys},[Table(keys,(secret,))]),dict(zip(keys,secret)),{},
        dict(kind='activity',mode='mastermind',duplicates=duplicates,attempt_limit=limit,
             palette=['#c53b3b','#2462c0','#398242','#e6b32b','#9244ae','#db7524'],
             color_names=['Rot','Blau','Grün','Gelb','Violett','Orange']),seed,difficulty)
    p.certify();return p


# Seven segments a,b,c,d,e,f,g. Operators have a horizontal and vertical stick.
DIGIT_SEGMENTS=('abcdef','bc','abdeg','abcdg','bcfg','acdfg','acdefg','abc','abcdefg','abcdfg')
DIGIT_MASKS=tuple(sum(1<<('abcdefg'.index(s)) for s in segments) for segments in DIGIT_SEGMENTS)
MATCH_SLOTS=23


def equation_mask(a,operator,b,c):
    return DIGIT_MASKS[a]|(1<<7)|((1<<8) if operator=='+' else 0)|(DIGIT_MASKS[b]<<9)|(DIGIT_MASKS[c]<<16)


def equation_value(mask):
    try:
        a=DIGIT_MASKS.index(mask&127);b=DIGIT_MASKS.index((mask>>9)&127);c=DIGIT_MASKS.index((mask>>16)&127)
    except ValueError:return None
    if not mask&(1<<7):return None
    operator='+' if mask&(1<<8) else '-'
    return a,operator,b,c


def correct_equation(mask):
    values=equation_value(mask)
    if values is None:return False
    a,operator,b,c=values
    return (a+b if operator=='+' else a-b)==c


@lru_cache(maxsize=2)
def match_pool(moves):
    all_masks=[equation_mask(a,op,b,c) for a,b,c in product(range(10),repeat=3) for op in ('+','-')]
    correct=[mask for mask in all_masks if correct_equation(mask)]
    result=[]
    for start in all_masks:
        if correct_equation(start):continue
        distances={mask:(mask^start).bit_count()//2 for mask in correct if mask.bit_count()==start.bit_count()}
        if not distances or min(distances.values())!=moves:continue
        targets=tuple(mask for mask,depth in distances.items() if depth==moves)
        if len(targets)==1:result.append((start,targets))
    return tuple(result)


class MatchPuzzle(Puzzle):
    def check_mask(self,mask):
        if type(mask) is not int or not 0<=mask<1<<MATCH_SLOTS:return 'invalid'
        start=self.view['initial'];required=self.view['moves_required']
        if mask.bit_count()!=start.bit_count():return 'invalid'
        if (mask^start).bit_count()!=2*required:return 'wrong'
        return 'correct' if correct_equation(mask) else 'wrong'

    def check(self,entries):
        pending=validate_entries(self,entries)
        if pending:return pending,[]
        mask=sum(entries[f'Segment {i}']<<i for i in range(MATCH_SLOTS))
        return ('correct',[]) if self.check_mask(mask)=='correct' else ('wrong',self.editable)

    def certify(self):
        if (self.view['initial'],self.targets) not in match_pool(self.view['moves_required']):
            raise ValueError('Streichholz-Aufgabe besitzt keinen vollständigen Gleichungsnachweis')
        if self.check(self.solution)[0]!='correct':raise ValueError('Ungültige Streichholz-Lösung')
        rows=tuple(tuple((mask>>i)&1 for i in range(MATCH_SLOTS)) for mask in self.targets)
        if self.model.constraints[0].rows!=rows:raise ValueError('Unvollständiges Streichholz-Prüfmodell')
        self.analysis.update(unique=True,logical_solvable=False,rules_verified=True,
            solution_method='complete_equation_enumeration',minimum_moves=self.view['moves_required'],
            optimality_verified=True,model_role='accepted_answers',search_branches=None)


def matchsticks(seed,difficulty):
    moves=1 if difficulty=='mittel' else 2
    start,targets=random.Random(seed).choice(match_pool(moves))
    keys=tuple(f'Segment {i}' for i in range(MATCH_SLOTS))
    rows=tuple(tuple((mask>>i)&1 for i in range(MATCH_SLOTS)) for mask in targets)
    p=MatchPuzzle('streichholzraetsel','Streichholzrätsel',
        f'Versetze genau {moves} Streichholz'+('' if moves==1 else 'er')+
        ', sodass eine richtige Gleichung entsteht. Ziffern sowie Plus und Minus dürfen verändert werden; '
        'das Gleichheitszeichen bleibt stehen. Klicke ein Holz und dann eine freie Segmentposition an. '
        'Es müssen normale Ziffern von 0 bis 9 und ein Plus- oder Minuszeichen entstehen. Rückgängig nimmt ein Versetzen zurück.',
        Model({k:{0,1} for k in keys},[Table(keys,rows)]),dict(zip(keys,rows[0])),{},
        dict(kind='activity',mode='matches',initial=start,moves_required=moves),seed,difficulty)
    p.targets=targets;p.certify();return p
