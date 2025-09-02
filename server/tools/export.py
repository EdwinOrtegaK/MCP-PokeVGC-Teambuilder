# server/tools/export.py
from ..core.models import Team
def team_to_showdown(team: Team) -> str:
    lines = []
    for m in team.members:
        lines += [
            f"{m.name} @ Sitrus Berry",
            "Ability: ---",
            "Level: 50",
            "EVs: 4 HP / 252 Atk / 252 Spe",
            "- Move1","- Move2","- Move3","- Move4",""
        ]
    return "\n".join(lines)
