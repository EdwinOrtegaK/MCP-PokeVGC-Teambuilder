from typing import List, Dict
from ..core.models import Pokemon, SynergyReport, TypeName

# Cobertura ofensiva mínima (se ampliara luego)
# damage multiplier for OFFENSIVE type against DEFENSIVE type
OFFENSIVE: Dict[TypeName, Dict[TypeName, float]] = {
    "Fire":   {"Grass":2,"Ice":2,"Bug":2,"Steel":2,"Fire":0.5,"Water":0.5,"Rock":0.5,"Dragon":0.5},
    "Water":  {"Fire":2,"Ground":2,"Rock":2,"Water":0.5,"Grass":0.5,"Dragon":0.5},
    "Electric":{"Water":2,"Flying":2,"Electric":0.5,"Grass":0.5,"Dragon":0.5,"Ground":0},
    "Grass":  {"Water":2,"Ground":2,"Rock":2,"Fire":0.5,"Grass":0.5,"Poison":0.5,"Flying":0.5,"Bug":0.5,"Dragon":0.5,"Steel":0.5},
    "Ice":    {"Grass":2,"Ground":2,"Flying":2,"Dragon":2,"Fire":0.5,"Water":0.5,"Ice":0.5,"Steel":0.5},
    "Fighting":{"Normal":2,"Ice":2,"Rock":2,"Dark":2,"Steel":2,"Poison":0.5,"Flying":0.5,"Psychic":0.5,"Bug":0.5,"Fairy":0.5,"Ghost":0},
    "Ground": {"Fire":2,"Electric":2,"Poison":2,"Rock":2,"Steel":2,"Grass":0.5,"Bug":0.5,"Flying":0},
    "Flying": {"Grass":2,"Fighting":2,"Bug":2,"Electric":0.5,"Rock":0.5,"Steel":0.5},
    "Psychic":{"Fighting":2,"Poison":2,"Psychic":0.5,"Steel":0.5,"Dark":0},
    "Rock":   {"Fire":2,"Ice":2,"Flying":2,"Bug":2,"Fighting":0.5,"Ground":0.5,"Steel":0.5},
    "Ghost":  {"Psychic":2,"Ghost":2,"Dark":0.5,"Normal":0},
    "Dragon": {"Dragon":2,"Steel":0.5,"Fairy":0},
    "Dark":   {"Psychic":2,"Ghost":2,"Fighting":0.5,"Dark":0.5,"Fairy":0.5},
    "Steel":  {"Ice":2,"Rock":2,"Fairy":2,"Fire":0.5,"Water":0.5,"Electric":0.5,"Steel":0.5},
    "Fairy":  {"Fighting":2,"Dragon":2,"Dark":2,"Fire":0.5,"Poison":0.5,"Steel":0.5},
    "Poison": {"Grass":2,"Fairy":2,"Poison":0.5,"Ground":0.5,"Rock":0.5,"Ghost":0.5,"Steel":0},
    "Normal": {"Rock":0.5,"Steel":0.5,"Ghost":0},
    "Bug":    {"Grass":2,"Psychic":2,"Dark":2,"Fighting":0.5,"Flying":0.5,"Poison":0.5,"Ghost":0.5,"Steel":0.5,"Fire":0.5,"Fairy":0.5},
}

ALL_TYPES: List[TypeName] = list(OFFENSIVE.keys())

def offensive_coverage_count(team: List[Pokemon]) -> Dict[TypeName, int]:
    """
    Para cada tipo DEFENSIVO, cuenta cuántos miembros del equipo
    pueden golpearlo a 2x (por STAB del miembro).
    """
    coverage: Dict[TypeName, int] = {t: 0 for t in ALL_TYPES}
    for p in team:
        stabs = [p.type1] + ([p.type2] if p.type2 else [])
        # si no conocemos el tipo en nuestra tabla parcial, lo ignoramos por ahora
        for def_t in ALL_TYPES:
            # si CUALQUIER STAB del Pokémon pega 2x al tipo defensivo → cuenta
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
    Usa los multiplicadores 'against' de cada Pokémon (tus columnas Against X).
    Cuenta cuántos miembros reciben <= 0.5x de cada tipo atacante.
    """
    resist: Dict[TypeName, int] = {t: 0 for t in ALL_TYPES}
    for p in team:
        for atk_t in ALL_TYPES:
            mult = p.against.get(atk_t, 1.0)
            if mult <= 0.5:
                resist[atk_t] += 1
    return resist

def find_holes(team: List[Pokemon]) -> List[str]:
    """
    Identifica tipos atacantes problemáticos: promedio del multiplicador > 1.5x
    (umbral inicial ajustable).
    """
    holes: List[str] = []
    for atk_t in ALL_TYPES:
        vals = []
        for p in team:
            vals.append(p.against.get(atk_t, 1.0))
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
    return SynergyReport(coverage_offensive=cov, resistances_defensive=res, holes=holes)
