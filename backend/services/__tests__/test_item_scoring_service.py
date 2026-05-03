"""
Tests for ItemScoringService candidate ranking.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from item_scoring_service import ItemScoringService


def make_item(item_id, layer=1, status="clean", temp_min=10, temp_max=25, usage_7d=0):
    return {
        "id": item_id,
        "name": f"Item {item_id}",
        "type": "t-shirt" if layer == 1 else "jeans",
        "layer": layer,
        "status": status,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "usage_metrics": {
            "usage_frequency_last_7_days": usage_7d,
            "usage_frequency_last_30_days": usage_7d,
            "is_overused": usage_7d >= 3,
        },
    }


def test_dirty_and_excluded_items_are_removed():
    service = ItemScoringService()
    items = [
        make_item("clean"),
        make_item("dirty", status="dirty"),
        make_item("excluded"),
    ]

    result = service.score_and_filter_items(
        items,
        temperature=18,
        exclude_ids=["excluded"],
    )

    kept_ids = {item["id"] for layer_items in result.values() for item in layer_items}
    assert "clean" in kept_ids
    assert "dirty" not in kept_ids
    assert "excluded" not in kept_ids
    assert service.score_item(items[1], 18) == service.excluded_score
    assert service.score_item(items[2], 18, exclude_ids={"excluded"}) == service.excluded_score


def test_must_include_survives_temperature_penalty():
    service = ItemScoringService()
    cold_item = make_item("must", temp_min=-20, temp_max=-5, usage_7d=6)

    result = service.score_and_filter_items(
        [cold_item],
        temperature=30,
        must_include_ids=["must"],
    )

    kept = result[1][0]
    assert kept["id"] == "must"
    assert kept["score"] > 400


def test_filters_low_scores_and_keeps_top_five_per_layer():
    service = ItemScoringService()
    items = [
        make_item(f"good-{idx}", layer=1, temp_min=10, temp_max=25, usage_7d=0)
        for idx in range(7)
    ]
    items.append(make_item("bad-temp", layer=1, temp_min=-30, temp_max=-20, usage_7d=8))

    result = service.score_and_filter_items(items, temperature=18, max_per_layer=5)
    kept_ids = [item["id"] for item in result[1]]

    assert len(kept_ids) == 5
    assert "bad-temp" not in kept_ids


def test_formal_style_boosts_formal_items_and_penalizes_casual_items():
    service = ItemScoringService()
    shirt = {
        **make_item("shirt"),
        "name": "Camisa Oxford",
        "type": "Camisa",
        "style": "formal",
    }
    sneakers = {
        **make_item("sneakers"),
        "name": "Yellow Sneakers",
        "type": "sneakers",
        "style": "casual",
    }
    jersey = {
        **make_item("jersey"),
        "name": "Training Jersey",
        "type": "jersey",
    }

    shirt_score = service.score_item(shirt, 18, style_preference="formal")
    sneakers_score = service.score_item(sneakers, 18, style_preference="formal")
    jersey_score = service.score_item(jersey, 18, style_preference="formal")

    assert shirt_score > sneakers_score
    assert shirt_score > jersey_score


def test_casual_style_boosts_sneakers_and_hoodies():
    service = ItemScoringService()
    sneakers = {
        **make_item("sneakers"),
        "name": "Daily Sneakers",
        "type": "sneakers",
    }
    blazer = {
        **make_item("blazer"),
        "name": "Work Blazer",
        "type": "blazer",
        "style": "formal",
    }

    sneakers_score = service.score_item(sneakers, 18, style_preference="casual")
    blazer_score = service.score_item(blazer, 18, style_preference="casual")

    assert sneakers_score > blazer_score
