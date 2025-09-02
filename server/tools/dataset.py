import pandas as pd
from typing import List, Dict
from ..core.models import Pokemon, TypeName

AGAINST_PREFIX = "Against "

# Asegura el set de tipos que esperamos encontrar
ALL_TYPES: List[TypeName] = [
    "Normal","Fire","Water","Electric","Grass","Ice","Fighting","Poison","Ground","Flying",
    "Psychic","Bug","Rock","Ghost","Dragon","Dark","Steel","Fairy"
]

def _parse_abilities(val) -> List[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val]
    if pd.isna(val):
        return []
    s = str(val).strip()
    # separadores comunes
    if s.startswith("[") and s.endswith("]"):
        # intentar eval simple y seguro
        s = s[1:-1]
    for sep in [";", ",", "/", "|"]:
        if sep in s:
            return [x.strip() for x in s.split(sep) if x.strip()]
    return [s] if s else []

def load_pokemon_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # normaliza NaN en "Type 2"
    if "Type 2" in df.columns:
        df["Type 2"] = df["Type 2"].where(pd.notna(df["Type 2"]), None)
    # parse abilities
    if "Abilities" in df.columns:
        df["Abilities"] = df["Abilities"].apply(_parse_abilities)
    return df

def _row_against_map(row: pd.Series) -> Dict[TypeName, float]:
    m: Dict[TypeName, float] = {}
    for t in ALL_TYPES:
        col = f"{AGAINST_PREFIX}{t}"
        if col in row and pd.notna(row[col]):
            try:
                m[t] = float(row[col])
            except Exception:
                m[t] = 1.0
        else:
            m[t] = 1.0
    return m

def load_pokemon(path: str) -> List[Pokemon]:
    df = load_pokemon_df(path)
    pokes: List[Pokemon] = []
    for _, r in df.iterrows():
        data = r.to_dict()

        # Mapa against
        against = _row_against_map(r)
        data["against"] = against

        # Ajustar nombres que chocan con Pydantic
        try:
            p = Pokemon(**data)
        except Exception:
            minimal = {
                "Number": int(r["Number"]),
                "Name": str(r["Name"]),
                "Type 1": str(r["Type 1"]),
                "Type 2": (str(r["Type 2"]) if r.get("Type 2") is not None and pd.notna(r["Type 2"]) else None),
                "Abilities": r.get("Abilities", []),
                "HP": int(r["HP"]),
                "Att": int(r["Att"]),
                "Def": int(r["Def"]),
                "Spa": int(r["Spa"]),
                "Spd": int(r["Spd"]),
                "Spe": int(r["Spe"]),
                "against": against
            }
            p = Pokemon(**minimal)
        pokes.append(p)
    return pokes
