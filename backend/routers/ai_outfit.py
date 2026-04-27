"""
AI Outfit Recommendation Routes

FastAPI router for the new AI-powered outfit recommendation endpoints:
- POST /ai-outfit/today - Daily outfit recommendation
- POST /ai-outfit/travel - Travel outfit recommendations
- POST /ai-outfit/alternative - Alternative outfit suggestions

These endpoints use the VLM-based recommendation pipeline with fallback
to rule-based recommendations if the VLM fails.
"""

from datetime import datetime

from database import get_user_from_token
from fastapi import APIRouter, Header, HTTPException
from schemas.ai_outfit import (
    AIOutfitAlternativeRequest,
    AIOutfitAlternativeResponse,
    AIOutfitDailyRequest,
    AIOutfitDailyResponse,
    AIOutfitTravelRequest,
    AIOutfitTravelResponse,
    ClothingItemInfo,
    OutfitSuggestion,
)
from services.recommendation_service import RecommendationService
from services.vlm_service import LLaVAService

router = APIRouter(prefix="/ai-outfit", tags=["ai-outfit"])

# Initialize services
import os

# Create VLM service. Falls back to mock if LLaVA is not enabled.
if os.getenv("ENABLE_VLM", "true").lower() == "true":
    vlm_service = LLaVAService() # Phase 2: LLaVA integration
else:
    from services.vlm_service import MockVLMService
    vlm_service = MockVLMService() 

