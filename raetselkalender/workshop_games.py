"""Language, expression, boolean-circuit and sliding-tile puzzles."""
import ast
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import product,combinations_with_replacement
import random
import string

from .card_code_matches import validate_entries
from .puzzle import Puzzle
from .solver import Model,Table

WORKSHOP_MODES=('crypto','target24','circuit','pentomino','row-shift','pipes')
ALPHABET=string.ascii_uppercase
PHRASES=(
 ('Geduld','MIT RUHE UND GEDULD FINDET MAN OFT DEN RICHTIGEN WEG.'),
 ('Zusammenhalt','GEMEINSAM FINDEN WIR AUCH AUF SCHWERE FRAGEN EINE ANTWORT.'),
 ('Neugier','WER NEUGIERIG BLEIBT ENTDECKT JEDEN TAG ETWAS NEUES.'),
 ('Lernen','JEDER KLEINE SCHRITT BRINGT UNS EIN STUECK WEITER.'),
 ('Natur','ZWISCHEN DEN BAEUMEN FINDET DER WIND SEINEN EIGENEN WEG.'),
 ('Freundschaft','EIN GUTES GESPRAECH KANN EINEN GRAUEN TAG HELLER MACHEN.'),
 ('Mut','MANCHMAL BEGINNT EIN GROSSES ABENTEUER MIT EINEM KLEINEN SCHRITT.'),
 ('Logik','AUFMERKSAM HINSEHEN UND GENAU NACHDENKEN FUEHRT OFT ZUM ZIEL.'),
 ('Zeit','NICHT JEDE FRAGE BRAUCHT SOFORT EINE SCHNELLE ANTWORT.'),
 ('Kreativitaet','EINE NEUE IDEE ENTSTEHT OFT WENN WIR DIE RICHTUNG WECHSELN.'),
 ('Wissen','WER GUTE FRAGEN STELLT HAT SCHON DEN ERSTEN SCHRITT GETAN.'),
 ('Ausdauer','AUCH EIN LANGER WEG BESTEHT AUS VIELEN KLEINEN SCHRITTEN.'),
 ('Entdecken','HINTER DER NAECHSTEN ECKE KANN EINE UEBERRASCHUNG WARTEN.'),
 ('Erholung','EIN RUHIGER AUGENBLICK GIBT DEN GEDANKEN WIEDER PLATZ.'),
 ('Zuversicht','MIT EINER GUTEN IDEE UND ETWAS MUT WIRD AUS EINEM PLAN EIN ZIEL.'),
 ('Raetsel','DIE BESTE LOESUNG ZEIGT SICH OFT ERST BEIM ZWEITEN BLICK.'),
)


class CryptogramPuzzle(Puzzle):
    def decoded(self,entries):
        values=self.givens|entries
        return ''.join(ALPHABET[values[c]] if c in values else '_' if c in ALPHABET else c for c in self.view['ciphertext'])

    def check(self,entries):
        pending=validate_entries(self,entries)
        if pending:return pending,[]
        return super().check(entries)

    def certify(self):
        if len(set(self.solution.values()))!=len(self.solution) or self.decoded(self.solution)!=self.result:raise ValueError('Ungültige Buchstabenersetzung')
        self.analysis.update(unique=False,logical_solvable=False,rules_verified=True,model_role='secret_validation',
                             solution_method='german_sentence_substitution',search_branches=None)


def cryptogram(seed,difficulty):
    rng=random.Random(seed);theme,plain=rng.choice(PHRASES);encoded=list(ALPHABET)
    while True:
        rng.shuffle(encoded)
        if all(a!=b for a,b in zip(ALPHABET,encoded)):break
    substitution=dict(zip(ALPHABET,encoded));ciphertext=''.join(substitution.get(c,c) for c in plain)
    solution={substitution[c]:ALPHABET.index(c) for c in sorted(set(plain)&set(ALPHABET))}
    keys=sorted(solution);solution={k:solution[k] for k in keys}
    givens={k:solution[k] for k in rng.sample(keys,3 if difficulty=='mittel' else 1)}
    p=CryptogramPuzzle('kryptogramm','Kryptogramm',
        'Entschlüssle den deutschen Satz. Jeder Geheimschrift-Buchstabe steht immer für denselben '
        'Klartext-Buchstaben; verschiedene Zeichen stehen für verschiedene Buchstaben. Wortabstaende und '
        'Satzzeichen bleiben erhalten. AE, OE, UE und SS ersetzen Umlaute und Eszett. '
        'Trage die Buchstaben in die Schlüsseltafel ein; alle Vorkommen werden gemeinsam eingesetzt. '
        'Einige Buchstaben sind vorgegeben. Thema und Häufigkeiten helfen beim Entschlüsseln.',
        Model({k:set(range(26)) for k in keys},[Table(tuple(keys),(tuple(solution.values()),))]),solution,givens,
        dict(kind='activity',mode='crypto',ciphertext=ciphertext,theme=theme,frequencies=dict(Counter(c for c in ciphertext if c in ALPHABET))),seed,difficulty,result=plain)
    p.certify();return p


