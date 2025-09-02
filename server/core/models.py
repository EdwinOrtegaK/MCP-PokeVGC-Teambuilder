from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal

TypeName = Literal[
    "Normal","Fire","Water","Electric","Grass","Ice","Fighting","Poison","Ground","Flying",
    "Psychic","Bug","Rock","Ghost","Dragon","Dark","Steel","Fairy"
]

class Pokemon(BaseModel):
    number: int = Field(alias="Number")
    name: str = Field(alias="Name")
    type1: TypeName = Field(alias="Type 1")
    type2: Optional[TypeName] = Field(alias="Type 2", default=None)
    abilities: List[str] = Field(default_factory=list, alias="Abilities")

    hp: int = Field(alias="HP")
    att: int = Field(alias="Att")
    deff: int = Field(alias="Def")
    spa: int = Field(alias="Spa")
    spd: int = Field(alias="Spd")
    spe: int = Field(alias="Spe")

    bst: Optional[int] = Field(default=None, alias="BST")
    mean: Optional[float] = Field(default=None, alias="Mean")
    std: Optional[float] = Field(default=None, alias="Standard Deviation")

    generation: Optional[int] = Field(default=None, alias="Generation")
    experience_type: Optional[str] = Field(default=None, alias="Experience type")
    exp_to_100: Optional[int] = Field(default=None, alias="Experience to level 100")
    final_evolution: Optional[bool] = Field(default=None, alias="Final Evolution")
    catch_rate: Optional[int] = Field(default=None, alias="Catch Rate")
    legendary: Optional[bool] = Field(default=None, alias="Legendary")
    mega_evolution: Optional[bool] = Field(default=None, alias="Mega Evolution")
    alolan_form: Optional[bool] = Field(default=None, alias="Alolan Form")
    galarian_form: Optional[bool] = Field(default=None, alias="Galarian Form")

    height_m: Optional[float] = Field(default=None, alias="Height")
    weight_kg: Optional[float] = Field(default=None, alias="Weight")
    bmi: Optional[float] = Field(default=None, alias="BMI")

    # Mapa de multiplicadores defensivos: ataque de tipo T contra este Pokémon
    against: Dict[TypeName, float] = Field(default_factory=dict)

    class Config:
        populate_by_name = True

class Constraints(BaseModel):
    include_types: List[TypeName] = []
    exclude_types: List[TypeName] = []
    min_speed: int = 0
    min_spdef: int = 0
    min_bulk: int = 0   # hp + deff + spd umbral simple

    roles_needed: List[Literal[
        "speed_control","redirection","damage_physical","damage_special",
        "intimidate","weather","terrain"
    ]] = []

class SuggestParams(BaseModel):
    format: str = "VGC2025"
    constraints: Constraints = Field(default_factory=Constraints)

class TeamMember(BaseModel):
    name: str
    type1: TypeName
    type2: Optional[TypeName] = None
    role: str = "balanced"

class Team(BaseModel):
    members: List[TeamMember]

class SynergyReport(BaseModel):
    coverage_offensive: Dict[TypeName, int]  # cuántos miembros golpean 2x a cada tipo
    resistances_defensive: Dict[TypeName, int]  # cuántos miembros reciben <=0.5x vs ese tipo atacante
    holes: List[str]     # tipos atacante problemáticos (promedio >1.5x, etc.)
