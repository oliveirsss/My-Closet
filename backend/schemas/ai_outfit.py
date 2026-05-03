from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ===== REQUEST SCHEMAS =====


class WeatherData(BaseModel):
    """
    Structured weather data accepted by AI endpoints.

    This model intentionally accepts common alias names (camelCase) via Field aliases
    so the frontend can send either snake_case or camelCase keys. Examples:
      - temperature can be sent as `temperature` or `temp`
      - temperature_min / tempMin, wind_speed / windSpeed, feels_like / feelsLike
    """

    temperature: Optional[float] = Field(
        default=None,
        alias="temp",
        description="Current temperature in °C (alias: temp)",
    )
    temperature_min: Optional[float] = Field(
        default=None,
        alias="tempMin",
        description="Minimum temperature (alias: tempMin)",
    )
    temperature_max: Optional[float] = Field(
        default=None,
        alias="tempMax",
        description="Maximum temperature (alias: tempMax)",
    )
    feels_like: Optional[float] = Field(
        default=None,
        alias="feelsLike",
        description="Feels-like temperature (alias: feelsLike)",
    )
    condition: Optional[str] = Field(
        default=None, description="Weather condition (e.g. 'sunny', 'rainy')"
    )
    humidity: Optional[float] = Field(
        default=None, description="Humidity percentage (0-100)"
    )
    wind_speed: Optional[float] = Field(
        default=None, alias="windSpeed", description="Wind speed (alias: windSpeed)"
    )
    precipitation_probability: Optional[float] = Field(
        default=None,
        alias="precipitationProbability",
        description="Chance of precipitation (0-100)",
    )
    date: Optional[datetime] = Field(
        default=None, description="Optional date for forecast entries"
    )

    class Config:
        populate_by_name = True


class AIOutfitDailyRequest(BaseModel):
    """
    Request schema for daily outfit recommendation.

    The AI system will use the current weather and user's wardrobe
    to suggest an outfit for today.
    """

    # Use a structured WeatherData model instead of a generic dict.
    # Frontend may send either snake_case or common camelCase aliases (see WeatherData).
    weather_data: Optional[WeatherData] = Field(
        default=None,
        description="Structured weather data (temperature, humidity, condition, etc). If not provided, will be fetched by the backend.",
    )
    preferences: Optional[dict] = Field(
        default=None,
        description="User preferences (style, comfort level, occasion, etc)",
    )
    exclude_items: Optional[List[str]] = Field(
        default=None, description="List of item IDs to exclude from recommendations"
    )
    current_outfit_items: Optional[List[str]] = Field(
        default=None,
        description="Current outfit item IDs for follow-up commands such as replacing only shoes",
    )
    user_request: Optional[str] = Field(
        default=None,
        description="User's natural language request (e.g., 'outfit with yellow sneakers', 'formal outfit for meeting')",
    )
    user_prompt: Optional[str] = Field(
        default=None,
        description="Alias for user_request sent by the chat UI.",
    )

    class Config:
        populate_by_name = True


class AIOutfitTravelRequest(BaseModel):
    """
    Request schema for travel outfit recommendations.

    The AI system will suggest multiple outfits for a trip,
    considering weather forecast and duration.
    """

    start_date: datetime
    end_date: datetime
    destination: str = Field(description="Location/city for travel")
    weather_forecast: Optional[List[dict]] = Field(
        default=None,
        description="Weather forecast for destination (if not provided, will be fetched)",
    )
    preferences: Optional[dict] = Field(
        default=None, description="User preferences (style, activities, occasions, etc)"
    )
    exclude_items: Optional[List[str]] = Field(
        default=None, description="List of item IDs to exclude from recommendations"
    )
    luggage_limit: Optional[int] = Field(
        default=10, description="Maximum number of items to pack"
    )

    class Config:
        populate_by_name = True