@lru_cache(maxsize=512)
def expressions24(numbers):
    """Exact subset DP; retain a witness with and without fractional intermediates."""
    numbers=tuple(numbers);states={}
    for mask in range(1,1<<4):
        out={}
        if mask.bit_count()==1:
            i=mask.bit_length()-1;out[(Fraction(numbers[i]),False)]=str(numbers[i])
        else:
            a=(mask-1)&mask
            while a:
                b=mask^a
                if a<b:
                    for (x,fx),ex in states[a].items():
                        for (y,fy),ey in states[b].items():
                            values=[(x+y,f'({ex}+{ey})'),(x*y,f'({ex}*{ey})'),(x-y,f'({ex}-{ey})'),(y-x,f'({ey}-{ex})')]
                            if y:values.append((x/y,f'({ex}/{ey})'))
                            if x:values.append((y/x,f'({ey}/{ex})'))
                            for value,expression in values:
                                fractional=fx or fy or value.denominator!=1
                                out.setdefault((value,fractional),expression)
                a=(a-1)&mask
        states[mask]=out
    final=states[15]
    return final.get((Fraction(24),False)),final.get((Fraction(24),True))


@lru_cache(maxsize=1)
def fractional24_pool():
    return tuple(numbers for numbers in combinations_with_replacement(range(1,10),4)
                 if (answers:=expressions24(numbers))[0] is None and answers[1] is not None)


def evaluate24(expression,numbers):
    if not isinstance(expression,str) or not expression.strip() or len(expression)>180:raise ValueError('Gib einen kurzen Rechenausdruck ein.')
    seen=[]
    def read(node):
        if isinstance(node,ast.Constant) and type(node.value) is int and 1<=node.value<=9:
            seen.append(node.value);return Fraction(node.value)
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            value=read(node.operand);return value if isinstance(node.op,ast.UAdd) else -value
        if not isinstance(node,ast.BinOp) or not isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            raise ValueError('Erlaubt sind die vier Zahlen, +, −, ×, / und Klammern.')
        a,b=read(node.left),read(node.right)
        if isinstance(node.op,ast.Add):return a+b
        if isinstance(node.op,ast.Sub):return a-b
        if isinstance(node.op,ast.Mult):return a*b
        if not b:raise ValueError('Durch null darf nicht geteilt werden.')
        return a/b
    try:value=read(ast.parse(expression.replace('×','*').replace('÷','/').replace(':','/').replace('−','-'),mode='eval').body)
    except (SyntaxError,RecursionError):raise ValueError('Der Ausdruck ist noch nicht vollständig oder ungültig.') from None
    if Counter(seen)!=Counter(numbers):raise ValueError('Jede der vier vorgegebenen Zahlen muss genau einmal vorkommen.')
    return value


class Target24Puzzle(Puzzle):
    def check_expression(self,expression):
        try:value=evaluate24(expression,self.view['numbers'])
        except ValueError as exc:return 'invalid',str(exc)
        return ('correct','24 erreicht!') if value==24 else ('wrong',f'Der Ausdruck ergibt {value}, gesucht ist 24.')

    def check(self,entries):
        pending=validate_entries(self,entries)
        return (pending,[]) if pending else ('correct',[])

    def certify(self):
        if self.check_expression(self.result)[0]!='correct':raise ValueError('Ungültiger 24-Nachweis')
        self.analysis.update(unique=False,logical_solvable=False,rules_verified=True,model_role='example_solution',
                             solution_method='exact_rational_subset_dp',search_branches=None)


