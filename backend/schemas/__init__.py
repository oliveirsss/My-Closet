"""
Schemas module for MyCloset backend.

Exports all Pydantic schemas for request/response validation and documentation.
Includes schemas for:
- Authentication (UserSignup, UserProfileUpdate, UserProfile)
- Clothing items (ClothingItem, ImageUpload)
- AI outfit recommendations (AIOutfitDailyRequest, AIOutfitDailyResponse, etc.)
"""

# Auth schemas
# AI outfit schemas
from schemas.ai_outfit import (
    AIOutfitAlternativeRequest,
    AIOutfitAlternativeResponse,
    AIOutfitDailyRequest,
    AIOutfitDailyResponse,
    AIOutfitTravelRequest,
    AIOutfitTravelResponse,
    ClothingItemInfo,
    ErrorResponse,
    OutfitSuggestion,
)
from schemas.auth import UserProfile, UserProfileUpdate, UserSignup

# Clothing schemas
from schemas.clothing import ClothingItem, ImageUpload

__all__ = [
    # Auth
    "UserSignup",
    "UserProfileUpdate",
    "UserProfile",
    # Clothing
    "ClothingItem",
    "ImageUpload",
    # AI outfit
    "AIOutfitDailyRequest",
    "AIOutfitDailyResponse",
    "AIOutfitTravelRequest",
    "AIOutfitTravelResponse",
    "AIOutfitAlternativeRequest",
    "AIOutfitAlternativeResponse",
    "ClothingItemInfo",
    "OutfitSuggestion",
    "ErrorResponse",
]
