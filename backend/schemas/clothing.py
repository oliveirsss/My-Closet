from typing import List, Optional

from pydantic import BaseModel, Field


class ClothingItem(BaseModel):
    """Schema for clothing item in the wardrobe."""

    name: str
    brand: str
    size: str
    type: str
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


class ImageUpload(BaseModel):
    """Schema for image upload request."""

    image: str
    fileName: str
