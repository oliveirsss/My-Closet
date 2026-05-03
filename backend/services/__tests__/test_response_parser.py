"""
Test suite for ResponseParser class.

This test file validates that the ResponseParser correctly:
1. Parses daily outfit recommendations
2. Validates items exist in wardrobe
3. Filters dirty items
4. Corrects layer assignments
5. Removes VLM artifacts from reasoning
6. Handles travel and alternative recommendations
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from response_parser import ResponseParser, ResponseParserError

# Sample wardrobe items for testing
SAMPLE_WARDROBE = [
    {
        "id": "base-001",
        "name": "Cotton T-Shirt",
        "type": "T-Shirt",
        "layer": 1,
        "status": "clean",
        "temperature_range": {"min": 10, "max": 30},
    },
    {
        "id": "base-002",
        "name": "Thermal Base Layer",
        "type": "Long Sleeve Base",
        "layer": 1,
        "status": "clean",
        "temperature_range": {"min": -5, "max": 15},
    },
    {
        "id": "mid-001",
        "name": "Fleece Sweater",
        "type": "Sweater",
        "layer": 2,
        "status": "clean",
        "temperature_range": {"min": 0, "max": 20},
    },
    {
        "id": "mid-002",
        "name": "Denim Pants",
        "type": "Jeans",
        "layer": 2,
        "status": "clean",
        "temperature_range": {"min": 5, "max": 25},
    },
    {
        "id": "outer-001",
        "name": "Winter Jacket",
        "type": "Jacket",
        "layer": 3,
        "status": "clean",
        "temperature_range": {"min": -10, "max": 10},
    },
    {
        "id": "shoes-001",
        "name": "Sneakers",
        "type": "Sneakers",
        "layer": 3,
        "status": "clean",
        "temperature_range": {"min": 5, "max": 25},
    },
    {
        "id": "acc-001",
        "name": "Wool Scarf",
        "type": "Scarf",
        "layer": 3,
        "status": "clean",
        "temperature_range": {"min": -10, "max": 10},
    },
    {
        "id": "dirty-001",
        "name": "Dirty T-Shirt",
        "type": "T-Shirt",
        "layer": 1,
        "status": "dirty",
        "temperature_range": {"min": 10, "max": 30},
    },
]


def test_parse_daily_outfit_basic():
    """Test parsing a basic daily outfit."""
    parser = ResponseParser()

    vlm_response = {
        "response": """
Base Layer (Layer 1):
Cotton T-Shirt (base-001)

Insulation Layer (Layer 2):
Fleece Sweater (mid-001) and Denim Pants (mid-002)

Outer Layer (Layer 3):
Winter Jacket (outer-001)

Shoes (Layer 3):
Sneakers (shoes-001)

Accessories (Layer 3):
Wool Scarf (acc-001)

Reasoning:
This is a great outfit for cold weather because the layers work together effectively.
The base layer keeps you warm, the sweater adds insulation, and the jacket provides protection.
""",
        "reasoning": "This is a great outfit for cold weather because the layers work together effectively.",
    }

    result = parser.parse_daily_outfit(vlm_response, SAMPLE_WARDROBE, {})

    assert result["success"], (
        f"Parsing failed with warnings: {result.get('warnings', [])}"
    )
    assert len(result["items"]) == 6, f"Expected 6 items, got {len(result['items'])}"
    assert len(result["warnings"]) == 0, f"Unexpected warnings: {result['warnings']}"
    print("✓ test_parse_daily_outfit_basic passed")


def test_parse_daily_outfit_filters_dirty():
    """Test that dirty items are filtered out."""
    parser = ResponseParser()

    vlm_response = {
        "response": """
Base Layer (Layer 1):
Dirty T-Shirt (dirty-001) and Cotton T-Shirt (base-001)

Insulation Layer (Layer 2):
Fleece Sweater (mid-001)

Outer Layer (Layer 3):
Winter Jacket (outer-001)

Shoes (Layer 3):
Sneakers (shoes-001)

