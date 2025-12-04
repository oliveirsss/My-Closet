from pydantic import BaseModel, Field
from typing import List, Optional


# --- PRODUTOS (Roupa) ---
class ClothingItem(BaseModel):
    name: str
    brand: str
    size: str
    type: str
    layer: int
    materials: List[str]
    weight: float
    # Alias para converter camelCase (React) -> snake_case (Python)
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


# --- IMAGENS ---
class ImageUpload(BaseModel):
    image: str
    fileName: str


# --- UTILIZADORES (Auth & Perfil) ---
class UserSignup(BaseModel):
    email: str
    password: str
    name: str


class UserProfileUpdate(BaseModel):
    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None


# (Opcional) Caso precises de retornar o perfil completo
class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None