def target24(seed,difficulty):
    rng=random.Random(seed)
    for _ in range(400):
        numbers=tuple(rng.randint(1,9) for _ in range(4)) if difficulty=='mittel' else rng.choice(fractional24_pool())
        integer,fractional=expressions24(numbers)
        expression=integer if difficulty=='mittel' else fractional
        if expression is None or difficulty=='schwer' and integer is not None:continue
        numbers=list(numbers);rng.shuffle(numbers)
        p=Target24Puzzle('vier-zahlen-ein-ziel','Vier Zahlen – ein Ziel',
            'Verwende jede der vier Zahlen genau einmal und erreiche 24. Du darfst +, −, ×, / und Klammern '
            'verwenden. Es gilt Punkt vor Strich; Brüche und negative Zwischenergebnisse sind erlaubt. '
            'Jeder mathematisch gültige Ausdruck zählt. Trage deinen Ausdruck ein und drücke „Prüfen“.',
            Model({'Ausdruck':{0}},[Table(('Ausdruck',),((0,),))]),{'Ausdruck':0},{},
            dict(kind='activity',mode='target24',numbers=numbers,target=24),seed,difficulty,result=expression)
        p.certify();return p
    raise ValueError('Keine passende 24-Aufgabe gefunden')


def gate_value(operation,values):
    if operation=='NOT':return int(not values[0])
    if operation=='AND':return int(all(values))
    if operation=='OR':return int(any(values))
    return int(values[0]!=values[1])


def circuit_values(view,inputs):
    values=inputs.copy()
    for gate in view['gates']:values[gate['id']]=gate_value(gate['op'],[values[k] for k in gate['inputs']])
    return values


class CircuitPuzzle(Puzzle):
    @property
    def editable(self):return self.view['inputs']

    def check(self,entries):
        if any(k not in self.model.domains or type(v) is not int or v not in self.model.domains[k] for k,v in entries.items()):return 'invalid',[]
        if any(k not in entries for k in self.editable):return 'incomplete',[]
        values=circuit_values(self.view,{k:entries[k] for k in self.editable})
        if any(k not in self.editable and values[k]!=v for k,v in entries.items()):return 'invalid',[]
        wrong=[k for k in self.editable if entries[k]!=self.solution[k]]
        if any(values[k]!=v for k,v in self.givens.items()):return 'wrong',wrong
        return super().check(values)


def circuits(seed,difficulty):
    rng=random.Random(seed);n=4 if difficulty=='mittel' else 6;inputs=list(ALPHABET[:n]);layers=3 if n==4 else 4
    width=3 if n==4 else 4
    for _ in range(1600):
        gates=[];previous=inputs.copy()
        for layer in range(layers):
            for trial in range(80):
                group=[]
                for row in range(width):
                    operation=rng.choice(('AND','OR','NOT','XOR'))
                    parents=rng.sample(previous,1 if operation=='NOT' else 2)
                    group.append(dict(id=f'G{len(gates)+row+1}',op=operation,inputs=parents,layer=layer,row=row))
                if {key for gate in group for key in gate['inputs']}==set(previous):break
            else:break
            gates.extend(group);previous=[g['id'] for g in group]
        if len(gates)!=width*layers or {g['op'] for g in gates}!={'AND','OR','NOT','XOR'}:continue
        view=dict(kind='activity',mode='circuit',inputs=inputs,gates=gates,layers=layers)
        keys=inputs+[g['id'] for g in gates]
        rows=tuple(tuple(circuit_values(view,dict(zip(inputs,bits))).values()) for bits in product((0,1),repeat=n))
        output_keys=[g['id'] for g in gates if g['layer']==layers-1]
        positions={key:i for i,key in enumerate(keys)}
        def matching(targets,source):
            return [row for row in rows if all(row[positions[k]]==source[positions[k]] for k in targets)]
        order=list(range(len(rows)));rng.shuffle(order)
        selected=None
        for chosen in order:
            source=rows[chosen];targets=output_keys.copy();helpers=[]
            candidates=[g['id'] for g in gates if g['layer']<layers-1];rng.shuffle(candidates)
            for key in candidates:
                if len(matching(targets,source))==1:break
                remaining=matching(targets+[key],source)
                if len(remaining)<len(matching(targets,source)):
                    targets.append(key);helpers.append(key)
                if len(helpers)>=2:break
            if len(matching(targets,source))!=1:continue
            if len(matching(helpers,source))<(4 if n==4 else 8):continue
            needed=[key for key in output_keys if len(matching([k for k in targets if k!=key],source))>1]
            if len(needed)<2:continue
            # A small intermediate measurement may help, but cannot replace
            # reasoning back from the final stage.
            if not helpers and n==4:
                for key in candidates:
                    helpful=targets+[key]
                    if len(matching([key],source))>=4 and sum(len(matching([k for k in helpful if k!=out],source))>1 for out in output_keys)>=2:
                        targets=helpful;helpers=[key];break
            selected=chosen,targets,helpers;break
        if selected is None:continue
        chosen,targets,helpers=selected;solution=dict(zip(keys,rows[chosen]));givens={k:solution[k] for k in targets}
        view.update(targets=givens.copy(),output_targets=output_keys,helper_targets=helpers)
        p=CircuitPuzzle('logikschaltungen','Logikschaltungen',
            'Bestimme die 0/1-Eingänge durch Zurückfolgern aus den vorgegebenen Ausgängen der letzten Stufe. '
            'Zusätzliche gelbe Zwischenmessungen dienen als Hilfe. AND (UND) liefert 1, wenn beide Eingänge 1 sind; '
            'OR (ODER), wenn mindestens einer 1 ist. NOT (NICHT) kehrt 0 und 1 um; '
            'XOR liefert 1, wenn genau einer der beiden Eingänge 1 ist. '
            'Klicke die Eingabefelder: leer / 0 / 1 / leer.',
            Model({k:{0,1} for k in keys},[Table(tuple(keys),rows)]),solution,givens,view,seed,difficulty)
        p.certify();p.analysis.update(rules_verified=True,model_role='accepted_answers');return p
    raise ValueError('Keine eindeutige Logikschaltung mit relevanten Endausgängen gefunden')


