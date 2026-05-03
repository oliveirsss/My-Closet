import os
import sys
from pathlib import Path

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "test")
sys.path.insert(0, str(Path(__file__).parents[2]))

from services.user_request_parser import UserRequestParser, parse_user_intent


def test_parse_user_intent_detects_yellow_sneakers_with_accents():
    assert parse_user_intent("TÉNIS amarelos") == {
        "requested_colors": ["yellow"],
        "requested_types": ["sneakers"],
        "requested_style": None,
        "must_include_items": [{"type": "sneakers", "color": "yellow"}],
        "avoid_items": [],
        "replace_sections": [],
        "keep_sections": [],
        "mode": "new_outfit",
    }


def test_parse_user_intent_detects_style():
    assert parse_user_intent("outfit formal") == {
        "requested_colors": [],
        "requested_types": [],
        "requested_style": "formal",
        "must_include_items": [],
        "avoid_items": [],
        "replace_sections": [],
        "keep_sections": [],
        "mode": "new_outfit",
    }
    assert parse_user_intent("look desportivo") == {
        "requested_colors": [],
        "requested_types": [],
        "requested_style": "sporty",
        "must_include_items": [],
        "avoid_items": [],
        "replace_sections": [],
        "keep_sections": [],
        "mode": "new_outfit",
    }


def test_parse_user_intent_detects_avoid_item():
    assert parse_user_intent("não quero Air Jordan") == {
        "requested_colors": [],
        "requested_types": [],
        "requested_style": None,
        "must_include_items": [],
        "avoid_items": [{"name": "Air Jordan"}],
        "replace_sections": [],
        "keep_sections": [],
        "mode": "avoid_piece",
    }


def test_legacy_parse_request_keeps_backend_shape():
    parsed = UserRequestParser().parse_request(
        "não quero Air Jordan com sapatilhas amarelas"
    )

    assert parsed["must_include"]["type"] == ["sneakers"]
    assert parsed["must_include"]["color"] == ["yellow"]
    assert parsed["avoid"] == {"name": "Air Jordan"}


def test_generic_intent_parser_examples():
    parser = UserRequestParser()

    assert parser.parse_user_intent("dá-me um look com casaco azul")["must_include_items"] == [
        {"type": "jacket", "color": "blue"}
    ]
    assert parser.parse_user_intent("quero um outfit mais formal")["requested_style"] == "formal"

    replace_shoes = parser.parse_user_intent("troca só as sapatilhas")
    assert replace_shoes["replace_sections"] == ["shoes"]
    assert replace_shoes["mode"] == "replace_piece"

    keep_pants = parser.parse_user_intent("mantém as calças e muda o resto")
    assert keep_pants["keep_sections"] == ["pants"]
    assert keep_pants["mode"] == "keep_piece"

    avoid_black = parser.parse_user_intent("não quero peças pretas")
    assert avoid_black["avoid_items"] == [{"color": "black"}]
    assert avoid_black["mode"] == "avoid_piece"


if __name__ == "__main__":
    test_parse_user_intent_detects_yellow_sneakers_with_accents()
    test_parse_user_intent_detects_style()
    test_parse_user_intent_detects_avoid_item()
    test_legacy_parse_request_keeps_backend_shape()
