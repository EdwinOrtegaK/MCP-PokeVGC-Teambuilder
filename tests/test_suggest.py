import json
from server.main import suggest_team, SuggestParams

def test_suggest_team_returns_six():
    params = SuggestParams(format="vgc2022", playstyle="balanced", constraints={"min_speed": 60})
    out = suggest_team(params)
    team = out["team"]["pokemon"]
    assert isinstance(team, list)
    assert len(team) == 6
    assert all("name" in m for m in team)
