"""Isolated, reviewable repair of WCC R03 terminal quantifier scope.
This is a restricted serialization check, not a natural-language theorem verifier.
"""
from pathlib import Path
import re

def r03_rendering_problems(ordered, formal, family):
    errors=[]
    # Retain occurrence checks for other entries, accepting formatting whitespace.
    for row in ordered:
        if not isinstance(row,dict) or not row.get('binder'):
            continue
        binder=str(row['binder'])
        pattern=r'\s*'.join(re.escape(x) for x in re.split(r'\s+',binder.strip()))
        if not re.search(pattern,formal):
            errors.append(f'binder {binder!r} absent from formal sentence')
    if family!='WCC':
        return errors
    if not ordered or not isinstance(ordered[-1],dict):
        return errors+['missing WCC terminal quantifier']
    end=ordered[-1]
    if (end.get('kind'),end.get('binder'),end.get('domain_id'))!=('not_exists','(q,t0)','D5'):
        return errors+['WCC terminal binder must be not_exists (q,t0) in D5']
    # In this candidate grammar the terminal sentence is the whole bound body.
    # Reject loose mentions, wrong polarity, wrong domains and post-body binders.
    normalized=re.sub(r'\s+',' ',formal).strip()
    clause=re.compile(r'(?<!\w)not exists\s+\(q\s*,\s*t0\)\s+in\s+D5\s+with\s+'
                      r'gamma\(\[t0\s*,\s*T\)\)\s+subset\s+J\^-\(q\)\s+intersect\s+M\.$')
    hits=list(clause.finditer(normalized))
    if len(hits)!=1:
        errors.append('WCC terminal clause must bind the full pair before the whole visibility body')
    else:
        before=normalized[:hits[0].start()].rstrip()
        if not before.endswith(':') or not re.search(r'forall future-inextendible causal geodesics gamma.*finite affine length:$',before):
            errors.append('WCC terminal clause must be scoped under the geodesic universal quantifier')
        if re.search(r'\bnot exists\b',before):
            errors.append('unsupported extra negated existential before WCC terminal clause')
    return errors

