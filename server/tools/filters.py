from typing import List
from ..core.models import Pokemon, Constraints

def bulk_score(p: Pokemon) -> int:
    return p.hp + p.deff + p.spd

def apply_filters(pokes: List[Pokemon], c: Constraints) -> List[Pokemon]:
    res: List[Pokemon] = []
    for p in pokes:
        if c.include_types and not (p.type1 in c.include_types or (p.type2 and p.type2 in c.include_types)):
            continue
        if c.exclude_types and (p.type1 in c.exclude_types or (p.type2 and p.type2 in c.exclude_types)):
            continue
        if p.spe < c.min_speed:
            continue
        if p.spd < c.min_spdef:
            continue
        if bulk_score(p) < c.min_bulk:
            continue
        res.append(p)
    return res