recommendation_service = RecommendationService(vlm_service=vlm_service)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/today", response_model=AIOutfitDailyResponse)
async def get_daily_outfit_recommendation(
    request: AIOutfitDailyRequest,
    authorization: str = Header(None),
):
    """
    Get an outfit recommendation for today.

    Takes current weather conditions and returns a recommended outfit
    from the user's wardrobe, along with alternative suggestions.

    Args:
        request: AIOutfitDailyRequest containing:
            - weather_data: Current weather dict (temp, humidity, conditions, etc)
            - preferences: Optional style preferences dict
            - exclude_items: Optional items to exclude

        authorization: Bearer token for authentication

    Returns:
        AIOutfitDailyResponse with recommended outfit(s) and reasoning

    Raises:
        HTTPException: If user is not authenticated or recommendation fails
    """
    # Authenticate user
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = user.user.id

    try:
        # Extract weather data from request
        weather_data = request.weather_data or {}
        temperature = weather_data.get("temp", 20)
        weather_condition = weather_data.get("condition", "sunny")
        humidity = weather_data.get("humidity")
        wind_speed = weather_data.get("wind_speed")

        # Call recommendation service
        result = await recommendation_service.recommend_daily_outfit(
            user_id=user_id,
            temperature=temperature,
            weather_condition=weather_condition,
            humidity=humidity,
            wind_speed=wind_speed,
            occasion=request.preferences.get("occasion")
            if request.preferences
            else None,
            preferences=request.preferences,
            exclude_items=request.exclude_items,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get("error", "Recommendation failed")
            )

        # Format response
        outfit_data = result.get("outfit", {})
        items = outfit_data.get("items", [])

        # Convert items to ClothingItemInfo format
        formatted_items = [
            ClothingItemInfo(
                id=item["id"],
                name=item["name"],
                type=item["type"],
                brand=item.get("brand"),
                image=item.get("image_url", item.get("image", "")),
                layer=item.get("layer", 1),
                materials=item.get("materials", []),
                temperature_range={
                    "min": item.get(
                        "tempMin", item.get("temperature_range", {}).get("min", -10)
                    ),
                    "max": item.get(
                        "tempMax", item.get("temperature_range", {}).get("max", 30)
                    ),
                },
                status=item.get("status", "clean"),
                favorite=item.get("favorite", False),
            )
            for item in items
        ]

        return AIOutfitDailyResponse(
            success=True,
            primary_outfit=OutfitSuggestion(
                outfit_id=f"{user_id}_{int(datetime.now().timestamp())}",
                items=formatted_items,
                reasoning=outfit_data.get("reasoning", result.get("reasoning", "AI-generated outfit recommendation")),
                weather_compatibility=result.get("weather_compatibility", {}),
                style_score=0.8,
                comfort_score=0.8,
                versatility_score=0.7,
            ),
            alternative_outfits=None,
            weather_summary=weather_data,
            generated_at=datetime.now(),
            model_used="rule_based"
            if result.get("model_used") == "rule_based"
            else "vlm",
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in daily outfit recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/travel", response_model=AIOutfitTravelResponse)
async def get_travel_outfit_recommendations(
    request: AIOutfitTravelRequest,
    authorization: str = Header(None),
):
    """
    Get outfit recommendations for a trip.

    Generates multiple outfits and a packing list for a trip,
    optimizing for the destination's weather and luggage constraints.

    Args:
        request: AIOutfitTravelRequest containing:
            - start_date: Trip start date
            - end_date: Trip end date
            - destination: Travel destination (for weather)
            - weather_forecast: Optional weather forecast list
            - preferences: Optional user preferences dict
            - exclude_items: Optional items to exclude
            - luggage_limit: Maximum items to pack

        authorization: Bearer token for authentication

    Returns:
        AIOutfitTravelResponse with daily outfits and packing list

    Raises:
        HTTPException: If user is not authenticated or recommendation fails
    """
    # Authenticate user
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = user.user.id

    try:
        # Call recommendation service
        result = await recommendation_service.recommend_travel_outfits(
            user_id=user_id,
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            luggage_limit=request.luggage_limit or 10,
            preferences=request.preferences,
            exclude_items=request.exclude_items,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Travel recommendation failed"),
            )

        # Format response
        travel_plan = result.get("travel_plan", {})
        daily_outfits = travel_plan.get("daily_outfits", [])
        packing_list = travel_plan.get("packing_list", [])

        # Convert to response format
        formatted_outfits = []
        for outfit_data in daily_outfits:
            items = outfit_data.get("items", [])
            formatted_items = [
                ClothingItemInfo(
                    id=item["id"],
                    name=item["name"],
                    type=item["type"],
                    brand=item.get("brand"),
                    image=item.get("image_url", item.get("image", "")),
                    layer=item.get("layer", 1),
                    materials=item.get("materials", []),
                    temperature_range={
                        "min": item.get(
                            "tempMin", item.get("temperature_range", {}).get("min", -10)
                        ),
                        "max": item.get(
                            "tempMax", item.get("temperature_range", {}).get("max", 30)
                        ),
                    },
                    status=item.get("status", "clean"),
                    favorite=item.get("favorite", False),
                )
                for item in items
            ]

            formatted_outfits.append(
                OutfitSuggestion(
                    outfit_id=f"{user_id}_day_{len(formatted_outfits)}",
                    items=formatted_items,
                    reasoning=outfit_data.get("reasoning", ""),
                    weather_compatibility={},
                    style_score=0.8,
                    comfort_score=0.8,
                    versatility_score=0.9,
                )
            )

        return AIOutfitTravelResponse(
            success=True,
            daily_outfits=formatted_outfits,
            packing_list=[
                ClothingItemInfo(
                    id=item["id"],
                    name=item["name"],
                    type=item["type"],
                    brand=item.get("brand"),
                    image=item.get("image_url", item.get("image", "")),
                    layer=item.get("layer", 1),
                    materials=item.get("materials", []),
                    temperature_range={
                        "min": item.get(
                            "tempMin", item.get("temperature_range", {}).get("min", -10)
                        ),
                        "max": item.get(
                            "tempMax", item.get("temperature_range", {}).get("max", 30)
                        ),
                    },
                    status=item.get("status", "clean"),
                    favorite=item.get("favorite", False),
                )
                for item in packing_list
            ],
            packing_summary={
                "total_items": len(packing_list),
                "notes": travel_plan.get("packing_notes", ""),
            },
            trip_details={
                "destination": request.destination,
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
            },
            generated_at=datetime.now(),
            model_used="rule_based"
            if result.get("model_used") == "rule_based"
            else "vlm",
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in travel outfit recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alternative", response_model=AIOutfitAlternativeResponse)
async def get_alternative_outfit_recommendations(
    request: AIOutfitAlternativeRequest,
    authorization: str = Header(None),
):
    """
    Get alternative outfit suggestions.

    Given an outfit, generate alternative suggestions that work
    for the same weather/occasion but with different items.

    Args:
        request: AIOutfitAlternativeRequest containing:
            - current_outfit_items: List of item IDs in current outfit
            - weather_data: Optional weather dict
            - num_alternatives: Number of alternatives (default 3)
            - preferences: Optional preferences dict
            - exclude_items: Optional items to exclude

        authorization: Bearer token for authentication

    Returns:
        AIOutfitAlternativeResponse with alternative suggestions

    Raises:
        HTTPException: If user is not authenticated or recommendation fails
    """
    # Authenticate user
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = user.user.id

    try:
        # Extract weather data from request
        weather_data = request.weather_data or {}
        temperature = weather_data.get("temp", 20)
        weather_condition = weather_data.get("condition", "sunny")
        humidity = weather_data.get("humidity")
        wind_speed = weather_data.get("wind_speed")

        # Call recommendation service
        result = await recommendation_service.recommend_alternatives(
            user_id=user_id,
            current_outfit_item_ids=request.current_outfit_items,
            temperature=temperature,
            weather_condition=weather_condition,
            humidity=humidity,
            wind_speed=wind_speed,
            num_alternatives=request.num_alternatives,
            preferences=request.preferences,
            exclude_items=request.exclude_items,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Alternative recommendation failed"),
            )

        # Format response
        alternatives_data = result.get("alternatives", [])

        formatted_alternatives = []
        for alt_data in alternatives_data:
            items = alt_data.get("items", [])
            formatted_items = [
                ClothingItemInfo(
                    id=item["id"],
                    name=item["name"],
                    type=item["type"],
                    brand=item.get("brand"),
                    image=item.get("image_url", item.get("image", "")),
                    layer=item.get("layer", 1),
                    materials=item.get("materials", []),
                    temperature_range={
                        "min": item.get(
                            "tempMin", item.get("temperature_range", {}).get("min", -10)
                        ),
                        "max": item.get(
                            "tempMax", item.get("temperature_range", {}).get("max", 30)
                        ),
                    },
                    status=item.get("status", "clean"),
                    favorite=item.get("favorite", False),
                )
                for item in items
            ]

            formatted_alternatives.append(
                OutfitSuggestion(
                    outfit_id=f"{user_id}_alt_{len(formatted_alternatives)}",
                    items=formatted_items,
                    reasoning=alt_data.get("reasoning", ""),
                    weather_compatibility={},
                    style_score=0.75,
                    comfort_score=0.75,
                    versatility_score=0.7,
                )
            )

        # Create a default original outfit from the current items (Phase 1)
        original_outfit = OutfitSuggestion(
            outfit_id=f"{user_id}_original",
            items=[],
            reasoning="Original outfit from current selection",
            weather_compatibility={},
            style_score=0.7,
            comfort_score=0.7,
            versatility_score=0.6,
        )

        return AIOutfitAlternativeResponse(
            success=True,
            original_outfit=original_outfit,
            alternative_outfits=formatted_alternatives,
            generated_at=datetime.now(),
            model_used="rule_based"
            if result.get("model_used") == "rule_based"
            else "vlm",
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in alternative outfit recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ai_recommendation_health_check():
    """
    Health check endpoint for AI recommendation system.

    Returns the status of all services in the recommendation pipeline.
    """
    return {
        "status": "operational",
        "services": {
            "vlm_service": "available" if vlm_service.health_check() else "unavailable",
            "wardrobe_service": "available",
            "weather_service": "available",
            "usage_service": "available",
            "prompt_service": "available",
            "response_parser": "available",
        },
        "recommendation_types": [
            "daily",
            "travel",
            "alternative",
        ],
        "phase": "2",
        "note": "LLaVA integration live via external API",
        "timestamp": datetime.now().isoformat(),
    }
