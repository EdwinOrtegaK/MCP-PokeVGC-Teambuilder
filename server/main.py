#!/usr/bin/env python3
"""
MCP Server para sugerencias de equipos VGC
"""
import sys
import json
import logging

from typing import Any, Dict, List, Optional
from types import SimpleNamespace
from server.tools.dataset import load_pokemon
from server.tools.filters import apply_filters, bulk_score
from server.tools.synergy import compute_synergy
from server.tools.roles import infer_roles

def _read_message(stdin_buf) -> dict | None:
    # Leer cabeceras como bytes
    headers = {}
    while True:
        line = stdin_buf.readline()
        if not line:
            return None  # EOF
        line = line.rstrip(b"\r\n")
        if line == b"":
            break
        k, v = line.split(b":", 1)
        headers[k.strip().lower()] = v.strip()

    length = int(headers.get(b"content-length", b"0"))
    if length <= 0:
        return None

    body = stdin_buf.read(length)
    return json.loads(body.decode("utf-8"))

def _write_message(stdout_buf, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    stdout_buf.write(header)
    stdout_buf.write(body)
    stdout_buf.flush()

# Configurar logging para debug
logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, ValidationError
except ImportError:
    print("Error: pydantic package not found. Install with: pip install pydantic", file=sys.stderr)
    sys.exit(1)

# Modelos de datos
class SuggestParams(BaseModel):
    format: Optional[str] = "vgc2022"
    playstyle: Optional[str] = "balanced"
    core_pokemon: Optional[List[str]] = None
    banned_pokemon: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None 

class Pokemon(BaseModel):
    name: str
    item: Optional[str] = None
    ability: Optional[str] = None
    moves: Optional[List[str]] = None
    nature: Optional[str] = None
    evs: Optional[Dict[str, int]] = None
    ivs: Optional[Dict[str, int]] = None
    level: Optional[int] = 50

class Team(BaseModel):
    pokemon: List[Pokemon]
    format: Optional[str] = "vgc2022"
    name: Optional[str] = None

# Funciones de herramientas
def suggest_team(params: SuggestParams) -> Dict[str, Any]:
    csv_path = "data/pokemon.csv"
    pokes = load_pokemon(csv_path)
    pokes = [p for p in pokes if getattr(p, "generation", 0) <= 8]

    c = params.constraints or {}
    lock_names = [n.lower() for n in c.get("lock", [])]
    include_types = set(t.lower() for t in c.get("include_types", []))
    exclude_types = set(t.lower() for t in c.get("exclude_types", []))
    require_abilities = [a.lower() for a in c.get("require_abilities", [])]
    min_speed = int(c.get("min_speed", 0))
    max_speed = c.get("max_speed")
    min_att = c.get("min_att")
    min_spa = c.get("min_spa")
    min_spdef = int(c.get("min_spdef", 0)) if c.get("min_spdef") is not None else 0
    min_bulk = int(c.get("min_bulk", 0)) if c.get("min_bulk") is not None else 0
    need_roles = set(r.lower() for r in c.get("need_roles", []))
    strategy = c.get("strategy", {}) or {}
    tr_mode = bool(strategy.get("trick_room"))
    weather = strategy.get("weather")
    want_speed_control = bool(strategy.get("speed_control"))

    # filtros ya existentes (tipos, speed, bulk, spdef)
    C = SimpleNamespace(
        include_types=list(include_types),
        exclude_types=list(exclude_types),
        min_speed=0 if tr_mode else min_speed,
        min_spdef=min_spdef,
        min_bulk=min_bulk,
        roles_needed=[]
    )

    pool = apply_filters(pokes, C)

    def _abilities_text(p) -> str:
        """Normaliza abilities a un string lowercase sin comillas, robusto a list/str/None."""
        ab = getattr(p, "abilities", None)
        if ab is None:
            return ""
        if isinstance(ab, list):
            txt = ",".join(map(str, ab))
        else:
            txt = str(ab)
        return txt.replace("'", "").replace('"', "").lower()

    # filtros por abilities, max_speed, umbrales att/spa
    def pass_extra(p):
        abis = _abilities_text(p)
        if require_abilities and not all(a.lower() in abis for a in require_abilities):
            return False
        spe = int(getattr(p, "spe", 0) or 0)
        att = int(getattr(p, "att", 0) or 0)
        spa = int(getattr(p, "spa", 0) or 0)
        if max_speed is not None and spe > int(max_speed):
            return False
        if min_att is not None and att < int(min_att):
            return False
        if min_spa is not None and spa < int(min_spa):
            return False
        return True

    pool = [p for p in pool if pass_extra(p)]

    # lock
    name_index = {p.name.lower(): p for p in pokes}
    locked = []
    for n in lock_names:
        if n in name_index:
            locked.append(name_index[n])

    # score segun estrategia
    def score(p):
        atk = max(p.att, p.spa)
        base = p.spe + atk + (bulk_score(p) // 2)
        # ajustes por estrategia
        r = infer_roles(p)
        if tr_mode:
            base = (800 - p.spe) + (bulk_score(p)) + (p.att + p.spa)//2
        if weather == "sun" and ("sun_abuser" in r): base += 120
        if weather == "rain" and ("rain_abuser" in r): base += 120
        if weather == "sand" and ("sand_abuser" in r): base += 120
        if weather == "snow" and ("snow_abuser" in r): base += 120
        if want_speed_control and ("speed_control" in r): base += 80
        # roles especificos, sube a los que aportan
        for need in need_roles:
            if need in r:
                base += 70
            # atacantes por tipo de daño
            if need == "special_attacker" and p.spa >= p.att and p.spa >= 100: base += 50
            if need == "physical_attacker" and p.att > p.spa and p.att >= 100: base += 50
            if need == "fast" and p.spe >= 100 and not tr_mode: base += 50
        return base

    # evita duplicados funcionales y arma el equipo
    banned_names = set()
    pick = list(locked)

    # elimina bloqueados del pool
    locked_names = {x.name for x in locked}
    cand = [p for p in pool if p.name not in locked_names]

    cand_sorted = sorted(cand, key=score, reverse=True)

    for p in cand_sorted:
        if len(pick) >= 6: break
        if p.name in banned_names: continue
        pick.append(p)
        banned_names.add(p.name)

    team_members = [{"name": p.name} for p in pick[:6]]
    syn = compute_synergy(pick[:6])

    return {
        "team": {"pokemon": team_members, "format": params.format, "name": "Suggested Team"},
        "synergy": syn.model_dump() if hasattr(syn, "model_dump") else syn,
        "success": True,
        "message": "Team generated with constraints"
    }

def team_to_showdown(team: Team) -> str:
    """Convierte un equipo al formato de Pokémon Showdown"""
    showdown_text = ""
    
    for pokemon in team.pokemon:
        showdown_text += f"{pokemon.name}"
        if pokemon.item:
            showdown_text += f" @ {pokemon.item}"
        showdown_text += "\n"
        
        if pokemon.ability:
            showdown_text += f"Ability: {pokemon.ability}\n"
        
        if pokemon.level and pokemon.level != 50:
            showdown_text += f"Level: {pokemon.level}\n"
        
        if pokemon.evs:
            ev_line = "EVs: " + " / ".join([f"{v} {k}" for k, v in pokemon.evs.items() if v > 0])
            showdown_text += ev_line + "\n"
        
        if pokemon.nature:
            showdown_text += f"{pokemon.nature} Nature\n"
        
        if pokemon.moves:
            for move in pokemon.moves:
                showdown_text += f"- {move}\n"
        
        showdown_text += "\n"
    
    return showdown_text.strip()

def handle_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Maneja las solicitudes MCP"""
    try:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.debug(f"Manejando método: {method} con ID: {request_id}")
        
        # Inicialización MCP
        if method == "initialize":
            # Validar que params tenga la estructura correcta
            if not isinstance(params, dict):
                logger.error("Params no es un diccionario")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid request parameters",
                        "data": "params must be an object"
                    }
                }
            
            # Verificar que se incluya protocolVersion
            if "protocolVersion" not in params:
                logger.error("Falta protocolVersion en initialize")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid request parameters",
                        "data": "protocolVersion is required"
                    }
                }
            
            client_protocol = params.get("protocolVersion")
            capabilities = params.get("capabilities", {})
            client_info = params.get("clientInfo", {})

            logger.info(f"Cliente: {client_info}, Protocolo: {client_protocol}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": client_protocol,
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "vgc-teambuilder",
                        "version": "0.1.0"
                    }
                }
            }
        
        # Completar inicialización (notification - no response needed)
        elif method == "initialized":
            logger.info("Servidor inicializado correctamente")
            return None
        
        # Listar herramientas
        elif method == "tools/list":
            if request_id is None:
                logger.error("tools/list requiere un ID")
                return {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request",
                        "data": "tools/list requires an id"
                    }
                }
            
            tools = [
                {
                    "name": "suggest_team",
                    "description": "Sugiere un equipo de Pokémon VGC basado en criterios específicos",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "description": "Formato de VGC",
                                "enum": ["vgc2020", "vgc2021", "vgc2022"],
                                "default": "vgc2022"
                            },
                            "playstyle": {
                                "type": "string",
                                "description": "Estilo de juego deseado",
                                "enum": ["aggressive", "balanced", "defensive", "trick_room"],
                                "default": "balanced"
                            },
                            "core_pokemon": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Pokémon que deben estar en el equipo"
                            },
                            "banned_pokemon": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "description": "Pokémon que no deben estar en el equipo"
                            },
                            "constraints": {
                              "type": "object",
                              "properties": {
                                "lock": { "type":"array", "items":{"type":"string"} },
                                "include_types": { "type":"array", "items":{"type":"string"} },
                                "exclude_types": { "type":"array", "items":{"type":"string"} },
                                "require_abilities": { "type":"array", "items":{"type":"string"} },
                                "min_speed": { "type":"integer", "default": 0 },
                                "max_speed": { "type":"integer" },
                                "min_att": { "type":"integer" },
                                "min_spa": { "type":"integer" },
                                "min_spdef": { "type":"integer" },
                                "min_bulk": { "type":"integer" },
                                "need_roles": {
                                  "type":"array",
                                  "items":{"type":"string"},
                                  "description":"p. ej. ['intimidate','fake_out','redirection','special_attacker','physical_attacker','fast']"
                                },
                                "strategy": {
                                  "type":"object",
                                  "properties":{
                                    "trick_room":{"type":"boolean"},
                                    "weather":{"type":"string","enum":["sun","rain","sand","snow"]},
                                    "speed_control":{"type":"boolean"}
                                  }
                                }
                              },
                              "additionalProperties": false
                            }
                        }
                    }
                },
                {
                    "name": "export_showdown",
                    "description": "Convierte un equipo al formato de Pokémon Showdown",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "team": {
                                "type": "object",
                                "description": "Equipo a convertir",
                                "properties": {
                                    "pokemon": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "item": {"type": "string"},
                                                "ability": {"type": "string"},
                                                "moves": {"type": "array", "items": {"type": "string"}},
                                                "nature": {"type": "string"},
                                                "evs": {"type": "object"},
                                                "ivs": {"type": "object"},
                                                "level": {"type": "integer"}
                                            },
                                            "required": ["name"]
                                        }
                                    }
                                },
                                "required": ["pokemon"]
                            }
                        },
                        "required": ["team"]
                    }
                },
                {
                    "name": "pool.filter",
                    "description": "Lista candidatos del pool según filtros sobre el CSV (tipos, velocidad, abilities, etc.)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "constraints": {
                                "type": "object",
                                "properties": {
                                    "include_types": {"type": "array", "items": {"type": "string"}},
                                    "exclude_types": {"type": "array", "items": {"type": "string"}},
                                    "min_speed": {"type": "integer", "default": 0},
                                    "max_speed": {"type": "integer"},
                                    "min_att": {"type": "integer"},
                                    "min_spa": {"type": "integer"},
                                    "require_abilities": {"type": "array", "items": {"type": "string"}}
                                },
                                "additionalProperties": false
                            },
                            "limit": {"type": "integer", "default": 30}
                        },
                        "required": ["constraints"]
                    }
                },
                {
                    "name": "team.synergy",
                    "description": "Analiza cobertura y resistencias de un equipo (usando el CSV)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "team": {
                                "type": "object",
                                "properties": {
                                    "pokemon": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {"name": {"type": "string"}},
                                            "required": ["name"]
                                        }
                                    }
                                },
                                "required": ["pokemon"]
                            }
                        },
                        "required": ["team"]
                    }
                },
                {
                    "name": "suggest_member",
                    "description": "Sugiere 3–5 candidatos que cumplan criterios específicos",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "min_speed": {
                                "type": "integer",
                                "description": "Velocidad mínima requerida",
                                "default": 100
                            },
                            "required_ability": {
                                "type": "string",
                                "description": "Habilidad requerida (substring match)"
                            },
                            "role": {
                                "type": "string",
                                "description": "Rol deseado",
                                "enum": ["physical_attacker","special_attacker","support","trick_room","fast","bulky"]
                            }
                        }
                    }
                }
            ]
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools}
            }
        
        # Ejecutar herramienta
        elif method == "tools/call":
            if request_id is None:
                logger.error("tools/call requiere un ID")
                return {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request",
                        "data": "tools/call requires an id"
                    }
                }
            
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.debug(f"Ejecutando herramienta: {tool_name} con argumentos: {arguments}")
            
            if tool_name == "suggest_team":
                try:
                    suggest_params = SuggestParams(**arguments)

                    allowed = {"vgc2020", "vgc2021", "vgc2022"}
                    if suggest_params.format not in allowed:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": "Invalid params",
                                "data": "Dataset soporta Gen 1–8. Usa uno de: vgc2020, vgc2021, vgc2022."
                            }
                        }

                    result = suggest_team(suggest_params)
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result, indent=2, ensure_ascii=False)
                            }]
                        }
                    }
                except Exception as e:
                    logger.error(f"Error en suggest_team: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        }
                    }
            
            elif tool_name == "export_showdown":
                try:
                    team = Team(**arguments["team"])
                    result = team_to_showdown(team)
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result
                                }
                            ]
                        }
                    }
                except Exception as e:
                    logger.error(f"Error en export_showdown: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        }
                    }
            
            elif tool_name == "pool.filter":
                # Filtros rápidos sobre el CSV con pandas (sin tocar tu motor)
                import pandas as pd
                constraints = arguments.get("constraints", {}) or {}
                limit = int(arguments.get("limit", 30))

                df = pd.read_csv("data/pokemon.csv")
                if "Generation" in df.columns:
                    df = df[df["Generation"] <= 8]

                # Normaliza
                def norm(x): return str(x).lower() if pd.notna(x) else ""
                df["Type 1"] = df["Type 1"].astype(str)
                df["Type 2"] = df["Type 2"].astype(str)
                df["Abilities"] = df["Abilities"].astype(str)

                inc = [t.lower() for t in constraints.get("include_types", [])]
                exc = [t.lower() for t in constraints.get("exclude_types", [])]
                min_speed = int(constraints.get("min_speed", 0))
                max_speed = constraints.get("max_speed")
                min_att = constraints.get("min_att")
                min_spa = constraints.get("min_spa")
                req_abis = [a.lower() for a in constraints.get("require_abilities", [])]

                mask = (df["Spe"] >= min_speed)
                if max_speed is not None:
                    mask &= (df["Spe"] <= int(max_speed))
                if min_att is not None:
                    mask &= (df["Att"] >= int(min_att))
                if min_spa is not None:
                    mask &= (df["Spa"] >= int(min_spa))
                if inc:
                    mask &= df.apply(lambda r: any(t in [str(r["Type 1"]).lower(), str(r["Type 2"]).lower()] for t in inc), axis=1)
                if exc:
                    mask &= df.apply(lambda r: all(t not in [str(r["Type 1"]).lower(), str(r["Type 2"]).lower()] for t in exc), axis=1)
                if req_abis:
                    mask &= df["Abilities"].str.lower().apply(lambda s: all(a in s for a in req_abis))

                out = df.loc[mask, ["Name","Type 1","Type 2","HP","Att","Def","Spa","Spd","Spe"]].copy()
                # bulk simple como métrica auxiliar
                out["Bulk"] = out["HP"] + out["Def"] + out["Spd"]

                # Top-N (prioriza Spe + atacante mayor)
                out["_score"] = out["Spe"] + out[["Att","Spa"]].max(axis=1) + (out["Bulk"]/2)
                out = out.sort_values("_score", ascending=False).head(limit)
                out = out.drop(columns=["_score"])

                result_rows = out.to_dict(orient="records")
                return {
                    "jsonrpc":"2.0","id":request_id,
                    "result":{"content":[{"type":"text","text":json.dumps(result_rows, ensure_ascii=False, indent=2)}]}
                }

            elif tool_name == "team.synergy":
                # Usa tu motor real para calcular sinergia
                try:
                    from server.tools.dataset import load_pokemon
                    from server.tools.synergy import compute_synergy

                    names = [x["name"] for x in arguments["team"]["pokemon"]]
                    pool = load_pokemon("data/pokemon.csv")
                    pool = [p for p in pool if getattr(p, "generation", 0) <= 8]
                    by_name = {p.name.lower(): p for p in pool}
                    selected = [by_name[n.lower()] for n in names if n and n.lower() in by_name]
                    syn = compute_synergy(selected)
                    syn_dict = syn.model_dump() if hasattr(syn, "model_dump") else syn
                    return {
                        "jsonrpc":"2.0","id":request_id,
                        "result":{"content":[{"type":"text","text":json.dumps(syn_dict, ensure_ascii=False, indent=2)}]}
                    }
                except Exception as e:
                    logger.exception(f"team.synergy failed: {e}")
                    return {
                        "jsonrpc":"2.0","id":request_id,
                        "error":{"code":-32603,"message":"Internal error","data":str(e)}
                    }

            elif tool_name == "suggest_member":
                # Sugerencias rápidas (3–5) para construir por pasos
                import pandas as pd
                min_speed = int(arguments.get("min_speed", 0))
                required_ability = arguments.get("required_ability")
                role = arguments.get("role")

                df = pd.read_csv("data/pokemon.csv")
                if "Generation" in df.columns:
                    df = df[df["Generation"] <= 8]

                df["Abilities"] = df["Abilities"].astype(str)

                mask = (df["Spe"] >= min_speed)
                if required_ability:
                    mask &= df["Abilities"].str.contains(required_ability, case=False, na=False)

                if role == "special_attacker":
                    mask &= (df["Spa"] >= 100)
                elif role == "physical_attacker":
                    mask &= (df["Att"] >= 100)
                elif role == "fast":
                    mask &= (df["Spe"] >= max(100, min_speed))
                elif role == "bulky":
                    mask &= (df["HP"] + df["Def"] + df["Spd"] >= 360)
                elif role == "support":
                    mask &= df["Abilities"].str.contains("Intimidate|Prankster|Regenerator|Friend Guard", case=False, na=False)
                elif role == "trick_room":
                    # rápido y sucio: preferir Spe <= 60 y buen bulk
                    mask &= (df["Spe"] <= 60) & ((df["HP"] + df["Def"] + df["Spd"]) >= 360)

                cand = df.loc[mask, ["Name","Type 1","Type 2","HP","Att","Def","Spa","Spd","Spe","Abilities"]].copy()
                if cand.empty:
                    sample = []
                else:
                    # puntuación simple para ordenar (puedes tunearla)
                    cand["Bulk"] = cand["HP"] + cand["Def"] + cand["Spd"]
                    cand["_score"] = cand["Spe"] + cand[["Att","Spa"]].max(axis=1) + (cand["Bulk"]/2)
                    # Para TR, invierte la velocidad
                    if role == "trick_room":
                        cand["_score"] = (800 - cand["Spe"]) + cand["Bulk"] + cand[["Att","Spa"]].max(axis=1)/2
                    cand = cand.sort_values("_score", ascending=False).head(5)
                    sample = cand.drop(columns=["_score"]).to_dict(orient="records")

                return {
                    "jsonrpc":"2.0","id":request_id,
                    "result":{"content":[{"type":"text","text":json.dumps(sample, ensure_ascii=False, indent=2)}]}
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found",
                        "data": f"Unknown tool: {tool_name}"
                    }
                }
        
        else:
            logger.warning(f"Método no reconocido: {method}")
            # Para métodos desconocidos, siempre devolver error si tiene ID
            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found",
                        "data": f"Unknown method: {method}"
                    }
                }
            else:
                return None
    
    except ValidationError as e:
        logger.error(f"Error de validación: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": str(e)
            }
        }
    
    except Exception as e:
        logger.exception(f"Error procesando solicitud: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        }

def main():
    logger.info("Iniciando servidor MCP VGC Team Builder...")
    stdin_buf = sys.stdin.buffer
    stdout_buf = sys.stdout.buffer

    while True:
        req = _read_message(stdin_buf)
        if req is None:
            break

        req_id = req.get("id")
        method = req.get("method")
        try:
            if method == "initialize":
                protocol = req.get("params", {}).get("protocolVersion", "2024-11-05")
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": protocol,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "vgc-teambuilder", "version": "0.1.0"}
                    }
                }
                _write_message(stdout_buf, resp)

            elif method == "initialized":
                # notification, no response
                continue

            elif method == "tools/list":
                tools = [  # pega aquí tus definiciones COMPLETAS (suggest_team, export_showdown, pool.filter, team.synergy, suggest_member)
                    # ... (las que ya tienes arriba)
                ]
                _write_message(stdout_buf, {"jsonrpc":"2.0","id": req_id, "result":{"tools": tools}})

            elif method == "tools/call":
                name = req.get("params", {}).get("name")
                args = req.get("params", {}).get("arguments", {}) or {}

                if name == "suggest_team":
                    result = suggest_team(SuggestParams(**args))
                    _write_message(stdout_buf, {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text": json.dumps(result, ensure_ascii=False, indent=2)}]}})

                elif name == "export_showdown":
                    team = Team(**args["team"])
                    txt = team_to_showdown(team)
                    _write_message(stdout_buf, {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text": txt}]}})

                elif name == "pool.filter":
                    # (tu implementación actual)
                    # al final: _write_message(stdout_buf, {...})
                    pass

                elif name == "team.synergy":
                    # (tu implementación actual)
                    # al final: _write_message(stdout_buf, {...})
                    pass

                elif name == "suggest_member":
                    # (tu implementación actual)
                    # al final: _write_message(stdout_buf, {...})
                    pass

                else:
                    _write_message(stdout_buf, {"jsonrpc":"2.0","id":req_id,"error":{"code":-32601,"message":"Method not found","data":f"Unknown tool: {name}"}})

            else:
                if req_id is not None:
                    _write_message(stdout_buf, {"jsonrpc":"2.0","id":req_id,"error":{"code":-32601,"message":"Method not found","data":f"Unknown method: {method}"}})

        except Exception as e:
            if req_id is not None:
                _write_message(stdout_buf, {"jsonrpc":"2.0","id":req_id,"error":{"code":-32603,"message":"Internal error","data":str(e)}})



if __name__ == "__main__":
    main()