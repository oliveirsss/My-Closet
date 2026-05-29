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
import re
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

TRAVEL_REUSE_WARNING_PT = (
    "Algumas peças foram repetidas porque o guarda-roupa ainda tem poucas alternativas."
)


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

    if any(token in normalized for token in ["vestido", "dress"]):
        return "dress"
    if any(token in normalized for token in ["saia", "skirt"]):
        return "skirt"
    if any(token in normalized for token in ["macacao", "jumpsuit"]):
        return "jumpsuit"
    if any(token in normalized for token in ["mala", "carteira", "handbag", "purse", "bag"]):
        return "bag"
    if any(token in normalized for token in ["calcado", "sapatilha", "tenis", "sneaker", "shoe", "sapato", "bota", "sandalia", "sandal"]):
        return "shoes"
    if any(token in normalized for token in ["calca", "calcas", "pants", "trousers", "jeans", "calcoes", "shorts"]):
        return "pants"
    if any(token in normalized for token in ["casaco", "jacket", "coat", "blazer", "sobretudo"]):
        return "outer_layer"
    if any(token in normalized for token in ["camisola", "hoodie", "sweater", "knit", "malha", "cardigan", "sweatshirt"]):
        return "insulation_layer"
    if any(token in normalized for token in ["top", "blusa", "blouse"]):
        return "base_layer"
    if any(token in normalized for token in ["acessor", "accessor", "belt", "cinto", "tie", "gravata", "scarf", "lenco", "hat", "bone", "cap"]):
        return "accessories"
    return "base_layer"


