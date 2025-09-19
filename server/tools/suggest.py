# server/tools/suggest.py
import os
import random
from pathlib import Path
from typing import Dict, List, Set
from types import SimpleNamespace

from ..core.models import SuggestParams, Team, TeamMember, Pokemon
from .dataset import load_pokemon
from .filters import apply_filters, bulk_score
from .synergy import compute_synergy

DATASET_PATH = "data/pokemon.csv"

# Restriction caps per VGC format (Gen 8 series)
FORMAT_CAP = {
    "vgc2020": 0,   # No restricteds allowed
    "vgc2021": 1,   # Max 1 restricted
    "vgc2022": 2,   # Max 2 restricteds
}

def _load_name_set(path: Path) -> Set[str]:
    """Load a text file into a set of Pokémon names (1 per line)."""
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def _deny_set_for(fmt: str) -> Set[str]:
    """Return the denylist (illegal Pokémon) for a given format."""
    return _load_name_set(Path("data/ilegal") / f"{fmt}.txt")

def _restricted_set_for(fmt: str) -> Set[str]:
    """
    Return the restricted list for a given format.
    These should be stored under data/restricted/vgcXXXX.txt.
    If the file does not exist, returns an empty set (no cap enforcement).
    """
    return _load_name_set(Path("data/restricted") / f"{fmt}.txt")

# --- extra guardrails for Gen 8 legality (automatic forms ban) ---
MEGA_PREFIXES = ("Mega ", "Mega-")  # cover "Mega Charizard X" or "Mega-Charizard-X"
OTHER_IMPOSSIBLE_FORMS_GEN8 = ("Primal ", "Primal-", "Ultra ", "Ultra-")
GEN8_FORMS_AUTO_BAN = {"Zygarde Complete", "Zygarde-Complete"} 

def _is_impossible_form_in_gen8(name: str) -> bool:
    """Return True if this is a form that doesn't exist in Gen 8 (e.g., Mega/Primal/Ultra)."""
    n = name.strip()
    if n.startswith(MEGA_PREFIXES):
        return True
    if n.startswith(OTHER_IMPOSSIBLE_FORMS_GEN8):
        return True
    if n in GEN8_FORMS_AUTO_BAN: 
        return True
    return False

def legal_suggest_team(params: SuggestParams) -> Dict:
    fmt = params.format or "vgc2022"

    # 1) Load full dataset and apply base constraints/filters
    all_pokes: List[Pokemon] = load_pokemon(DATASET_PATH)
    pool = apply_filters(all_pokes, params.constraints)

    # --- normalize constraints -> object with attributes (apply_filters expects attrs, not a dict) ---
    raw_c = getattr(params, "constraints", None)
    # soporta dict o Pydantic; si fuera BaseModel, usa model_dump()
    if hasattr(raw_c, "model_dump"):
        raw_c = raw_c.model_dump()
    raw_c = raw_c or {}

    # si te interesa respetar trick room aquí (min_speed=0 en TR):
    strategy = (raw_c.get("strategy") or {})
    tr_mode = bool(strategy.get("trick_room"))

    C = SimpleNamespace(
        include_types=[t.lower() for t in raw_c.get("include_types", [])],
        exclude_types=[t.lower() for t in raw_c.get("exclude_types", [])],
        min_speed=0 if tr_mode else int(raw_c.get("min_speed", 0) or 0),
        min_spdef=int(raw_c.get("min_spdef", 0) or 0),
        min_bulk=int(raw_c.get("min_bulk", 0) or 0),
        roles_needed=[]
    )
    pool = apply_filters(all_pokes, C)

    # 2) Compose denylist: file-based + automatic Gen8-impossible forms
    base_deny: Set[str] = _deny_set_for(fmt)
    auto_forms_block: Set[str] = {p.name for p in all_pokes if _is_impossible_form_in_gen8(p.name)}
    deny: Set[str] = base_deny | auto_forms_block

    # 3) Remove illegal Pokémon for this format
    pool = [p for p in pool if p.name not in deny]

    if len(pool) < 6:
        # Fallback: if too few remain, reload full dataset without illegals
        pool = [p for p in all_pokes if p.name not in deny]

    # 4) Scoring heuristic:
    #    Speed + best offensive stat (Att/SpA) + half of bulk
    def score(p: Pokemon) -> int:
        atk = max(p.att, p.spa)
        return p.spe + atk + (bulk_score(p) // 2)

    pool_sorted = sorted(pool, key=score, reverse=True)
    top = pool_sorted[:24] if len(pool_sorted) >= 24 else pool_sorted

    # 5) Draft initial team of 6 from the top pool
    team_pokes = random.sample(top, k=6) if len(top) >= 6 else top[:6]

    # 6) Enforce restricted cap if needed (vgc2021/2022)
    cap = FORMAT_CAP.get(fmt, 0)
    if cap > 0:
        restricted = _restricted_set_for(fmt)
        if restricted:  # only enforce if file exists
            current_restricted = [p for p in team_pokes if p.name in restricted]
            if len(current_restricted) > cap:
                # Replace excess restricted mons with non-restricted candidates
                non_restricted_candidates = [
                    p for p in top
                    if p.name not in restricted and p not in team_pokes
                ]
                i = 0
                while len(current_restricted) > cap and i < len(non_restricted_candidates):
                    to_remove = current_restricted.pop()  # drop last restricted
                    idx = team_pokes.index(to_remove)
                    team_pokes[idx] = non_restricted_candidates[i]
                    i += 1

    # 7) Pack result
    team = Team(members=[
        TeamMember(name=p.name, type1=p.type1, type2=p.type2, role="balanced")
        for p in team_pokes
    ])
    syn = compute_synergy(team_pokes)
    return {"team": team.model_dump(), "synergy": syn.model_dump()}