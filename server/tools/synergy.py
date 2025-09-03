from typing import List, Dict
from ..core.models import Pokemon, SynergyReport, TypeName

# Tabla de tipos
TYPES: List[TypeName] = [
    "Normal","Fire","Water","Electric","Grass","Ice","Fighting","Poison","Ground",
    "Flying","Psychic","Bug","Rock","Ghost","Dragon","Dark","Steel","Fairy"
]

_EFFECT = {
    "Normal":   {"x2": [], "x05": ["Rock","Steel"], "x0": ["Ghost"]},
    "Fire":     {"x2": ["Grass","Ice","Bug","Steel"], "x05": ["Fire","Water","Rock","Dragon"], "x0": []},
    "Water":    {"x2": ["Fire","Ground","Rock"], "x05": ["Water","Grass","Dragon"], "x0": []},
    "Electric": {"x2": ["Water","Flying"], "x05": ["Electric","Grass","Dragon"], "x0": ["Ground"]},
    "Grass":    {"x2": ["Water","Ground","Rock"], "x05": ["Fire","Grass","Poison","Flying","Bug","Dragon","Steel"], "x0": []},
    "Ice":      {"x2": ["Grass","Ground","Flying","Dragon"], "x05": ["Fire","Water","Ice","Steel"], "x0": []},
    "Fighting": {"x2": ["Normal","Ice","Rock","Dark","Steel"], "x05": ["Poison","Flying","Psychic","Bug","Fairy"], "x0": ["Ghost"]},
    "Poison":   {"x2": ["Grass","Fairy"], "x05": ["Poison","Ground","Rock","Ghost"], "x0": ["Steel"]},
    "Ground":   {"x2": ["Fire","Electric","Poison","Rock","Steel"], "x05": ["Grass","Bug"], "x0": ["Flying"]},
    "Flying":   {"x2": ["Grass","Fighting","Bug"], "x05": ["Electric","Rock","Steel"], "x0": []},
    "Psychic":  {"x2": ["Fighting","Poison"], "x05": ["Psychic","Steel"], "x0": ["Dark"]},
    "Bug":      {"x2": ["Grass","Psychic","Dark"], "x05": ["Fire","Fighting","Poison","Flying","Ghost","Steel","Fairy","Rock"], "x0": []},
    "Rock":     {"x2": ["Fire","Ice","Flying","Bug"], "x05": ["Fighting","Ground","Steel"], "x0": []},
    "Ghost":    {"x2": ["Psychic","Ghost"], "x05": ["Dark"], "x0": ["Normal"]},
    "Dragon":   {"x2": ["Dragon"], "x05": ["Steel"], "x0": ["Fairy"]},
    "Dark":     {"x2": ["Psychic","Ghost"], "x05": ["Fighting","Dark","Fairy"], "x0": []},
    "Steel":    {"x2": ["Ice","Rock","Fairy"], "x05": ["Fire","Water","Electric","Steel"], "x0": []},
    "Fairy":    {"x2": ["Fighting","Dragon","Dark"], "x05": ["Fire","Poison","Steel"], "x0": []},
}

OFFENSIVE: Dict[TypeName, Dict[TypeName, float]] = {atk: {d: 1.0 for d in TYPES} for atk in TYPES}
for atk, eff in _EFFECT.items():
    for d in eff["x2"]:
        OFFENSIVE[atk][d] = 2.0
    for d in eff["x05"]:
        OFFENSIVE[atk][d] = 0.5
    for d in eff["x0"]:
        OFFENSIVE[atk][d] = 0.0

ALL_TYPES: List[TypeName] = TYPES[:]

def offensive_coverage_count(team: List[Pokemon]) -> Dict[TypeName, int]:
    """
    Para cada tipo DEFENSIVO, cuenta cuántos miembros del equipo pueden golpearlo a 2x
    usando STAB (type1/type2) del Pokémon.
    """
    coverage: Dict[TypeName, int] = {t: 0 for t in ALL_TYPES}
    for p in team:
        stabs = []
        if getattr(p, "type1", None):
            stabs.append(p.type1)
        if getattr(p, "type2", None):
            stabs.append(p.type2)

        for def_t in ALL_TYPES:
            ok = False
            for stab in stabs:
                if stab in OFFENSIVE and def_t in OFFENSIVE[stab]:
                    if OFFENSIVE[stab][def_t] >= 2.0:
                        ok = True
                        break
            if ok:
                coverage[def_t] += 1
    return coverage

def defensive_resistances(team: List[Pokemon]) -> Dict[TypeName, int]:
    """
    Usa los multiplicadores 'against' de cada Pokémon (mapa p.against {Tipo: mult}).
    Cuenta cuántos miembros reciben <= 0.5x de cada tipo atacante (incluye inmunidades 0x).
    """
    resist: Dict[TypeName, int] = {t: 0 for t in ALL_TYPES}
    for p in team:
        against = getattr(p, "against", {}) or {}
        for atk_t in ALL_TYPES:
            mult = against.get(atk_t, 1.0)
            if mult <= 0.5:
                resist[atk_t] += 1
    return resist

def find_holes(team: List[Pokemon]) -> List[str]:
    """
    Tipos atacantes problemáticos: promedio del multiplicador > 1.5x (umbral inicial).
    """
    holes: List[str] = []
    for atk_t in ALL_TYPES:
        vals = []
        for p in team:
            mult = (getattr(p, "against", {}) or {}).get(atk_t, 1.0)
            vals.append(mult)
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        if avg > 1.5:
            holes.append(atk_t)
    return holes

def compute_synergy(team: List[Pokemon]) -> SynergyReport:
    cov = offensive_coverage_count(team)
    res = defensive_resistances(team)
    holes = find_holes(team)
    return SynergyReport(
        coverage_offensive=cov,
        resistances_defensive=res,
        holes=holes
    )