def layer_for_section(section: str, fallback_layer: int) -> int:
    return {
        "base_layer": 1,
        "dress": 1,
        "jumpsuit": 1,
        "insulation_layer": 2,
        "skirt": 2,
        "pants": 2,
        "outer_layer": 3,
        "shoes": 3,
        "bag": 3,
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


def _travel_day_weather(day_weather: dict, destination: str) -> dict:
    temp = day_weather.get("temp")
    if temp is None:
        temp = day_weather.get("temperature")
    if temp is None:
        temp_min = day_weather.get("temperature_min")
        temp_max = day_weather.get("temperature_max")
        if temp_min is not None and temp_max is not None:
            temp = (float(temp_min) + float(temp_max)) / 2
    if temp is None:
        temp = 18
    try:
        temp = float(temp)
    except (TypeError, ValueError):
        temp = 18

    return {
        "temp": temp,
        "temperature": temp,
        "condition": day_weather.get("condition", "cloudy"),
        "humidity": day_weather.get("humidity"),
        "wind_speed": day_weather.get("wind_speed", day_weather.get("windSpeed")),
        "location": day_weather.get("location", destination),
        "date": day_weather.get("date"),
        "is_mock": day_weather.get("is_mock", False),
    }


def _clean_item_ids_by_section(items: list[dict]) -> dict[str, set[str]]:
    sections = {
        "dress": set(),
        "jumpsuit": set(),
        "base_layer": set(),
        "skirt": set(),
        "pants": set(),
        "shoes": set(),
        "outer_layer": set(),
        "insulation_layer": set(),
        "bag": set(),
        "accessories": set(),
    }
    for item in items:
        item_id = item.get("id")
        if not item_id:
            continue
        status = str(item.get("status") or "clean").strip().lower()
        section = derive_display_section(item)
        if status == "clean" and section in sections:
            sections[section].add(str(item_id))
    return sections


def _rotation_excludes_for_day(
    used_ids_by_section: dict[str, set[str]],
    clean_ids_by_section: dict[str, set[str]],
    base_excludes: set[str],
    trip_days: int,
) -> list[str]:
    excluded = set(base_excludes)

    for section in [
        "base_layer",
        "dress",
        "jumpsuit",
        "skirt",
        "pants",
        "shoes",
        "outer_layer",
        "insulation_layer",
    ]:
        used_ids = used_ids_by_section.get(section, set())
        clean_ids = clean_ids_by_section.get(section, set())
        if clean_ids - used_ids:
            excluded.update(used_ids)
    return sorted(excluded)


def _travel_section_caps(trip_days: int) -> dict[str, int]:
    return {
        "dress": min(trip_days, 5),
        "jumpsuit": min(trip_days, 5),
        "base_layer": min(trip_days, 5),
        "skirt": 2 if trip_days <= 3 else 3,
        "pants": 2 if trip_days <= 3 else 3,
        "shoes": 2,
        "outer_layer": 2,
        "insulation_layer": 2,
        "bag": 2,
        "accessories": 2,
    }


def _travel_primary_sections() -> set[str]:
    return {"dress", "jumpsuit", "skirt", "base_layer"}


def _selected_sections(items: list[dict]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    for item in items:
        item_id = item.get("id")
        if not item_id:
            continue
        section = derive_display_section(item)
        sections.setdefault(section, []).append(str(item_id))
    return sections


def _wardrobe_by_id(items: list[dict]) -> dict[str, dict]:
    return {
        str(item.get("id")): item
        for item in items
        if item.get("id")
    }


def _travel_item_text(item: dict) -> str:
    text = " ".join(
        str(value or "")
        for value in [
            item.get("name"),
            item.get("type"),
            item.get("brand"),
            item.get("style"),
            item.get("occasion"),
            item.get("color"),
        ]
    ).lower()
    return (
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


def _is_rainy_weather(weather: dict) -> bool:
    return any(
        token in str(weather.get("condition") or "").lower()
        for token in ["rain", "rainy", "chuva"]
    )


def _is_cloudy_weather(weather: dict) -> bool:
    return any(
        token in str(weather.get("condition") or "").lower()
        for token in ["cloud", "cloudy", "nublado"]
    )


def _weather_temp(weather: dict, fallback: float = 18) -> float:
    try:
        return float(weather.get("temp", weather.get("temperature", fallback)))
    except (TypeError, ValueError):
        return fallback


def _is_sunny_warm_weather(weather: dict) -> bool:
    condition = str(weather.get("condition") or "").lower()
    return _weather_temp(weather) >= 20 and any(
        token in condition for token in ["sun", "sunny", "clear", "sol"]
    )


def _needs_extra_layer(weather: dict) -> bool:
    condition = str(weather.get("condition") or "").lower()
    temp = _weather_temp(weather)
    return temp <= 19 or any(token in condition for token in ["cloud", "cloudy", "rain", "rainy", "nublado", "chuva"])


def _is_city_trip_destination(destination: str) -> bool:
    text = str(destination or "").lower()
    return not any(token in text for token in ["beach", "praia", "resort", "algarve"])


def _is_open_or_beach_shoe(item: dict) -> bool:
    if derive_display_section(item) != "shoes":
        return False
    text = _travel_item_text(item)
    return any(token in text for token in ["beach", "praia", "sandals", "sandalias", "birks", "birkenstock", "chinelos", "flip flop", "slides"])


def _is_short_pants(item: dict) -> bool:
    if derive_display_section(item) != "pants":
        return False
    text = _travel_item_text(item)
    return any(token in text for token in ["calcoes", "shorts", "short ", "bermuda"])


def _is_light_outer_layer(item: dict) -> bool:
    if derive_display_section(item) != "outer_layer":
        return False
    text = _travel_item_text(item)
    return any(token in text for token in ["light", "leve", "denim", "linen", "linho", "overshirt", "shirt jacket"])


def _is_formal_for_casual_trip(item: dict) -> bool:
    section = derive_display_section(item)
    text = _travel_item_text(item)
    if not any(token in text for token in ["formal", "work", "office", "classico", "classica", "classic", "elegant", "elegante"]):
        return False
    if section == "outer_layer" and any(token in text for token in ["black", "blue", "navy", "gray", "grey", "beige", "brown", "preto", "azul", "cinzento"]):
        return False
    return True


def _travel_constraint_excludes(
    wardrobe_items: list[dict],
    weather: dict,
    requested_style: str,
    destination: str,
) -> set[str]:
    excluded: set[str] = set()
    clean_by_section = _clean_item_ids_by_section(wardrobe_items)
    non_formal_clean_by_section: dict[str, set[str]] = {}
    long_pants_available = False
    closed_shoes_available = False
    for item in wardrobe_items:
        item_id = item.get("id")
        if not item_id:
            continue
        section = derive_display_section(item)
        if str(item.get("status") or "clean").strip().lower() != "clean":
            continue
        if section == "pants" and not _is_short_pants(item):
            long_pants_available = True
        if section == "shoes" and not _is_open_or_beach_shoe(item):
            closed_shoes_available = True
        if not _is_formal_for_casual_trip(item):
            non_formal_clean_by_section.setdefault(section, set()).add(str(item_id))

    temp = _weather_temp(weather)
    rainy = _is_rainy_weather(weather)
    cloudy = _is_cloudy_weather(weather)
    city_trip = _is_city_trip_destination(destination)
    for item in wardrobe_items:
        item_id = item.get("id")
        if not item_id:
            continue
        section = derive_display_section(item)
        text = _travel_item_text(item)
        is_beach_item = "beach" in text or "praia" in text
        if section == "shoes" and _is_open_or_beach_shoe(item) and (
            rainy
            or cloudy
            or temp < 22
            or is_beach_item
        ):
            if closed_shoes_available or is_beach_item or rainy:
                excluded.add(str(item_id))
        if section == "pants" and _is_short_pants(item) and (
            temp < 20
            or rainy
            or city_trip
        ):
            if long_pants_available:
                excluded.add(str(item_id))
        if rainy and section == "shoes" and _is_open_or_beach_shoe(item):
            excluded.add(str(item_id))
        if requested_style.lower() == "casual" and _is_formal_for_casual_trip(item):
            if non_formal_clean_by_section.get(section) or not clean_by_section.get(section):
                excluded.add(str(item_id))
    return excluded


def _best_extra_layer_for_weather(
    wardrobe_items: list[dict],
    weather: dict,
    requested_style: str,
    excluded_ids: set[str],
    used_ids_by_section: dict[str, set[str]],
    trip_days: int,
) -> dict | None:
    caps = _travel_section_caps(trip_days)
    candidates = []
    for item in wardrobe_items:
        item_id = str(item.get("id") or "")
        section = derive_display_section(item)
        if section not in {"outer_layer", "insulation_layer"}:
            continue
        if not item_id or item_id in excluded_ids:
            continue
        if str(item.get("status") or "clean").strip().lower() != "clean":
            continue
        if requested_style.lower() == "casual" and _is_formal_for_casual_trip(item):
            continue
        used_in_section = used_ids_by_section.get(section, set())
        if len(used_in_section) >= caps.get(section, 2) and item_id not in used_in_section:
            continue
        text = _travel_item_text(item)
        score = 0
        if section == "outer_layer":
            score += 3
        if _is_rainy_weather(weather) and any(token in text for token in ["waterproof", "impermeavel", "rain", "chuva", "jacket", "casaco"]):
            score += 4
        if item_id in used_in_section:
            score += 2
        candidates.append((score, item))
    if not candidates:
        return None
    return sorted(candidates, key=lambda pair: pair[0], reverse=True)[0][1]


def _dedupe_items_by_id(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        item_id = str(item.get("id") or "")
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        unique.append(item)
    return unique


def _add_unique_warning(warnings: list[str], warning: str) -> None:
    if warning and warning not in warnings:
        warnings.append(warning)


def _normalize_travel_reasoning(reasoning: str) -> str:
    text = str(reasoning or "").strip()
    if not text:
        return ""
    return re.sub(r"\band\b", "e", text, flags=re.IGNORECASE)


def _travel_candidate_full_items(
    candidate: dict,
    wardrobe_by_item_id: dict[str, dict],
) -> list[dict]:
    items = []
    for candidate_item in candidate.get("items", []):
        item_id = str(candidate_item.get("id") or "")
        source = wardrobe_by_item_id.get(item_id)
        if not source:
            continue
        items.append({
            **source,
            "section": candidate_item.get("section") or derive_display_section(source),
        })
    return _dedupe_items_by_id(items)


def _travel_candidate_reuse_score(
    candidate_items: list[dict],
    used_ids_by_section: dict[str, set[str]],
    previous_sections: dict[str, list[str]],
    exact_outfit_keys: set[tuple[str, ...]],
) -> tuple[float, bool]:
    score = 0.0
    has_reuse = False
    outfit_key = tuple(sorted(str(item.get("id")) for item in candidate_items if item.get("id")))
    if outfit_key in exact_outfit_keys:
        score -= 180.0
        has_reuse = True

    primary_seen = False
    for item in candidate_items:
        item_id = str(item.get("id") or "")
        section = derive_display_section(item)
        if not item_id:
            continue
        if section in _travel_primary_sections():
            primary_seen = True
        if item_id in used_ids_by_section.get(section, set()):
            has_reuse = True
            if section in {"dress", "base_layer", "shoes", "outer_layer"}:
                score -= 95.0
            elif section in {"jumpsuit", "skirt", "pants", "insulation_layer"}:
                score -= 70.0
            elif section in {"bag", "accessories"}:
                score -= 18.0
            else:
                score -= 40.0
        if section == "outer_layer" and item_id in set(previous_sections.get("outer_layer", [])):
            score -= 55.0
        if section == "shoes" and item_id in set(previous_sections.get("shoes", [])):
            score -= 45.0

    if not primary_seen:
        score -= 120.0
    return score, has_reuse


def _select_travel_candidate(
    candidates: list[dict],
    wardrobe_by_item_id: dict[str, dict],
    used_ids_by_section: dict[str, set[str]],
    previous_sections: dict[str, list[str]],
    exact_outfit_keys: set[tuple[str, ...]],
) -> tuple[dict | None, list[dict], bool]:
    best_candidate = None
    best_items: list[dict] = []
    best_score = None
    best_reused = False

    for candidate in candidates:
        candidate_items = _travel_candidate_full_items(candidate, wardrobe_by_item_id)
        if not candidate_items:
            continue
        diversity_score, reused = _travel_candidate_reuse_score(
            candidate_items=candidate_items,
            used_ids_by_section=used_ids_by_section,
            previous_sections=previous_sections,
            exact_outfit_keys=exact_outfit_keys,
        )
        total_score = float(candidate.get("score") or 0) + diversity_score
        print(
            "[TravelPlanner] candidate_score "
            f"id={candidate.get('candidate_id')} base={candidate.get('score')} "
            f"diversity={diversity_score} total={total_score} "
            f"sections={[derive_display_section(item) for item in candidate_items]} "
            f"ids={[item.get('id') for item in candidate_items]}"
        )
        if best_score is None or total_score > best_score:
            best_score = total_score
            best_candidate = candidate
            best_items = candidate_items
            best_reused = reused

    return best_candidate, best_items, best_reused


def _should_add_travel_bag(preferences: dict, requested_style: str) -> bool:
    text = " ".join(
        str(value or "")
        for value in [
            requested_style,
            preferences.get("style"),
            preferences.get("occasion"),
            preferences.get("event"),
        ]
    ).lower()
    return any(token in text for token in ["formal", "date", "dinner", "jantar", "elegant", "elegante", "party"])


def _best_travel_bag(
    wardrobe_items: list[dict],
    outfit_items: list[dict],
    used_ids_by_section: dict[str, set[str]],
    requested_style: str,
    preferences: dict,
) -> dict | None:
    if any(derive_display_section(item) == "bag" for item in outfit_items):
        return None
    if not _should_add_travel_bag(preferences, requested_style):
        return None
    outfit_ids = {str(item.get("id")) for item in outfit_items if item.get("id")}
    candidates = []
    for item in wardrobe_items:
        item_id = str(item.get("id") or "")
        if not item_id or item_id in outfit_ids:
            continue
        if derive_display_section(item) != "bag":
            continue
        if str(item.get("status") or "clean").strip().lower() != "clean":
            continue
        text = _travel_item_text(item)
        score = 8.0
        if item_id not in used_ids_by_section.get("bag", set()):
            score += 10.0
        if any(token in text for token in ["formal", "elegant", "elegante", "leather", "pele", "preto", "black"]):
            score += 4.0
        candidates.append((score, item))
    if not candidates:
        return None
    return sorted(candidates, key=lambda pair: pair[0], reverse=True)[0][1]


def _build_travel_day_reasoning(
    day_number: int,
    outfit_items: list[dict],
    weather: dict,
    requested_style: str,
) -> str:
    item_names = [str(item.get("name") or item.get("type") or "").strip() for item in outfit_items]
    item_names = [name for name in item_names if name]
    if len(item_names) > 1:
        item_phrase = f"{', '.join(item_names[:-1])} e {item_names[-1]}"
    elif item_names:
        item_phrase = item_names[0]
    else:
        item_phrase = "as peças selecionadas"
    style = requested_style or "casual"
    temp = round(_weather_temp(weather))
    condition = weather.get("condition", "tempo previsto")
    return _normalize_travel_reasoning(
        f"Para o Dia {day_number}, escolhi um look {style} com {item_phrase}, "
        f"adequado a {temp}°C e tempo {condition}."
    )


def _trim_travel_outfit_layers(items: list[dict], weather: dict) -> list[dict]:
    deduped = _dedupe_items_by_id(items)
    temp = _weather_temp(weather)
    rainy_or_cloudy = _is_rainy_weather(weather) or _is_cloudy_weather(weather)
    max_items = 5 if temp < 20 or rainy_or_cloudy else 4
    sunny_warm = _is_sunny_warm_weather(weather)

    present_sections = {derive_display_section(item) for item in deduped}
    if "dress" in present_sections:
        required_sections = {"dress", "shoes"}
    elif "jumpsuit" in present_sections:
        required_sections = {"jumpsuit", "shoes"}
    elif "skirt" in present_sections:
        required_sections = {"skirt", "base_layer", "shoes"}
    else:
        required_sections = {"base_layer", "pants", "shoes"}

    if sunny_warm:
        insulation_ids = [
            str(item.get("id")) for item in deduped
            if derive_display_section(item) == "insulation_layer"
        ]
        outer_items = [
            item for item in deduped
            if derive_display_section(item) == "outer_layer"
        ]
        removable_ids = set(insulation_ids)
        if outer_items:
            try:
                has_wind = float(weather.get("wind_speed") or 0) >= 15
            except (TypeError, ValueError):
                has_wind = False
            if not has_wind:
                removable_ids.update(
                    str(item.get("id")) for item in outer_items
                    if not _is_light_outer_layer(item)
                )
        deduped = [
            item for item in deduped
            if str(item.get("id")) not in removable_ids
        ]

        has_insulation = any(
            derive_display_section(item) == "insulation_layer"
            for item in deduped
        )
        has_outer = any(
            derive_display_section(item) == "outer_layer"
            for item in deduped
        )
        if has_insulation and has_outer:
            deduped = [
                item for item in deduped
                if derive_display_section(item) != "insulation_layer"
            ]

    while len(deduped) > max_items:
        remove_index = None
        for section in ["accessories", "bag", "insulation_layer", "outer_layer"]:
            for index in range(len(deduped) - 1, -1, -1):
                if derive_display_section(deduped[index]) == section:
                    if section == "outer_layer" and _is_rainy_weather(weather):
                        continue
                    remove_index = index
                    break
            if remove_index is not None:
                break
        if remove_index is None:
            for index in range(len(deduped) - 1, -1, -1):
                section = derive_display_section(deduped[index])
                if section not in required_sections:
                    remove_index = index
                    break
        if remove_index is None:
            break
        deduped.pop(remove_index)
    return deduped


def _packing_items_unique(packing_by_id: dict[str, dict]) -> list[dict]:
    seen = set()
    unique = []
    for item_id, item in packing_by_id.items():
        normalized_id = str(item_id or item.get("id") or "")
        if not normalized_id or normalized_id in seen:
            continue
        seen.add(normalized_id)
        unique.append(item)
    return unique


def _format_unique_clothing_items(items: list[dict]) -> list[ClothingItemInfo]:
    seen = set()
    formatted = []
    for item in items:
        item_id = str(item.get("id") or "")
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        formatted.append(format_clothing_item(item))
    return formatted


@router.post("/travel-plan")
async def get_candidate_based_travel_plan(
    payload: dict = Body(...),
    user=Depends(get_authenticated_user),
):
    user_id = user.user.id
    destination = (payload.get("destination") or "").strip()
    preferences = dict(payload.get("preferences") or {})
    requested_style = (preferences.get("style") or payload.get("style") or "").strip()
    if requested_style:
        preferences["style"] = requested_style
    warnings = []

    if not destination:
        raise HTTPException(status_code=400, detail="Destination is required.")

    try:
        requested_days = int(payload.get("days") or 1)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Days must be a number.")
    if requested_days < 1:
        raise HTTPException(status_code=400, detail="Duration must be at least 1 day.")
    if requested_days > 5:
        raise HTTPException(status_code=400, detail="Duration must be between 1 and 5 days.")

    print(f"[TravelPlanner] destination={destination}")
    print(f"[TravelPlanner] days={requested_days}")
    print(f"[TravelPlanner] requested_style={requested_style}")

    provided_weather = payload.get("weather_by_day") or payload.get("weather_forecast")
    if isinstance(provided_weather, list) and provided_weather:
        forecast = provided_weather[:requested_days]
    else:
        forecast = await recommendation_service.weather_service.get_weather_forecast(
            destination,
            num_days=requested_days,
        )
        if not forecast:
            forecast = [
                {"temp": 18, "condition": "cloudy", "location": destination}
                for _ in range(requested_days)
            ]

    daily_outfits = []
    packing_by_id = {}
    exact_outfit_keys = set()
    base_excludes = {str(item_id) for item_id in payload.get("exclude_items") or []}
    used_ids_by_section = {
        "dress": set(),
        "jumpsuit": set(),
        "base_layer": set(),
        "skirt": set(),
        "pants": set(),
        "shoes": set(),
        "outer_layer": set(),
        "insulation_layer": set(),
        "bag": set(),
        "accessories": set(),
    }
    wardrobe_items = await recommendation_service.wardrobe_service.get_user_wardrobe(
        user_id=user_id,
        only_clean=False,
        exclude_item_ids=None,
    )
    clean_ids_by_section = _clean_item_ids_by_section(wardrobe_items)
    any_reused = False
    model_used = "candidate_travel_plan"
    previous_sections: dict[str, list[str]] = {}
    wardrobe_by_item_id = _wardrobe_by_id(wardrobe_items)

    for day_index in range(requested_days):
        weather = _travel_day_weather(
            forecast[day_index] if day_index < len(forecast) else {},
            destination,
        )
        if requested_style:
            user_request = (
                f"cria um outfit {requested_style} para viagem em "
                f"{destination} - dia {day_index + 1}"
            )
        else:
            user_request = f"cria um outfit para viagem em {destination} - dia {day_index + 1}"
        excluded_for_rotation = _rotation_excludes_for_day(
            used_ids_by_section=used_ids_by_section,
            clean_ids_by_section=clean_ids_by_section,
            base_excludes=base_excludes,
            trip_days=requested_days,
        )
        constraint_excludes = _travel_constraint_excludes(
            wardrobe_items=wardrobe_items,
            weather=weather,
            requested_style=requested_style,
            destination=destination,
        )
        excluded_for_day = sorted(set(excluded_for_rotation) | constraint_excludes)
        print(f"[TravelPlanner] day={day_index + 1} weather={weather}")
        print(f"[TravelPlanner] day={day_index + 1} excluded_for_rotation={excluded_for_day}")

        parsed_intent = recommendation_service.user_request_parser.parse_request(user_request)
        if requested_style:
            parsed_intent["style"] = [requested_style]
            parsed_intent["requested_style"] = requested_style
        if preferences.get("occasion"):
            parsed_intent["occasion"] = [preferences["occasion"]]

        candidate_result = candidate_outfit_service.generate_candidate_outfits(
            user_id=user_id,
            wardrobe_items=wardrobe_items,
            weather=weather,
            parsed_intent=parsed_intent,
            current_outfit_items=[],
            exclude_items=sorted(base_excludes | constraint_excludes),
            max_candidates=24,
        )

        if not candidate_result.get("success"):
            _add_unique_warning(warnings, TRAVEL_REUSE_WARNING_PT)
            candidate_result = candidate_outfit_service.generate_candidate_outfits(
                user_id=user_id,
                wardrobe_items=wardrobe_items,
                weather=weather,
                parsed_intent=parsed_intent,
                current_outfit_items=[],
                exclude_items=sorted(base_excludes),
                max_candidates=24,
            )

        if not candidate_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=candidate_result.get("error", f"Could not generate outfit for day {day_index + 1}."),
            )

        selected_candidate, outfit_items, candidate_reused = _select_travel_candidate(
            candidates=candidate_result.get("candidates", []),
            wardrobe_by_item_id=wardrobe_by_item_id,
            used_ids_by_section=used_ids_by_section,
            previous_sections=previous_sections,
            exact_outfit_keys=exact_outfit_keys,
        )
        if not selected_candidate or not outfit_items:
            raise HTTPException(
                status_code=500,
                detail=f"Could not select a travel outfit for day {day_index + 1}.",
            )
        if candidate_reused:
            any_reused = True

        selected_sections_before_layer = _selected_sections(outfit_items)
        if (
            _needs_extra_layer(weather)
            and not selected_sections_before_layer.get("outer_layer")
            and not selected_sections_before_layer.get("insulation_layer")
        ):
            extra_layer = _best_extra_layer_for_weather(
                wardrobe_items=wardrobe_items,
                weather=weather,
                requested_style=requested_style,
                excluded_ids=set(excluded_for_day),
                used_ids_by_section=used_ids_by_section,
                trip_days=requested_days,
            )
            if extra_layer and str(extra_layer.get("id")) not in {
                str(item.get("id")) for item in outfit_items if item.get("id")
            }:
                extra_section = derive_display_section(extra_layer)
                outfit_items.append({**extra_layer, "section": extra_section})
        outfit_items = _trim_travel_outfit_layers(outfit_items, weather)
        bag_item = _best_travel_bag(
            wardrobe_items=wardrobe_items,
            outfit_items=outfit_items,
            used_ids_by_section=used_ids_by_section,
            requested_style=requested_style,
            preferences=preferences,
        )
        if bag_item and len(outfit_items) < 5:
            outfit_items.append({**bag_item, "section": "bag"})

        outfit_key = tuple(sorted(str(item.get("id")) for item in outfit_items if item.get("id")))
        if outfit_key in exact_outfit_keys:
            any_reused = True
        exact_outfit_keys.add(outfit_key)

        for item in outfit_items:
            if item.get("id"):
                item_id = str(item["id"])
                packing_by_id[item_id] = item
                section = derive_display_section(item)
                if section in used_ids_by_section:
                    if item_id in used_ids_by_section[section]:
                        any_reused = True
                    used_ids_by_section[section].add(item_id)

        selected_item_ids = [item.get("id") for item in outfit_items if item.get("id")]
        selected_sections = _selected_sections(outfit_items)
        previous_sections = selected_sections
        print(f"[TravelPlanner] day={day_index + 1} selected_sections={selected_sections}")
        print(f"[TravelPlanner] day={day_index + 1} selected_item_ids={selected_item_ids}")

        daily_outfits.append({
            "day": day_index + 1,
            "weather": weather,
            "outfit": {
                "items": [format_clothing_item(item) for item in outfit_items],
                "reasoning": _build_travel_day_reasoning(
                    day_number=day_index + 1,
                    outfit_items=outfit_items,
                    weather=weather,
                    requested_style=requested_style,
                ),
            },
            "model_used": "candidate_travel_plan",
        })

    packing_items = _format_unique_clothing_items(
        _packing_items_unique(packing_by_id)
    )
    packing_unique_item_ids = [item.id for item in packing_items]
    print(f"[TravelPlanner] packing_unique_item_ids={packing_unique_item_ids}")

    if any_reused:
        _add_unique_warning(warnings, TRAVEL_REUSE_WARNING_PT)

    return {
        "success": True,
        "destination": destination,
        "days": requested_days,
        "packing_items": packing_items,
        "daily_outfits": daily_outfits,
        "warnings": warnings,
        "model_used": model_used,
        "generated_at": datetime.now().isoformat(),
    }


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