class AIOutfitAlternativeRequest(BaseModel):
    """
    Request schema for alternative outfit suggestions.

    Given a suggested outfit, request alternatives based on
    weather, occasion, or style preferences.
    """

    current_outfit_items: List[str] = Field(
        description="List of item IDs in the current/suggested outfit"
    )
    weather_data: Optional[WeatherData] = Field(
        default=None,
        description="Structured weather data (optional). Accepts snake_case or camelCase aliases.",
    )
    num_alternatives: int = Field(
        default=3, description="Number of alternative outfits to suggest"
    )
    preferences: Optional[dict] = Field(
        default=None, description="User preferences for alternatives"
    )
    exclude_items: Optional[List[str]] = Field(
        default=None, description="List of item IDs to exclude from alternatives"
    )

    class Config:
        populate_by_name = True


# ===== RESPONSE SCHEMAS =====


class ClothingItemInfo(BaseModel):
    """
    Simplified clothing item information for outfit responses.
    """

    id: str
    name: str
    type: str
    brand: Optional[str] = None
    color: Optional[str] = None
    style: Optional[str] = None
    occasion: Optional[str] = None
    section: Optional[str] = Field(
        default=None,
        description="Display section: base_layer, insulation_layer, pants, outer_layer, shoes, accessories",
    )
    image: str
    layer: int
    materials: Optional[List[str]] = None
    temperature_range: Optional[dict] = Field(
        default=None, description="{'min': X, 'max': Y} temperature range"
    )
    status: str = Field(description="'clean' or 'dirty'")
    favorite: bool = False

    class Config:
        populate_by_name = True


class OutfitSuggestion(BaseModel):
    """
    A single outfit suggestion with items organized by layer/category.
    """

    outfit_id: str = Field(description="Unique ID for this outfit suggestion")
    items: List[ClothingItemInfo] = Field(description="Clothing items in this outfit")
    reasoning: str = Field(
        description="AI-generated explanation of why this outfit was suggested"
    )
    weather_compatibility: dict = Field(
        description="Score/explanation of how well outfit matches weather conditions"
    )
    style_score: Optional[float] = Field(
        default=None, description="Score from 0-1 indicating style coherence"
    )
    comfort_score: Optional[float] = Field(
        default=None, description="Score from 0-1 indicating comfort level"
    )
    versatility_score: Optional[float] = Field(
        default=None,
        description="Score from 0-1 indicating how versatile the outfit is",
    )

    class Config:
        populate_by_name = True


class AIOutfitDailyResponse(BaseModel):
    """
    Response schema for daily outfit recommendation.
    """

    success: bool
    primary_outfit: OutfitSuggestion
    alternative_outfits: Optional[List[OutfitSuggestion]] = Field(
        default=None, description="Alternative outfit suggestions"
    )
    weather_summary: dict = Field(
        description="Summary of weather conditions used for recommendation"
    )
    debug: Optional[dict] = Field(
        default=None, description="Temporary debug information for VLM inspection"
    )
    generated_at: datetime
    model_used: str = Field(description="'vlm' or 'rule_based' (if fallback was used)")

    class Config:
        populate_by_name = True


class AIOutfitTravelResponse(BaseModel):
    """
    Response schema for travel outfit recommendations.
    """

    success: bool
    daily_outfits: List[dict] = Field(
        description="List of outfits recommended for each day of travel"
    )
    packing_list: List[ClothingItemInfo] = Field(
        description="Consolidated list of all items to pack"
    )
    packing_summary: dict = Field(
        description="Summary of packing (total items, breakdown by type, etc)"
    )
    trip_details: dict = Field(
        description="Details about the trip (dates, location, weather overview)"
    )
    generated_at: datetime
    model_used: str = Field(description="'vlm' or 'rule_based' (if fallback was used)")

    class Config:
        populate_by_name = True


class AIOutfitAlternativeResponse(BaseModel):
    """
    Response schema for alternative outfit suggestions.
    """

    success: bool
    original_outfit: OutfitSuggestion
    alternative_outfits: List[OutfitSuggestion]
    generated_at: datetime
    model_used: str = Field(description="'vlm' or 'rule_based' (if fallback was used)")

    class Config:
        populate_by_name = True


class ErrorResponse(BaseModel):
    """
    Standard error response for AI recommendation endpoints.
    """

    success: bool = False
    error: str = Field(description="Error message")
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback rule-based recommendation was provided",
    )
    fallback_outfit: Optional[OutfitSuggestion] = None
    timestamp: datetime
