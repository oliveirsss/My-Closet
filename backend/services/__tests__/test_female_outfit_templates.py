import os
import sys
from pathlib import Path

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "test")
sys.path.insert(0, str(Path(__file__).parents[2]))

from services.candidate_outfit_service import CandidateOutfitService


def _item(item_id, name, item_type, **extra):
    return {
        "id": item_id,
        "name": name,
        "type": item_type,
        "status": "clean",
        "temp_min": 0,
        "temp_max": 35,
        **extra,
    }


def _generate(items, parsed_intent=None):
    return CandidateOutfitService().generate_candidate_outfits(
        user_id="u1",
        wardrobe_items=items,
        weather={"temperature": 18, "condition": "clear"},
        parsed_intent=parsed_intent or {},
        max_candidates=4,
    )


def _best_sections(result):
    assert result["success"], result.get("error")
    return [item["section"] for item in result["candidates"][0]["items"]]


def test_dress_and_shoes_generate_dress_template_without_pants():
    result = _generate([
        _item("dress", "Black Dress", "dress", style="formal"),
        _item("shoes", "Black Heels", "shoes", style="formal"),
        _item("pants", "Blue Jeans", "jeans"),
    ])

    sections = _best_sections(result)
    assert "dress" in sections
    assert "shoes" in sections
    assert "pants" not in sections
    assert result["candidates"][0]["metadata"]["template_used"] == "dress_outfit"


def test_skirt_top_and_shoes_generate_skirt_template():
    result = _generate([
        _item("skirt", "Pleated Skirt", "skirt"),
        _item("top", "White Blouse", "blouse"),
        _item("shoes", "Leather Shoes", "shoes"),
    ])

    sections = _best_sections(result)
    assert {"skirt", "base_layer", "shoes"}.issubset(set(sections))
    assert result["candidates"][0]["metadata"]["template_used"] == "skirt_outfit"


def test_jumpsuit_and_shoes_generate_jumpsuit_template_without_pants_or_base():
    result = _generate([
        _item("jumpsuit", "Navy Jumpsuit", "jumpsuit"),
        _item("shoes", "Black Sandals", "sandals"),
        _item("top", "White Tee", "t-shirt"),
        _item("pants", "Black Pants", "pants"),
    ])

    sections = _best_sections(result)
    assert "jumpsuit" in sections
    assert "shoes" in sections
    assert "pants" not in sections
    assert "base_layer" not in sections
    assert result["candidates"][0]["metadata"]["template_used"] == "jumpsuit_outfit"


def test_formal_female_look_can_include_blazer_and_bag():
    result = _generate(
        [
            _item("dress", "Formal Dress", "dress", style="formal"),
            _item("shoes", "Oxford Heels", "shoes", style="formal"),
            _item("blazer", "Black Blazer", "blazer", style="formal"),
            _item("bag", "Leather Bag", "bag", style="formal"),
        ],
        {"style": ["formal"], "occasion": ["dinner"]},
    )

    sections = _best_sections(result)
    assert {"dress", "shoes", "outer_layer", "bag"}.issubset(set(sections))
    assert result["candidates"][0]["metadata"]["template_used"] == "dress_outfit"


def test_wardrobe_without_female_items_still_generates_standard_outfit():
    result = _generate([
        _item("tee", "White Tee", "t-shirt"),
        _item("pants", "Blue Jeans", "jeans"),
        _item("shoes", "White Sneakers", "sneakers"),
        _item("jacket", "Denim Jacket", "jacket"),
    ])

    sections = _best_sections(result)
    assert {"base_layer", "pants", "shoes"}.issubset(set(sections))
    assert "dress" not in sections
    assert "skirt" not in sections
    assert "jumpsuit" not in sections
    assert result["candidates"][0]["metadata"]["template_used"] == "standard_outfit"
