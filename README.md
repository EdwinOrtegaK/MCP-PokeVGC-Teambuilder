# MCP-PokeVGC-Teambuilder

Servidor **MCP** para construir y analizar equipos de Pokémon VGC (Video Game Championships).  
Este proyecto fue diseñado como un **MVP (Minimum Viable Product)** que permite:

- Sugerir equipos completos basados en restricciones (tipos, velocidad, habilidades, roles, etc.).
- Sugerir miembros individuales para completar un equipo.
- Exportar equipos al formato de Pokémon Showdown.
- Analizar sinergias ofensivas y defensivas de un equipo.
- Filtrar rápidamente el pool de Pokémon desde el dataset.

## 🚀 Instalación

1. Clona el repositorio:

```bash
git clone <repository-url>
cd MCP-PokeVGC-Teambuilder
```

2. Crea y activa un entorno virtual:

```bash
python -m venv .venv
# En Linux/macOS
source .venv/bin/activate
# En Windows (PowerShell)
.venv\Scripts\activate
```

3. Instala dependencias:

```bash
pip install -r requirements.txt
```

## ▶️ Ejecución del servidor MCP

Ejecuta el servidor directamente con Python:

```bash
python -m server.main
```

También puedes configurarlo como un **MCP Server** en clientes compatibles (ej. Claude Desktop), apuntando al binario de Python en tu `.venv` y con argumentos:

```
-u -m server.main
```

Cuando está corriendo, el servidor escucha solicitudes MCP vía **stdin/stdout**.

## 📂 Estructura del proyecto

```
MCP-PokeVGC-Teambuilder/
├── data/
│   └── pokemon.csv          # Dataset principal (Gen 1–8)
├── server/
│   ├── core/
│   │   └── models.py        # Definición de objetos Pokémon y SynergyReport
│   ├── tools/
│   │   ├── dataset.py       # Carga y normalización del dataset
│   │   ├── filters.py       # Filtros rápidos (velocidad, tipos, etc.)
│   │   ├── roles.py         # Inferencia de roles por stats/abilities
│   │   ├── synergy.py       # Cobertura ofensiva y resistencias
│   │   └── export.py        # Exportar equipos a Showdown
│   ├── schemas/             # Esquemas JSON para herramientas MCP
│   └── main.py              # Servidor MCP principal
├── tests/                   # Pruebas unitarias con pytest
└── README.md
```

## 🛠 Herramientas MCP disponibles

El servidor expone varias herramientas que pueden ser invocadas vía `tools/call`:

### 1. `suggest_team`
Sugiere un equipo completo (6 Pokémon).

**Ejemplo de argumentos:**

```json
{
  "format": "vgc2022",
  "playstyle": "balanced",
  "constraints": {
    "min_speed": 90,
    "need_roles": ["special_attacker","fast"],
    "strategy": { "trick_room": false }
  }
}
```

### 2. `export_showdown`
Convierte un equipo al formato de Pokémon Showdown.

```json
{
  "team": {
    "pokemon": [
      {"name": "Garchomp", "item": "Life Orb", "ability": "Rough Skin", "moves": ["Earthquake","Rock Slide"]},
      {"name": "Rotom-Heat", "item": "Sitrus Berry", "ability": "Levitate"}
    ]
  }
}
```

### 3. `pool.filter`
Devuelve un listado de candidatos según filtros simples.

**Ejemplo:**

```json
{
  "constraints": {
    "include_types": ["dragon"],
    "min_speed": 100,
    "require_abilities": ["Levitate"]
  },
  "limit": 10
}
```

### 4. `team.synergy`
Analiza la sinergia de un equipo (cobertura ofensiva y resistencias).

**Ejemplo:**

```json
{
  "team": {
    "pokemon": [
      {"name": "Garchomp"},
      {"name": "Rotom-Heat"},
      {"name": "Amoonguss"}
    ]
  }
}
```

### 5. `suggest_member`
Sugiere 3–5 candidatos que cumplan criterios.

**Ejemplo:**

```json
{
  "min_speed": 120,
  "role": "fast",
  "required_ability": "Levitate"
}
```

## ✅ Pruebas

El proyecto incluye **tests automáticos** con `pytest`:

```bash
python -m pytest -q
```

Pruebas incluidas:

- `test_dataset.py`: valida carga correcta de `pokemon.csv`.
- `test_synergy.py`: revisa cobertura y resistencias con equipos toy.
- `test_suggest.py`: asegura que `suggest_team` devuelve siempre 6 miembros.

## 📊 Dataset

El dataset usado es `data/pokemon.csv`, derivado de Smogon y Kaggle.  
Incluye columnas:

- **Name, Type 1, Type 2**
- **HP, Att, Def, Spa, Spd, Spe**
- **Abilities**
- **Against_X** para los 18 tipos
- **Generation**

Actualmente soporta **Generación 1–8**.  
Los formatos disponibles en este MVP son: `vgc2020`, `vgc2021`, `vgc2022`.

## 🧪 Ejemplos de uso

### Equipo Trick Room

```json
{
  "format": "vgc2022",
  "constraints": {
    "strategy": { "trick_room": true },
    "need_roles": ["trick_room","bulky"]
  }
}
```

### Equipo rápido con Dragapult lockeado

```json
{
  "format": "vgc2022",
  "constraints": {
    "lock": ["Dragapult"],
    "min_speed": 120,
    "need_roles": ["fast","special_attacker"]
  }
}
```

## ⚠️ Problemas comunes

1. **`pytest` no se reconoce**  
   Ejecutar con:  
   ```bash
   python -m pytest -q
   ```

2. **Claude rechaza formatos VGC futuros (2023+)**  
   El dataset llega solo hasta **Gen 8**, por lo que únicamente se soportan: `vgc2020`, `vgc2021`, `vgc2022`.

3. **Abilities como lista en el CSV**  
   Se normalizan en runtime para que `infer_roles` funcione correctamente.

