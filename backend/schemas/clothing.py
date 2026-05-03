from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


COLOR_ALIASES = {
    "amarelo": "yellow",
    "amarelos": "yellow",
    "amarela": "yellow",
    "amarelas": "yellow",
    "azul": "blue",
    "azuis": "blue",
    "vermelho": "red",
    "vermelhos": "red",
    "vermelha": "red",
    "vermelhas": "red",
    "verde": "green",
    "verdes": "green",
    "preto": "black",
    "pretos": "black",
    "preta": "black",
    "pretas": "black",
    "branco": "white",
    "brancos": "white",
    "branca": "white",
    "brancas": "white",
    "cinza": "gray",
    "cinzas": "gray",
    "rosa": "pink",
    "rosas": "pink",
    "roxo": "purple",
    "roxos": "purple",
    "roxa": "purple",
    "roxas": "purple",
    "laranja": "orange",
    "laranjas": "orange",
    "marrom": "brown",
    "marrons": "brown",
    "bege": "beige",
    "beges": "beige",
    "creme": "cream",
    "cremes": "cream",
    "ouro": "gold",
    "ouros": "gold",
    "prata": "silver",
    "pratas": "silver",
    "grey": "gray",
}


class ClothingItem(BaseModel):
    """Schema for clothing item in the wardrobe."""

    name: str
    brand: str
    size: str
    type: str
    color: Optional[str] = None
    style: Optional[str] = None
    occasion: Optional[str] = None
    layer: int
    materials: List[str]
    weight: float
    tempMin: int = Field(alias="tempMin")
    tempMax: int = Field(alias="tempMax")
    waterproof: bool
    windproof: bool
    seasons: List[str]
    image: str
    status: str
    favorite: bool
    is_public: bool = Field(default=False, alias="isPublic")
    id: Optional[str] = None

    class Config:
        populate_by_name = True

    @field_validator("color", mode="before")
    @classmethod
    def normalize_optional_color(cls, value):
        if value is None:
            return None

        normalized = str(value).strip().lower()
        if not normalized:
            return None

        return COLOR_ALIASES.get(normalized, normalized)

    @field_validator("style", "occasion", mode="before")
    @classmethod
    def normalize_optional_metadata(cls, value):
        if value is None:
            return None

        normalized = str(value).strip().lower()
        return normalized or None


class ImageUpload(BaseModel):
    """Schema for image upload request."""

    image: str
    fileName: str
