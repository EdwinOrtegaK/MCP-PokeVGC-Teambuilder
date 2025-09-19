# server/core/formats.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / "data"

# Denylist por formato (ya las tienes)
DENYLIST_FILES = {
    "vgc2020": DATA / "ilegal" / "vgc2020.txt",
    "vgc2021": DATA / "ilegal" / "vgc2021.txt",
    "vgc2022": DATA / "ilegal" / "vgc2022.txt",
}

# Limit of restricted items by format (gen8)
RESTRICTED_LIMIT = {
    "vgc2020": 0,  # Series 1–3
    "vgc2021": 1,  # Series 7–9
    "vgc2022": 2,  # Serie 12
}

# Restricted list (gen8) for counting quotas in 2021/2022
RESTRICTED_GEN8 = {
    "Mewtwo","Lugia","Ho-Oh","Kyogre","Groudon","Rayquaza",
    "Dialga","Palkia","Giratina","Reshiram","Zekrom","Kyurem",
    "Xerneas","Yveltal","Zygarde","Cosmog","Cosmoem",
    "Solgaleo","Lunala","Necrozma","Zacian","Zamazenta",
    "Eternatus","Calyrex Ice Rider","Calyrex Shadow Rider"
}

def _read_lines(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}

def get_denylist(fmt: str) -> set[str]:
    return _read_lines(DENYLIST_FILES.get(fmt, Path("/does/not/exist")))

def get_restricted_limit(fmt: str) -> int:
    return RESTRICTED_LIMIT.get(fmt, 0)

def is_restricted(name: str) -> bool:
    return name.strip() in RESTRICTED_GEN8
