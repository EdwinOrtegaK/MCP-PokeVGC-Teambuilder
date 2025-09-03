from server.tools.dataset import load_pokemon
from server.tools.synergy import compute_synergy

def test_synergy_basic_non_empty():
    pool = load_pokemon("data/pokemon.csv")
    team = pool[:3]
    syn = compute_synergy(team)
    assert hasattr(syn, "coverage_offensive") or "coverage_offensive" in getattr(syn, "__dict__", {})
    assert hasattr(syn, "resistances_defensive") or "resistances_defensive" in getattr(syn, "__dict__", {})
