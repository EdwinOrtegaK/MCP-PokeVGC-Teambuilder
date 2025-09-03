from typing import Set

def _abilities_text(p) -> str:
    """
    Normaliza abilities a un string lowercase sin comillas, robusto a list/str/None.
    """
    ab = getattr(p, "abilities", None)
    if ab is None:
        return ""
    if isinstance(ab, list):
        txt = ",".join(map(str, ab))
    else:
        txt = str(ab)
    return txt.replace("'", "").replace('"', "").lower()

def infer_roles(p, fast_threshold: int = 90) -> Set[str]:
    roles: Set[str] = set()

    abis = _abilities_text(p)

    # Stats robustas
    spe = int(getattr(p, "spe", 0) or 0)
    att = int(getattr(p, "att", 0) or 0)
    spa = int(getattr(p, "spa", 0) or 0)
    hp  = int(getattr(p, "hp", 0) or 0)
    deff = int(getattr(p, "def_", getattr(p, "def", 0)) or 0)
    spd = int(getattr(p, "spd", 0) or 0)
    bulk = hp + deff + spd

    # Habilidades típicas de soporte / control velocidad
    if "intimidate" in abis:
        roles.update({"intimidate", "support"})
    if "prankster" in abis:
        roles.update({"speed_control", "support"})
    if "friend guard" in abis:
        roles.add("support")

    # Abusadores de clima
    if "chlorophyll" in abis:
        roles.update({"weather_abuser", "sun_abuser"})
    if "swift swim" in abis:
        roles.update({"weather_abuser", "rain_abuser"})
    if "sand rush" in abis or "sand force" in abis:
        roles.update({"weather_abuser", "sand_abuser"})
    if "slush rush" in abis or "snow warning" in abis:
        roles.update({"weather_abuser", "snow_abuser"})

    # Perfil por stats
    if spe >= fast_threshold:
        roles.add("fast")
    if att >= 100:
        roles.add("physical_attacker")
    if spa >= 100:
        roles.add("special_attacker")
    if bulk >= 360:
        roles.add("bulky")

    # Candidato Trick Room
    if spe <= 60 and bulk >= 360:
        roles.add("trick_room")

    return roles
