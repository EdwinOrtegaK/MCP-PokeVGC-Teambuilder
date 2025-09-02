# server/tools/roles.py
from typing import Dict, Set

FAKE_OUT = {"Incineroar","Rillaboom","Iron Hands","Raichu","Weavile","Mienshao","Medicham","Scrafty","Ambipom","Kangaskhan"}
REDIRECTION = {"Amoonguss","Togekiss","Clefairy","Clefable","Indeedee","Indeedee-F"}
SPEED_CONTROL_SPECIES = {"Tornadus","Cresselia","Farigiraf","Murkrow","Whimsicott","Icy Wind"}
WEATHER_SETTERS = {
    "sun": {"Torkoal","Ninetales"}, "rain":{"Pelipper","Politoed"},
    "sand":{"Tyranitar","Hippowdon"}, "snow":{"Abomasnow","Ninetales-Alola"}
}

def infer_roles(p, fast_threshold: int = 90) -> Set[str]:
    roles = set()

    abis = (p.abilities or "").lower()

    if p.spe >= fast_threshold:
        roles.add("fast")
    if p.spa >= p.att and p.spa >= 100:
        roles.add("special_attacker")
    if p.att > p.spa and p.att >= 100:
        roles.add("physical_attacker")
    if "intimidate" in abis:
        roles.add("intimidate")

    if any(x in abis for x in ["chlorophyll"]): roles.add("sun_abuser")
    if any(x in abis for x in ["swift swim"]): roles.add("rain_abuser")
    if any(x in abis for x in ["sand rush"]): roles.add("sand_abuser")
    if any(x in abis for x in ["slush rush"]): roles.add("snow_abuser")

    if p.name in FAKE_OUT: roles.add("fake_out")
    if p.name in REDIRECTION: roles.add("redirection")
    if p.name in SPEED_CONTROL_SPECIES: roles.add("speed_control")
    return roles