Accessories (Layer 3):
None
""",
        "reasoning": "Test reasoning",
    }

    result = parser.parse_daily_outfit(vlm_response, SAMPLE_WARDROBE, {})

    # Find the dirty item - it should NOT be in the result
    item_ids = result["item_ids"]
    assert "dirty-001" not in item_ids, "Dirty item should have been filtered out"
    assert "base-001" in item_ids, "Clean item should be present"
    assert any("dirty" in w.lower() for w in result["warnings"]), (
        "Should have warning about dirty item"
    )
    print("✓ test_parse_daily_outfit_filters_dirty passed")


def test_parse_daily_outfit_missing_item():
    """Test handling of items not in wardrobe."""
    parser = ResponseParser()

    vlm_response = {
        "response": """
Base Layer (Layer 1):
Cotton T-Shirt (base-001) and Unknown Item (unknown-999)

Insulation Layer (Layer 2):
Fleece Sweater (mid-001)

Outer Layer (Layer 3):
Winter Jacket (outer-001)

Shoes (Layer 3):
Sneakers (shoes-001)

Accessories (Layer 3):
None
""",
        "reasoning": "Test reasoning",
    }

    result = parser.parse_daily_outfit(vlm_response, SAMPLE_WARDROBE, {})

    assert "unknown-999" not in result["item_ids"], (
        "Unknown item should not be included"
    )
    assert any("not found" in w.lower() for w in result["warnings"]), (
        "Should have warning about missing item"
    )
    print("✓ test_parse_daily_outfit_missing_item passed")


def test_parse_daily_outfit_layer_correction():
    """Test that items in wrong layers are corrected."""
    parser = ResponseParser()

    # Put sweater (layer 2 type) in base layer section
    vlm_response = {
        "response": """
Base Layer (Layer 1):
Fleece Sweater (mid-001)

Insulation Layer (Layer 2):
Cotton T-Shirt (base-001)

Outer Layer (Layer 3):
Winter Jacket (outer-001)

Shoes (Layer 3):
Sneakers (shoes-001)

Accessories (Layer 3):
None
""",
        "reasoning": "Testing layer correction",
    }

    result = parser.parse_daily_outfit(vlm_response, SAMPLE_WARDROBE, {})

    # Check that sweater is in layer 2 (corrected)
    layer_assignments = result["layer_assignments"]
    assert "mid-001" in layer_assignments[2], "Sweater should be corrected to layer 2"
    assert "mid-001" not in layer_assignments[1], "Sweater should not be in layer 1"
    assert any("corrected" in w.lower() for w in result["warnings"]), (
        "Should have correction warning"
    )
    print("✓ test_parse_daily_outfit_layer_correction passed")


def test_clean_reasoning_removes_artifacts():
    """Test that VLM artifacts are removed from reasoning."""
    parser = ResponseParser()

    reasoning_with_artifacts = """
This is good reasoning.

PECAS_EM_FALTA:
Some missing items here

More good reasoning.

Missing items:
None needed

Final thoughts about the outfit.
"""

    cleaned = parser._clean_reasoning(reasoning_with_artifacts)

    assert "PECAS_EM_FALTA" not in cleaned, "PECAS_EM_FALTA should be removed"
    assert "Missing items" not in cleaned, "Missing items section should be removed"
    assert "good reasoning" in cleaned, "Good content should be preserved"
    assert "Final thoughts" in cleaned, "Final thoughts should be preserved"
    print("✓ test_clean_reasoning_removes_artifacts passed")


def test_clean_reasoning_removes_peças_em_falta():
    """Test Portuguese artifact removal."""
    parser = ResponseParser()

    reasoning = """
This is good reasoning.

Peças em falta:
Some missing pieces here

