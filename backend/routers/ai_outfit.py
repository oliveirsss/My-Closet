"""
AI Outfit Recommendation Routes

FastAPI router for AI-powered outfit recommendation endpoints:
- POST /ai-outfit/today
- POST /ai-outfit/travel
- POST /ai-outfit/alternative

These endpoints use the VLM-based recommendation pipeline with fallback
to rule-based recommendations if the VLM fails.
"""

import os
from datetime import datetime

from database import get_user_from_token
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
from services.image_preprocessing_service import ImagePreprocessingService
from services.candidate_outfit_service import CandidateOutfitService
from services.vlm_service import LLaVAService, MockVLMService

router = APIRouter(prefix="/ai-outfit", tags=["ai-outfit"])
security = HTTPBearer()


def get_authorization_header(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Convert FastAPI HTTPBearer credentials into the Authorization header format
    expected by get_user_from_token().
    """
    return f"Bearer {credentials.credentials}"


def get_authenticated_user(
    authorization: str = Depends(get_authorization_header),
):
    """
    Authenticate the current user using the Supabase JWT token.
    """
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def create_vlm_service():
    """
    Create the correct VLM service based on environment configuration.
    """
    enable_vlm = os.getenv("ENABLE_VLM", "true").lower() == "true"
    provider = os.getenv("VLM_PROVIDER", "mock").lower()

    print(f"[VLM] ENABLE_VLM={enable_vlm}")
    print(f"[VLM] VLM_PROVIDER={provider}")

    if not enable_vlm:
        print("[VLM] VLM disabled. Using MockVLMService.")
        return MockVLMService()

    if provider == "llava":
        print("[VLM] Creating LLaVAService")
        return LLaVAService()

    print("[VLM] Creating MockVLMService")
    return MockVLMService()


vlm_service = create_vlm_service()
recommendation_service = RecommendationService(vlm_service=vlm_service)
image_preprocessing_service = ImagePreprocessingService()
candidate_outfit_service = CandidateOutfitService()


def derive_display_section(item: dict) -> str:
    """
    Derive UI display section from candidate section or item metadata.
    Candidate sections are authoritative when present.
    """
    if item.get("section"):
        return item["section"]

    text = " ".join(
        str(value or "")
        for value in [item.get("type"), item.get("name"), item.get("brand")]
    ).lower()
    normalized = (
        text.replace("ç", "c")
        .replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
    )

    if any(token in normalized for token in ["calcado", "sapatilha", "tenis", "sneaker", "shoe", "sapato", "bota"]):
        return "shoes"
    if any(token in normalized for token in ["calca", "calcas", "pants", "trousers", "jeans", "calcoes", "shorts"]):
        return "pants"
    if any(token in normalized for token in ["casaco", "jacket", "coat", "blazer", "sobretudo"]):
        return "outer_layer"
    if any(token in normalized for token in ["camisola", "hoodie", "sweater", "knit", "malha", "cardigan", "sweatshirt"]):
        return "insulation_layer"
    if any(token in normalized for token in ["acessor", "accessor", "belt", "cinto", "tie", "gravata", "scarf", "lenco", "hat", "bone", "cap"]):
        return "accessories"
    return "base_layer"


def layer_for_section(section: str, fallback_layer: int) -> int:
    return {
        "base_layer": 1,
        "insulation_layer": 2,
        "pants": 2,
        "outer_layer": 3,
        "shoes": 3,
        "accessories": 3,
    }.get(section, fallback_layer)


def format_clothing_item(item: dict) -> ClothingItemInfo:
    """
    Convert any internal clothing item dictionary into the response schema format.
    """
    temperature_range = item.get("temperature_range", {}) or {}
    section = derive_display_section(item)

    return ClothingItemInfo(
        id=item["id"],
        name=item["name"],
        type=item["type"],
        brand=item.get("brand"),
        color=item.get("color"),
        style=item.get("style"),
        occasion=item.get("occasion"),
        section=section,
        image=item.get("image_url", item.get("image", "")),
        layer=layer_for_section(section, item.get("layer", 1)),
        materials=item.get("materials", []),
        temperature_range={
            "min": item.get(
                "tempMin", item.get("temp_min", temperature_range.get("min", -10))
            ),
            "max": item.get(
                "tempMax", item.get("temp_max", temperature_range.get("max", 30))
            ),
        },
        status=item.get("status", "clean"),
        favorite=item.get("favorite", False),
    )


@router.post("/today", response_model=AIOutfitDailyResponse)
async def get_daily_outfit_recommendation(
    request: AIOutfitDailyRequest,
    user=Depends(get_authenticated_user),
):
    user_id = user.user.id

    try:
        weather_data_obj = request.weather_data

        weather_data = weather_data_obj.model_dump() if weather_data_obj else {}

        temperature = weather_data.get("temp", weather_data.get("temperature", 20))
        weather_condition = weather_data.get("condition", "sunny")
        humidity = weather_data.get("humidity")
        wind_speed = weather_data.get("wind_speed", weather_data.get("windSpeed"))
        user_prompt = request.user_request or request.user_prompt

        print(f"[AI Outfit] Daily request for user={user_id}")
        print(f"[AI Outfit] Weather: {weather_data}")
        print(f"[AI Outfit] User request: {user_prompt}")
        print(f"[AI Outfit] Current outfit items: {request.current_outfit_items}")

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
            current_outfit_items=request.current_outfit_items,
            user_request=user_prompt,
        )

        if not result.get("success"):
            print(
                "[AI Outfit] Recommendation failed: "
                f"{result.get('error', 'Recommendation failed')}"
            )
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Recommendation failed"),
            )

        outfit_data = result.get("outfit", {})
        items = outfit_data.get("items", [])

        formatted_items = [format_clothing_item(item) for item in items]

        model_used = result.get("model_used", "unknown")

        debug_payload = result.get("debug") if os.getenv("DEBUG_AI", "false").lower() == "true" else None

        return AIOutfitDailyResponse(
            success=True,
            primary_outfit=OutfitSuggestion(
                outfit_id=f"{user_id}_{int(datetime.now().timestamp())}",
                items=formatted_items,
                reasoning=outfit_data.get(
                    "reasoning",
                    result.get("reasoning", "AI-generated outfit recommendation"),
                ),
                weather_compatibility=result.get("weather_compatibility", {}),
                style_score=0.8,
                comfort_score=0.8,
                versatility_score=0.7,
            ),
            alternative_outfits=None,
            weather_summary=weather_data,
            debug=debug_payload,
            generated_at=datetime.now(),
            model_used=model_used,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AI Outfit] Error in daily outfit recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/matcher")
async def debug_ai_matcher(user=Depends(get_authenticated_user)):
    user_id = user.user.id
    try:
        return await recommendation_service.debug_deterministic_matcher(
            user_id=user_id,
            temperature=20,
        )
    except Exception as e:
        print(f"[AI Outfit] Error in matcher debug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug-candidates")
async def debug_candidate_outfits(
    payload: dict = Body(...),
    user=Depends(get_authenticated_user),
):
    """
    Temporary deterministic candidate generation endpoint.

    This endpoint does not call LLaVA. It loads the authenticated user's wardrobe,
    parses the user request, and returns 3-5 complete candidate outfits when
    possible.
    """
    user_id = user.user.id
    try:
        user_request = payload.get("user_request") or payload.get("user_prompt") or ""
        weather_data = payload.get("weather_data") or {}
        current_outfit_items = payload.get("current_outfit_items") or []
        exclude_items = payload.get("exclude_items") or []
        parsed_intent = recommendation_service.user_request_parser.parse_request(
            user_request
        )

        print(f"[AI Outfit] Debug candidates request for user={user_id}")
        print(f"[AI Outfit] Debug candidates user_request={user_request}")
        print(f"[AI Outfit] Debug candidates weather_data={weather_data}")
        print(f"[AI Outfit] Debug candidates current_outfit_items={current_outfit_items}")
        print(f"[AI Outfit] Debug candidates exclude_items={exclude_items}")

        wardrobe_items = await recommendation_service.wardrobe_service.get_user_wardrobe(
            user_id=user_id,
            only_clean=False,
            exclude_item_ids=None,
        )

        result = candidate_outfit_service.generate_candidate_outfits(
            user_id=user_id,
            wardrobe_items=wardrobe_items,
            weather=weather_data,
            parsed_intent=parsed_intent,
            current_outfit_items=current_outfit_items,
            exclude_items=exclude_items,
        )
        return result
    except Exception as e:
        print(f"[AI Outfit] Error in debug candidate generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/travel", response_model=AIOutfitTravelResponse)
async def get_travel_outfit_recommendations(
    request: AIOutfitTravelRequest,
    user=Depends(get_authenticated_user),
):
    user_id = user.user.id

    try:
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

        travel_plan = result.get("travel_plan", {})
        daily_outfits = travel_plan.get("daily_outfits", [])
        packing_list = travel_plan.get("packing_list", [])

        formatted_outfits = []
        for index, outfit_data in enumerate(daily_outfits):
            formatted_items = [
                format_clothing_item(item) for item in outfit_data.get("items", [])
            ]

            formatted_outfits.append(
                OutfitSuggestion(
                    outfit_id=f"{user_id}_day_{index + 1}",
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
            packing_list=[format_clothing_item(item) for item in packing_list],
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
            model_used=result.get("model_used", "unknown"),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AI Outfit] Error in travel outfit recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alternative", response_model=AIOutfitAlternativeResponse)
async def get_alternative_outfit_recommendations(
    request: AIOutfitAlternativeRequest,
    user=Depends(get_authenticated_user),
):
    user_id = user.user.id

    try:
        weather_data = request.weather_data.model_dump() if request.weather_data else {}
        temperature = weather_data.get("temp", weather_data.get("temperature", 20))
        weather_condition = weather_data.get("condition", "sunny")
        humidity = weather_data.get("humidity")
        wind_speed = weather_data.get("wind_speed", weather_data.get("windSpeed"))

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

        formatted_alternatives = []
        for index, alt_data in enumerate(result.get("alternatives", [])):
            formatted_items = [
                format_clothing_item(item) for item in alt_data.get("items", [])
            ]

            formatted_alternatives.append(
                OutfitSuggestion(
                    outfit_id=f"{user_id}_alt_{index + 1}",
                    items=formatted_items,
                    reasoning=alt_data.get("reasoning", ""),
                    weather_compatibility={},
                    style_score=0.75,
                    comfort_score=0.75,
                    versatility_score=0.7,
                )
            )

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
            model_used=result.get("model_used", "unknown"),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AI Outfit] Error in alternative outfit recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ai_recommendation_health_check():
    provider = os.getenv("VLM_PROVIDER", "mock").lower()
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
        "recommendation_types": ["daily", "travel", "alternative"],
        "phase": "5",
        "model_provider": provider,
        "vlm_provider": provider,
        "llava_active": provider == "llava",
        "fallback_active": True,
        "image_preprocessing_status": {
            "active": True,
            "max_images_per_request": image_preprocessing_service.get_stats().get(
                "max_images_per_request"
            ),
        },
        "note": "VLM pipeline with reliability validation and fallback",
        "timestamp": datetime.now().isoformat(),
    }