def slide_targets(board,n):
    if len(board)!=n*n or board.count(0)!=1:raise ValueError('Das Feld braucht genau eine Lücke')
    gap=board.index(0);r,c=divmod(gap,n)
    return tuple(rr*n+cc for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=rr<n and 0<=cc<n)


def shift_board(board,n,action):
    if type(action) is not int or action not in slide_targets(board,n):
        raise ValueError('Nur ein direkt benachbarter Stein darf in die Lücke rutschen')
    result=list(board);gap=result.index(0);result[gap],result[action]=result[action],result[gap]
    return tuple(result)


class RowShiftPuzzle(Puzzle):
    def check_moves(self,moves):
        board=tuple(self.view['initial']);n=self.view['size']
        try:
            for action in moves:board=shift_board(board,n,action)
        except (ValueError,TypeError):return 'invalid',board
        return ('correct' if board==tuple(self.view['target']) else 'wrong'),board

    def check(self,entries):
        pending=validate_entries(self,entries)
        if pending:return pending,[]
        state,board=self.check_moves([entries[k] for k in self.editable])
        return state,([] if state=='correct' else self.editable)

    def certify(self):
        if sorted(self.view['initial'])!=list(range(16)) or self.view['target']!=list(range(1,16))+[0]:raise ValueError('Ungültiges Schiebefeld')
        if self.check(self.solution)[0]!='correct':raise ValueError('Ungültiger Row-Shift-Lösungsweg')
        self.analysis.update(unique=False,logical_solvable=False,rules_verified=True,model_role='example_solution',
                             solution_method='inverse_legal_blank_scramble',search_branches=None)


def row_shift(seed,difficulty):
    rng=random.Random(seed);n=4;target=tuple(range(1,16))+(0,);count=24 if difficulty=='mittel' else 70
    for _ in range(300):
        board=target;seen={board};reverse=[]
        for step in range(count):
            choices=[(action,shift_board(board,n,action)) for action in slide_targets(board,n)]
            choices=[choice for choice in choices if choice[1] not in seen]
            if not choices:break
            previous_gap=board.index(0);action,board=rng.choice(choices);reverse.append(previous_gap);seen.add(board)
        else:
            distance=sum(abs(i//n-(value-1)//n)+abs(i%n-(value-1)%n) for i,value in enumerate(board) if value)
            if distance<(8 if difficulty=='mittel' else 18):continue
            inverse=tuple(reversed(reverse));keys=tuple(f'Zug {i+1}' for i in range(len(inverse)))
            p=RowShiftPuzzle('row-shift','Row Shift',
                'Schiebe die Zahlensteine in das rechts gezeigte Zielbild. Es gibt immer genau eine Lücke. '
                'Nur ein waagerecht oder senkrecht direkt benachbarter Stein kann durch Anklicken in diese Lücke '
                'rutschen; an seiner bisherigen Position entsteht die neue Lücke. Jede legale Zugfolge zum Ziel '
                'zählt. Rückgängig nimmt einen Schiebezug zurück.',
                Model({k:set(range(n*n)) for k in keys},[Table(keys,(inverse,))]),dict(zip(keys,inverse)),{},
                dict(kind='activity',mode='row-shift',size=n,initial=list(board),target=list(target)),seed,difficulty)
            p.certify();return p
    raise ValueError('Kein ausreichend gemischtes Schiebefeld gefunden')
