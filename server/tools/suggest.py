import random
from typing import Dict, List
from ..core.models import SuggestParams, Team, TeamMember, Pokemon
from .dataset import load_pokemon
from .filters import apply_filters, bulk_score
from .synergy import compute_synergy

DATASET_PATH = "data/pokemon.csv"

def suggest_team(params: SuggestParams) -> Dict:
    pokes: List[Pokemon] = load_pokemon(DATASET_PATH)
    pool = apply_filters(pokes, params.constraints)

    # Heurística inicial:
    # - Ordena por (Speed + max(Att,Spa) + bulk/2) para mezclar velocidad, ataque y bulk
    def score(p: Pokemon) -> int:
        atk = max(p.att, p.spa)
        return p.spe + atk + (bulk_score(p) // 2)

    pool_sorted = sorted(pool, key=score, reverse=True)
    top = pool_sorted[:24] if len(pool_sorted) >= 24 else pool_sorted
    team_pokes = random.sample(top, k=6) if len(top) >= 6 else top

    team = Team(members=[
        TeamMember(name=p.name, type1=p.type1, type2=p.type2, role="balanced") for p in team_pokes
    ])
    syn = compute_synergy(team_pokes)
    return {"team": team.model_dump(), "synergy": syn.model_dump()}
