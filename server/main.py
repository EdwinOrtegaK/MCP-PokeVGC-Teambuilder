#!/usr/bin/env python3
"""
MCP Server para sugerencias de equipos VGC
"""
import sys
import json
from typing import Any, Dict, List, Optional
import logging

# Configurar logging para debug
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, ValidationError
except ImportError:
    print("Error: pydantic package not found. Install with: pip install pydantic", file=sys.stderr)
    sys.exit(1)

# Modelos de datos
class SuggestParams(BaseModel):
    format: Optional[str] = "vgc2024"
    playstyle: Optional[str] = "balanced"
    core_pokemon: Optional[List[str]] = None
    banned_pokemon: Optional[List[str]] = None

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
    format: Optional[str] = "vgc2024"
    name: Optional[str] = None

# Funciones de herramientas
def suggest_team(params: SuggestParams) -> Dict[str, Any]:
    """Sugiere un equipo basado en los parámetros dados"""
    logger.debug(f"Generando equipo con parámetros: {params}")
    
    pokemon_pool = [
        {"name": "Garchomp", "item": "Life Orb", "ability": "Rough Skin"},
        {"name": "Rotom-Heat", "item": "Sitrus Berry", "ability": "Levitate"},
        {"name": "Amoonguss", "item": "Rocky Helmet", "ability": "Regenerator"},
        {"name": "Incineroar", "item": "Assault Vest", "ability": "Intimidate"},
        {"name": "Rillaboom", "item": "Miracle Seed", "ability": "Grassy Surge"},
        {"name": "Dragapult", "item": "Focus Sash", "ability": "Clear Body"},
        {"name": "Urshifu", "item": "Focus Sash", "ability": "Unseen Fist"},
        {"name": "Tornadus", "item": "Mental Herb", "ability": "Prankster"},
        {"name": "Landorus-Therian", "item": "Choice Scarf", "ability": "Intimidate"},
        {"name": "Calyrex-Shadow", "item": "Focus Sash", "ability": "As One"},
    ]
    
    selected_pokemon = []
    
    # Agregar Pokémon core
    if params.core_pokemon:
        for core in params.core_pokemon:
            core_pokemon = next((p for p in pokemon_pool if p["name"].lower() == core.lower()), None)
            if core_pokemon:
                selected_pokemon.append(core_pokemon)
    
    # Completar el equipo
    banned_names = [p.lower() for p in (params.banned_pokemon or [])]
    
    for pokemon in pokemon_pool:
        if len(selected_pokemon) >= 6:
            break
        if pokemon["name"].lower() not in banned_names and pokemon not in selected_pokemon:
            selected_pokemon.append(pokemon)
    
    # Rellenar si no hay suficientes
    while len(selected_pokemon) < 6:
        selected_pokemon.append({"name": "Ditto", "item": "Choice Scarf", "ability": "Imposter"})
    
    return {
        "team": {
            "pokemon": selected_pokemon[:6],
            "format": params.format,
            "name": f"Suggested {params.playstyle.title()} Team"
        },
        "success": True,
        "message": f"Generated {params.playstyle} team for {params.format}"
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
                    "protocolVersion": "2024-11-05",
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
                                "description": "Formato de VGC (ej: vgc2024, vgc2025)",
                                "default": "vgc2024"
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
                    result = suggest_team(suggest_params)
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, indent=2, ensure_ascii=False)
                                }
                            ]
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
    """Función principal del servidor"""
    logger.info("Iniciando servidor MCP VGC Team Builder...")
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            logger.debug(f"Línea recibida: {line}")
            
            try:
                request = json.loads(line)
                logger.debug(f"Request parseado: {request}")
                
                response = handle_request(request)
                
                # Solo enviar respuesta si no es None
                if response is not None:
                    response_json = json.dumps(response, ensure_ascii=False)
                    logger.debug(f"Enviando respuesta: {response_json}")
                    
                    print(response_json)
                    sys.stdout.flush()
                else:
                    logger.debug("Sin respuesta necesaria (notification)")
                
            except json.JSONDecodeError as e:
                logger.error(f"Error decodificando JSON: {e} - Línea: {line}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                        "data": str(e)
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
                
            except Exception as e:
                logger.exception(f"Error inesperado procesando línea: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
    
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
    except Exception as e:
        logger.exception(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()