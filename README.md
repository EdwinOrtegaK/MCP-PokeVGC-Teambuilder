# MCP-PokeVGC-Teambuilder

**MCP** server for building and analyzing Pokémon VGC (Video Game Championships) teams.  
This project was designed as an **MVP (Minimum Viable Product)** that allows:

- Suggesting complete teams based on constraints (types, speed, abilities, roles, etc.).
- Suggesting individual members to complete a team.
- Exporting teams to the Pokémon Showdown format.
- Analyzing offensive and defensive synergies of a team.
- Quickly filtering the Pokémon pool from the dataset.

## 🚀 Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd MCP-PokeVGC-Teambuilder
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv

# On Linux/macOS
source .venv/bin/activate

# On Windows (PowerShell)
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## ▶️ Running the MCP server

Run the server directly with Python:

```bash
python -m server.main
```

You can also configure it as an **MCP Server** in compatible clients (e.g. Claude Desktop), pointing to the Python binary in your `.venv` and with arguments:

```
-u -m server.main
```

When running, the server listens for MCP requests via **stdin/stdout**.

## 📂 Project structure

```
MCP-PokeVGC-Teambuilder/
├── data/
│   └── pokemon.csv          # Main dataset (Gen 1–8)
├── server/
│   ├── core/
│   │   └── models.py        # Definition of Pokémon objects and SynergyReport
│   ├── tools/
│   │   ├── dataset.py       # Dataset loading and normalization
│   │   ├── filters.py       # Quick filters (speed, types, etc.)
│   │   ├── roles.py         # Role inference by stats/abilities
│   │   ├── synergy.py       # Offensive coverage and resistances
│   │   └── export.py        # Export teams to Showdown
│   ├── schemas/             # JSON Schemas for MCP tools
│   └── main.py              # Main MCP server
├── tests/                   # Unit tests with pytest
└── README.md
```

## 🛠 Available MCP tools

The server exposes several tools that can be invoked via `tools/call`:

### 1. `suggest_team`
Suggests a complete team (6 Pokémon).

**Example arguments:**

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
Converts a team to Pokémon Showdown format.

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
Returns a list of candidates according to simple filters.

**Example:**

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
Analyzes the synergy of a team (offensive coverage and resistances).

**Example:**

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
Suggests 3–5 candidates that meet criteria.

**Example:**

```json
{
  "min_speed": 120,
  "role": "fast",
  "required_ability": "Levitate"
}
```

## ✅ Tests

The project includes **automated tests** with `pytest`:

```bash
python -m pytest -q
```

Included tests:

- `test_dataset.py`: validates correct loading of `pokemon.csv`.
- `test_synergy.py`: checks coverage and resistances with toy teams.
- `test_suggest.py`: ensures `suggest_team` always returns 6 members.

## 📊 Dataset

The dataset used is `data/pokemon.csv`, derived from Smogon and Kaggle.  
It includes columns:

- **Name, Type 1, Type 2**
- **HP, Att, Def, Spa, Spd, Spe**
- **Abilities**
- **Against_X** for all 18 types
- **Generation**

Currently supports **Generations 1–8**.  
The formats available in this MVP are: `vgc2020`, `vgc2021`, `vgc2022`.

## 🧪 Usage examples

### Trick Room team

```json
{
  "format": "vgc2022",
  "constraints": {
    "strategy": { "trick_room": true },
    "need_roles": ["trick_room","bulky"]
  }
}
```

### Fast team with locked Dragapult

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

## ⚠️ Common issues

1. **`pytest` not recognized**  
   Run with:  
   ```bash
   python -m pytest -q
   ```

2. **Claude rejects future VGC formats (2023+)**  
   The dataset only goes up to **Gen 8**, so only these are supported: `vgc2020`, `vgc2021`, `vgc2022`.

3. **Abilities as a list in the CSV**  
   They are normalized at runtime so that `infer_roles` works correctly.
