"""Explicit truth-valued speech, including references to other speakers."""
from itertools import product


def claim_value(claim,chest,truths):
    kind=claim[0]
    if kind=='loc':return chest in claim[1]
    if kind=='truth':return bool(truths[claim[1]])==bool(claim[2])
    if kind=='same':return truths[claim[1]]==truths[claim[2]]
    a=claim_value(claim[1],chest,truths);b=claim_value(claim[2],chest,truths)
    return a and b if kind=='and' else a!=b if kind=='xor' else not a or b


def claim_text(claim):
    kind=claim[0]
    if kind=='loc':return 'Schatz in Kiste '+' oder '.join(chr(65+i) for i in claim[1])
    if kind=='truth':return chr(65+claim[1])+(' sagt die Wahrheit' if claim[2] else ' lügt')
    if kind=='same':return f'{chr(65+claim[1])} und {chr(65+claim[2])} sind gleich ehrlich'
    a,b=claim_text(claim[1]),claim_text(claim[2])
    return (f'Beides gilt:\n{a};\n{b}.' if kind=='and' else
            f'Genau eines gilt:\n{a};\n{b}.' if kind=='xor' else f'Aus »{a}« folgt:\n»{b}«.')


def consistent_worlds(claims,omit=None):
    n=len(claims)
    return tuple((chest,)+truths for chest in range(n) for truths in product((0,1),repeat=n)
                 if sum(truths)==n-1 and all(i==omit or claim_value(claim,chest,truths)==bool(truths[i])
                                            for i,claim in enumerate(claims)))
