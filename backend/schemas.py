from pydantic import BaseModel
from typing import List, Optional

# Modelo para Roupa
class ClothingItem(BaseModel):
    name: str
    brand: str
    size: str
    type: str
    layer: int
    materials: List[str]
    weight: float
    tempMin: int
    tempMax: int
    waterproof: bool
    windproof: bool
    seasons: List[str]
    image: str
    status: str
    favorite: bool
    id: Optional[str] = None

# Modelo para Upload de Imagem
class ImageUpload(BaseModel):
    image: str
    fileName: str

# Modelo para Signup
class UserSignup(BaseModel):
    email: str
    password: str
    name: str


class UserProfileBase(BaseModel):
    name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None


class UserProfile(UserProfileBase):
    user_id: str


class UserProfileUpdate(UserProfileBase):
    pass