"""
Focused tests for final outfit behavior and user-facing output.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "test")
sys.path.insert(0, str(Path(__file__).parents[2]))

from services.constraint_matching_service import ConstraintMatchingService
from services.item_scoring_service import ItemScoringService
from services.data_preparation_service import AIReadyContext, AIReadyItem, AIReadyWeather, DataPreparationService
from services.recommendation_service import RecommendationService
from services.user_request_parser import UserRequestParser
from services.vlm_service import MockVLMService


def test_yellow_sneakers_request_is_matched_and_reasoning_is_clean():
    parser = UserRequestParser()
    constraints = parser.parse_request("outfit com sapatilhas amarelas")
    assert constraints["must_include"]["type"] == ["sneakers"]
    assert constraints["must_include"]["color"] == ["yellow"]

    wardrobe = [
        {"id": "shoe-yellow", "name": "Yellow Sneakers", "type": "sneakers", "color": "yellow"}
    ]
    matches, missing = ConstraintMatchingService().find_matching_items(
        constraints, wardrobe
    )
    assert not missing
    assert matches[0]["id"] == "shoe-yellow"

    service = RecommendationService(vlm_service=MockVLMService())
    reasoning = service.build_clean_reasoning(
        validated_items=[
            SimpleNamespace(name="White Tee", type="t-shirt", layer=1, style="casual"),
            SimpleNamespace(name="Yellow Sneakers", type="sneakers", layer=3, style="casual"),
        ],
        weather={"temperature": 20, "condition": "sunny"},
        must_include_items=[{"id": "shoe-yellow", "name": "Yellow Sneakers"}],
        user_request_text="outfit com sapatilhas amarelas",
    )

    assert "Yellow Sneakers as requested" in reasoning
    assert "debug" not in reasoning.lower()
    assert "validation" not in reasoning.lower()
    assert "raw" not in reasoning.lower()


def test_yellow_sneakers_match_color_field_and_name_fallback():
    constraints = UserRequestParser().parse_request("sapatilhas amarelas")
    matcher = ConstraintMatchingService()

    wardrobe_with_color = [
        {"id": "yellow-field", "name": "Campus 00s", "type": "Calçado", "color": "yellow"}
    ]
    matches, missing = matcher.find_matching_items(constraints, wardrobe_with_color)
    assert not missing
    assert matches[0]["id"] == "yellow-field"

    wardrobe_name_fallback = [
        {"id": "yellow-name", "name": "Sapatilhas Amarelas", "type": "Calçado"}
    ]
    matches, missing = matcher.find_matching_items(constraints, wardrobe_name_fallback)
    assert not missing
    assert matches[0]["id"] == "yellow-name"


def test_color_type_request_matches_inferred_color_not_unknown_color():
    constraints = UserRequestParser().parse_request("quero um look com um casaco verde")
    matcher = ConstraintMatchingService()

    wardrobe_with_inferred_color = [
        {
            "id": "green-jacket",
            "name": "Zara",
            "type": "Casaco",
            "color": "",
            "inferred_color": "green",
        }
    ]

    matches, missing = matcher.find_matching_items(
        constraints,
        wardrobe_with_inferred_color,
    )
    assert not missing
    assert matches[0]["id"] == "green-jacket"

    wardrobe_unknown_color = [
        {
            "id": "unknown-jacket",
            "name": "Zara",
            "type": "Casaco",
            "color": "",
        }
    ]
    matches, missing = matcher.find_matching_items(constraints, wardrobe_unknown_color)
    assert not matches
    assert missing

    wardrobe_black = [
        {
            "id": "black-jacket",
            "name": "Work Jacket",
            "type": "Casaco",
            "color": "black",
        }
    ]
    matches, missing = matcher.find_matching_items(constraints, wardrobe_black)
    assert not matches
    assert missing


def test_color_field_mismatch_does_not_fallback_to_name():
    constraints = UserRequestParser().parse_request("sapatilhas amarelas")
    wardrobe = [
        {
            "id": "bad-metadata",
            "name": "Sapatilhas Amarelas",
            "type": "Calçado",
            "color": "blue",
        }
    ]

    matches, missing = ConstraintMatchingService().find_matching_items(
        constraints, wardrobe
    )
    assert not matches
    assert missing


def test_formal_request_sets_style_and_matches_formal_items():
    constraints = UserRequestParser().parse_request("outfit mais formal")
    assert constraints["style"] == ["formal"]

    service = RecommendationService(vlm_service=MockVLMService())
    formal_items = [
        SimpleNamespace(name="Work Jacket", type="blazer", layer=3, style="formal"),
        SimpleNamespace(name="Oxford Shirt", type="shirt", layer=1, style="formal"),
    ]
    assert service._items_match_requested_style(formal_items, "formal")

    reasoning = service.build_clean_reasoning(
        validated_items=formal_items,
        weather={"temperature": 16, "condition": "cloudy"},
        preferences={"style": "formal"},
    )
    assert "formal" in reasoning.lower()


def test_formal_request_rejects_mostly_casual_outfit():
    service = RecommendationService(vlm_service=MockVLMService())
    casual_items = [
        SimpleNamespace(name="Graphic Tee", type="t-shirt", layer=1, style="casual"),
        SimpleNamespace(name="Yellow Sneakers", type="sneakers", layer=3, style="casual"),
    ]
    assert not service._items_match_requested_style(casual_items, "formal")


def test_missing_green_jacket_message_is_specific():
    constraints = UserRequestParser().parse_request("da me um look com um casaco verde")
    service = RecommendationService(vlm_service=MockVLMService())

    assert (
        service._missing_constraint_message(constraints)
        == "I could not find a green jacket in your wardrobe."
    )


def test_daily_filter_excludes_temperature_mismatch_before_llava_unless_mandatory():
    prep = DataPreparationService()
    sobretudo = AIReadyItem(
        {
            "id": "sobretudo",
            "name": "Sobretudo",
            "type": "Casaco",
            "layer": 3,
            "status": "clean",
            "temp_min": -6,
            "temp_max": 10,
        }
    )
    yellow_sneakers = AIReadyItem(
        {
            "id": "yellow-shoes",
            "name": "Sapatilhas Amarelas",
            "type": "Calçado",
            "color": "yellow",
            "layer": 3,
            "status": "clean",
            "temp_min": 10,
            "temp_max": 30,
        }
    )

    filtered = prep._filter_wardrobe_for_daily(
        [sobretudo, yellow_sneakers],
        temperature=17,
        weather_condition="cloudy",
    )
    assert [item.id for item in filtered] == ["yellow-shoes"]

    filtered_with_must_include = prep._filter_wardrobe_for_daily(
        [sobretudo, yellow_sneakers],
        temperature=17,
        weather_condition="cloudy",
        must_include_ids=["sobretudo"],
    )
    assert "sobretudo" in [item.id for item in filtered_with_must_include]


def test_formal_filter_keeps_formal_alternatives_over_sport_items():
    prep = DataPreparationService()
    items = [
        AIReadyItem(
            {
                "id": "jersey",
                "name": "Football Jersey",
                "type": "Jersey",
                "layer": 1,
                "status": "clean",
                "temp_min": 10,
                "temp_max": 30,
            }
        ),
        AIReadyItem(
            {
                "id": "jordan",
                "name": "Air Jordan",
                "type": "Calçado",
                "layer": 3,
                "status": "clean",
                "temp_min": 10,
                "temp_max": 30,
            }
        ),
        AIReadyItem(
            {
                "id": "shirt",
                "name": "Oxford Shirt",
                "type": "Camisa",
                "style": "formal",
                "layer": 1,
                "status": "clean",
                "temp_min": 10,
                "temp_max": 30,
            }
        ),
        AIReadyItem(
            {
                "id": "boots",
                "name": "Leather Boots",
                "type": "boots",
                "style": "formal",
                "layer": 3,
                "status": "clean",
                "temp_min": 0,
                "temp_max": 25,
            }
        ),
    ]

    filtered = prep._filter_wardrobe_for_daily(
        items,
        temperature=17,
        weather_condition="cloudy",
        user_preferences={"style": "formal"},
    )
    filtered_ids = {item.id for item in filtered}

    assert "shirt" in filtered_ids
    assert "boots" in filtered_ids
    assert "jersey" not in filtered_ids
    assert "jordan" not in filtered_ids


def test_candidate_selection_can_vary_when_alternatives_exist():
    service = ItemScoringService()
    items = [
        {
            "id": f"item-{index}",
            "name": f"Item {index}",
            "type": "t-shirt",
            "layer": 1,
            "status": "clean",
            "temp_min": 10,
            "temp_max": 25,
            "usage_metrics": {"usage_frequency_last_7_days": 0},
        }
        for index in range(8)
    ]

    with patch("random.shuffle", lambda values: None):
        first = service.score_and_filter_items(items, temperature=18, max_per_layer=4)
    with patch("random.shuffle", lambda values: values.reverse()):
        second = service.score_and_filter_items(items, temperature=18, max_per_layer=4)

    first_ids = [item["id"] for item in first[1]]
    second_ids = [item["id"] for item in second[1]]
    assert first_ids != second_ids


def test_followup_replaces_only_shoes_and_keeps_rest():
    service = RecommendationService(vlm_service=MockVLMService())
    parser = UserRequestParser()
    parsed = parser.parse_request("troca só as sapatilhas")

    current_items = [
        {"id": "tee", "name": "White Tee", "type": "t-shirt", "layer": 1, "status": "clean"},
        {"id": "pants", "name": "Blue Jeans", "type": "jeans", "layer": 2, "status": "clean"},
        {"id": "old-shoes", "name": "Old Sneakers", "type": "sneakers", "layer": 3, "status": "clean"},
    ]
    plan = service._build_followup_plan(parsed, current_items)

    assert plan["keep_ids"] == ["tee", "pants"]
    assert plan["replace_ids"] == ["old-shoes"]
    assert plan["replace_sections"] == ["shoes"]

    context = AIReadyContext(
        user_id="u1",
        recommendation_type="daily",
        weather=AIReadyWeather({"temperature": 18, "condition": "sunny"}),
        wardrobe_by_layer={
            1: [AIReadyItem(current_items[0])],
            2: [AIReadyItem(current_items[1])],
            3: [
                AIReadyItem(current_items[2]),
                AIReadyItem({"id": "new-shoes", "name": "Clean Sneakers", "type": "sneakers", "layer": 3, "status": "clean"}),
            ],
        },
        user_constraints={"must_include_ids": ["tee", "pants"], "preferences": {}},
    )
    response = service._build_followup_response(
        ai_context=context,
        current_items=current_items,
        keep_ids=plan["keep_ids"],
        replace_sections=plan["replace_sections"],
        parsed_constraints=parsed,
        weather={"temperature": 18, "condition": "sunny"},
        preferences={},
        must_include_items=[],
    )

    response_ids = [item["id"] for item in response["outfit"]["items"]]
    assert response_ids == ["tee", "pants", "new-shoes"]
    assert "replaced only the shoes" in response["outfit"]["reasoning"]