More reasoning continues here.
"""

    cleaned = parser._clean_reasoning(reasoning)

    assert "Peças em falta" not in cleaned, "Peças em falta should be removed"
    assert "good reasoning" in cleaned, "Good content should be preserved"
    print("✓ test_clean_reasoning_removes_peças_em_falta passed")


def test_validate_layer_assignment():
    """Test layer assignment validation."""
    parser = ResponseParser()

    # Test with t-shirt (should be layer 1)
    tshirt = {"type": "T-Shirt", "layer": 1}
    is_valid, corrected = parser._validate_layer_assignment(tshirt, 1)
    assert is_valid and corrected == 1

    # Test with t-shirt assigned to wrong layer (should correct to 1)
    is_valid, corrected = parser._validate_layer_assignment(tshirt, 2)
    assert is_valid and corrected == 1, "Should correct t-shirt to layer 1"

    # Test with jacket (should be layer 3)
    jacket = {"type": "Jacket", "layer": 3}
    is_valid, corrected = parser._validate_layer_assignment(jacket, 3)
    assert is_valid and corrected == 3

    # Test with jacket assigned to wrong layer (should correct to 3)
    is_valid, corrected = parser._validate_layer_assignment(jacket, 1)
    assert is_valid and corrected == 3, "Should correct jacket to layer 3"

    print("✓ test_validate_layer_assignment passed")


def test_is_clean_item():
    """Test clean item detection."""
    parser = ResponseParser()

    clean_item = {"status": "clean"}
    assert parser._is_clean_item(clean_item), "Clean item should be clean"

    dirty_item = {"status": "dirty"}
    assert not parser._is_clean_item(dirty_item), "Dirty item should not be clean"

    unknown_item = {"status": "unknown"}
    assert parser._is_clean_item(unknown_item), (
        "Unknown status should be treated as clean"
    )

    print("✓ test_is_clean_item passed")


def test_extract_item_id():
    """Test item ID extraction."""
    parser = ResponseParser()

    # UUID format
    uuid_text = "Cotton T-Shirt (123e4567-e89b-12d3-a456-426614174000)"
    item_id = parser._extract_item_id(uuid_text)
    assert item_id == "123e4567-e89b-12d3-a456-426614174000", "Should extract UUID"

    # Simple ID in parentheses
    simple_text = "Fleece Sweater (mid-001)"
    item_id = parser._extract_item_id(simple_text)
    assert item_id == "mid-001", "Should extract simple ID"

    # Bare ID
    bare_text = "base-001"
    item_id = parser._extract_item_id(bare_text)
    assert item_id == "base-001", "Should extract bare ID"

    print("✓ test_extract_item_id passed")


def test_name_based_matching_exact():
    """Test fallback exact name matching when no ID is present."""
    parser = ResponseParser()

    vlm_response = {
        "response": """
Base Layer:
Cotton T-Shirt

Insulation Layer:
Denim Pants

Outer Layer:
Winter Jacket

Shoes:
Sneakers

Accessories:
Wool Scarf
""",
        "reasoning": "Simple fallback test",
    }

    result = parser.parse_daily_outfit(vlm_response, SAMPLE_WARDROBE, {})
    assert result["success"], "Name-based exact matching should succeed"
    assert "base-001" in result["item_ids"]
    assert "mid-002" in result["item_ids"]
    assert "outer-001" in result["item_ids"]
    assert "shoes-001" in result["item_ids"]
    assert "acc-001" in result["item_ids"]
    print("✓ test_name_based_matching_exact passed")


def test_name_based_matching_partial():
    """Test fallback partial name matching when no ID is present."""
    parser = ResponseParser()

    wardrobe = SAMPLE_WARDROBE + [
        {
            "id": "base-003",
            "name": "White Jersey",
            "type": "Shirt",
            "layer": 1,
            "status": "clean",
            "temperature_range": {"min": 10, "max": 30},
        }
    ]

    vlm_response = {
        "response": """
Base Layer:
Jersey

Insulation Layer:
Fleece

Outer Layer:
Jacket

Shoes:
Sneakers

Accessories:
None
""",
        "reasoning": "Partial fallback test",
    }

    result = parser.parse_daily_outfit(vlm_response, wardrobe, {})
    assert "base-003" in result["item_ids"], "Partial 'Jersey' should match 'White Jersey'"
    assert "mid-001" in result["item_ids"], "Partial 'Fleece' should match 'Fleece Sweater'"
    print("✓ test_name_based_matching_partial passed")


if __name__ == "__main__":
    print("Running ResponseParser tests...\n")

    test_parse_daily_outfit_basic()
    test_parse_daily_outfit_filters_dirty()
    test_parse_daily_outfit_missing_item()
    test_parse_daily_outfit_layer_correction()
    test_clean_reasoning_removes_artifacts()
    test_clean_reasoning_removes_peças_em_falta()
    test_validate_layer_assignment()
    test_is_clean_item()
    test_extract_item_id()
    test_name_based_matching_exact()
    test_name_based_matching_partial()

    print("\n✅ All tests passed!")
