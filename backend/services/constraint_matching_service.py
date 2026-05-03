"""
Constraint Matching Service

Matches parsed user request constraints with actual wardrobe items.

Provides:
- Finding items that match color/type constraints
- Finding items by name
- Building MUST_INCLUDE items list
- Validating that required items exist
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


COLOR_ALIASES = {
    "amarelo": "yellow",
    "amarelos": "yellow",
    "amarela": "yellow",
    "amarelas": "yellow",
    "azul": "blue",
    "azuis": "blue",
    "vermelho": "red",
    "vermelhos": "red",
    "vermelha": "red",
    "vermelhas": "red",
    "verde": "green",
    "verdes": "green",
    "preto": "black",
    "pretos": "black",
    "preta": "black",
    "pretas": "black",
    "branco": "white",
    "brancos": "white",
    "branca": "white",
    "brancas": "white",
    "cinza": "gray",
    "cinzas": "gray",
    "cinzento": "gray",
    "cinzentos": "gray",
    "cinzenta": "gray",
    "cinzentas": "gray",
    "rosa": "pink",
    "rosas": "pink",
    "roxo": "purple",
    "roxos": "purple",
    "roxa": "purple",
    "roxas": "purple",
    "laranja": "orange",
    "laranjas": "orange",
    "marrom": "brown",
    "marrons": "brown",
    "castanho": "brown",
    "castanhos": "brown",
    "castanha": "brown",
    "castanhas": "brown",
    "bege": "beige",
    "beges": "beige",
    "creme": "cream",
    "cremes": "cream",
    "ouro": "gold",
    "ouros": "gold",
    "prata": "silver",
    "pratas": "silver",
    "grey": "gray",
}

TYPE_ALIASES = {
    "sneakers": [
        "sneaker", "sneakers", "athletic shoe", "sports shoe",
        "shoes", "shoe", "footwear", "calçado", "calcado",
        "sapatilha", "sapatilhas", "tenis", "ténis",
    ],
    "shoes": [
        "shoe", "shoes", "sneaker", "sneakers", "footwear",
        "calçado", "calcado", "sapatilha", "sapatilhas",
        "sapato", "sapatos", "tenis", "ténis",
    ],
    "jacket": ["jacket", "coat", "casaco", "casacos"],
    "pants": ["pants", "pant", "trouser", "trousers", "jeans", "jean", "calças", "calcas", "calça", "calca"],
    "shirt": ["shirt", "camisa"],
    "tshirt": ["t-shirt", "tshirt", "t shirt", "camiseta", "jersey"],
    "sweater": ["camisola", "sueter", "sweater", "hoodie", "jumper", "knit"],
}


class ConstraintMatchingService:
    """
    Matches parsed constraints with wardrobe items.
    """

    def __init__(self):
        pass

    def _as_list(self, value: Any) -> List[Any]:
        """Accept both compact scalar intent and legacy list-shaped constraints."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "")
        decomposed = unicodedata.normalize("NFD", text)
        without_accents = "".join(
            char for char in decomposed if unicodedata.category(char) != "Mn"
        )
        return without_accents.lower().strip()

    def _canonical_type(self, value: Any) -> str:
        normalized_value = self._normalize_text(value)
        if not normalized_value:
            return ""

        for canonical, aliases in TYPE_ALIASES.items():
            normalized_aliases = {self._normalize_text(alias) for alias in aliases}
            normalized_aliases.add(self._normalize_text(canonical))
            if normalized_value in normalized_aliases:
                return canonical

        return normalized_value

    def find_matching_items(
        self,
        constraints: Dict[str, Any],
        wardrobe: List[Dict[str, Any]],
        debug_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Find wardrobe items that match the parsed constraints.

        Args:
            constraints: Parsed user request (from UserRequestParser)
            wardrobe: List of wardrobe items (dicts with id, name, type, color, etc)

        Returns:
            Tuple of:
            - List of matching items with constraint info
            - List of unmatched constraint descriptions
        """
        matching_items = []
        unmatched = []

        # Match by exact item name
        if "name" in constraints.get("must_include", {}):
            name_matches, name_unmatched = self._match_by_name(
                self._as_list(constraints["must_include"]["name"]),
                wardrobe
            )
            matching_items.extend(name_matches)
            unmatched.extend(name_unmatched)

        # Match by type + color
        type_constraints = [
            item_type
            for item_type in self._as_list(
                constraints.get("must_include", {}).get("type")
            )
            if item_type and item_type != "item_type"
        ]
        color_constraints = self._as_list(
            constraints.get("must_include", {}).get("color")
        )

        if type_constraints or color_constraints:
            type_color_matches, type_color_unmatched = self._match_by_type_and_color(
                type_constraints,
                color_constraints,
                wardrobe,
                already_matched_ids={item["id"] for item in matching_items},
                debug_context=debug_context,
            )
            matching_items.extend(type_color_matches)
            unmatched.extend(type_color_unmatched)

        return matching_items, unmatched

    def _match_by_name(
        self,
        name_constraints: List[str],
        wardrobe: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Match items by their names."""
        matches = []
        unmatched = []

        for constraint_name in name_constraints:
            found = False
            constraint_lower = self._normalize_text(constraint_name)

            for item in wardrobe:
                item_name = self._normalize_text(item.get("name", ""))
                # Exact match or substring match
                if (item_name == constraint_lower or
                    constraint_lower in item_name or
                    item_name in constraint_lower):
                    matches.append({
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "type": item.get("type"),
                        "color": item.get("color"),
                        "constraint_match": "name",
                        "original_item": item,
                    })
                    found = True
                    break

            if not found:
                unmatched.append(f"Item named '{constraint_name}'")

        return matches, unmatched

    def _match_by_type_and_color(
        self,
        type_constraints: List[str],
        color_constraints: List[str],
        wardrobe: List[Dict[str, Any]],
        already_matched_ids: set = None,
        debug_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Match items by type and/or color."""
        matches = []
        unmatched = []
        already_matched_ids = already_matched_ids or set()

        # If both constraints exist, we need exact matches for the combination
        if type_constraints and color_constraints:
            for required_type in type_constraints:
                for required_color in color_constraints:
                    found = False
                    for item in wardrobe:
                        if item["id"] in already_matched_ids:
                            continue

                        item_type = item.get("type", "")
                        type_match = self._type_matches(item_type, required_type)
                        color_match = self._item_color_matches(item, required_color)
                        status_allowed = self._status_allowed(item)
                        temp_allowed = self._temp_allowed(item, debug_context)
                        final_match = (
                            type_match
                            and color_match
                            and status_allowed
                            and temp_allowed
                        )
                        self._debug_match_decision(
                            item,
                            type_match,
                            color_match,
                            status_allowed,
                            temp_allowed,
                            final_match,
                            debug_context,
                        )
                        if final_match:
                            matches.append({
                                "id": item.get("id"),
                                "name": item.get("name"),
                                "type": item.get("type"),
                                "color": item.get("color"),
                                "constraint_match": f"type:{required_type},color:{required_color}",
                                "original_item": item,
                            })
                            already_matched_ids.add(item["id"])
                            found = True
                            break

                    if not found:
                        unmatched.append(f"{required_color.capitalize()} {required_type}")

        # If only type constraints
        elif type_constraints:
            for required_type in type_constraints:
                found = False
                for item in wardrobe:
                    if item["id"] in already_matched_ids:
                        continue

                    item_type = item.get("type", "")
                    type_match = self._type_matches(item_type, required_type)
                    color_match = True
                    status_allowed = self._status_allowed(item)
                    temp_allowed = self._temp_allowed(item, debug_context)
                    final_match = type_match and status_allowed and temp_allowed
                    self._debug_match_decision(
                        item,
                        type_match,
                        color_match,
                        status_allowed,
                        temp_allowed,
                        final_match,
                        debug_context,
                    )
                    if final_match:
                        matches.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "type": item.get("type"),
                            "color": item.get("color"),
                            "constraint_match": f"type:{required_type}",
                            "original_item": item,
                        })
                        already_matched_ids.add(item["id"])
                        found = True
                        break

                if not found:
                    unmatched.append(f"{required_type}")

        # If only color constraints
        elif color_constraints:
            for required_color in color_constraints:
                found = False
                for item in wardrobe:
                    if item["id"] in already_matched_ids:
                        continue

                    type_match = True
                    color_match = self._item_color_matches(item, required_color)
                    status_allowed = self._status_allowed(item)
                    temp_allowed = self._temp_allowed(item, debug_context)
                    final_match = color_match and status_allowed and temp_allowed
                    self._debug_match_decision(
                        item,
                        type_match,
                        color_match,
                        status_allowed,
                        temp_allowed,
                        final_match,
                        debug_context,
                    )
                    if final_match:
                        matches.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "type": item.get("type"),
                            "color": item.get("color"),
                            "constraint_match": f"color:{required_color}",
                            "original_item": item,
                        })
                        already_matched_ids.add(item["id"])
                        found = True
                        break

                if not found:
                    unmatched.append(f"{required_color}")

        return matches, unmatched

    def _status_allowed(self, item: Dict[str, Any]) -> bool:
        return item.get("status", "clean") == "clean"

    def _temp_allowed(
        self,
        item: Dict[str, Any],
        debug_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not debug_context or debug_context.get("temperature") is None:
            return True

        temperature = debug_context.get("temperature")
        temperature_range = item.get("temperature_range") or {}
        temp_min = item.get("temp_min", item.get("tempMin", temperature_range.get("min")))
        temp_max = item.get("temp_max", item.get("tempMax", temperature_range.get("max")))
        if temp_min is None or temp_max is None:
            return True

        try:
            return float(temp_min) <= float(temperature) <= float(temp_max)
        except (TypeError, ValueError):
            return True

    def _debug_match_decision(
        self,
        item: Dict[str, Any],
        type_match: bool,
        color_match: bool,
        status_allowed: bool,
        temp_allowed: bool,
        final_match: bool,
        debug_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not debug_context or not debug_context.get("enabled"):
            return

        reasons = []
        if not type_match:
            reasons.append("type synonym did not match")
        if not color_match:
            color_source = item.get("color_source", "unknown")
            reasons.append(f"color did not match (color_source={color_source})")
        if not status_allowed:
            reasons.append(f"status is {item.get('status')}")
        if not temp_allowed:
            temperature_range = item.get("temperature_range") or {}
            temp_min = item.get("temp_min", item.get("tempMin", temperature_range.get("min")))
            temp_max = item.get("temp_max", item.get("tempMax", temperature_range.get("max")))
            reasons.append(
                f"temperature outside item range [{temp_min},{temp_max}]"
            )
        if not reasons and not final_match:
            reasons.append("unknown matcher rejection")

        print(
            "[MatchDebug] item="
            f"{item.get('name')} type_match={type_match} "
            f"color_match={color_match} status_allowed={status_allowed} "
            f"temp_allowed={temp_allowed} final_match={final_match} "
            f"reason={'matched' if final_match else '; '.join(reasons)}"
        )

    def _type_matches(self, item_type: str, required_type: str) -> bool:
        """Check if item type matches required type."""
        item_type_lower = self._normalize_text(item_type)
        required_type_lower = self._normalize_text(required_type)

        # Exact match
        if item_type_lower == required_type_lower:
            return True

        item_canonical = self._canonical_type(item_type_lower)
        required_canonical = self._canonical_type(required_type_lower)
        if item_canonical == required_canonical:
            return True
        if required_canonical == "sneakers" and item_canonical == "shoes":
            return True
        if required_canonical == "shoes" and item_canonical == "sneakers":
            return True

        # Canonical synonym groups. All entries are normalized before comparison,
        # so accented/unaccented Portuguese labels match the same group.
        type_aliases = TYPE_ALIASES
        legacy_extra_aliases = {
            "sneakers": [
                "sneaker",
                "sneakers",
                "athletic shoe",
                "sports shoe",
                "shoes",
                "shoe",
                "footwear",
                "calçado",
                "calcado",
                "sapatilha",
                "sapatilhas",
                "tenis",
                "ténis",
            ],
            "shoes": [
                "shoe",
                "shoes",
                "sneaker",
                "sneakers",
                "footwear",
                "calçado",
                "calcado",
                "sapatilha",
                "sapatilhas",
                "sapato",
                "sapatos",
                "tenis",
                "ténis",
            ],
            "jacket": ["jacket", "coat", "blazer", "windbreaker", "casaco", "casacos", "jaqueta"],
            "shirt": ["camisa"],
            "tshirt": ["t-shirt", "tshirt", "t shirt", "basic top", "camiseta", "jersey"],
            "t-shirt": ["tshirt", "t shirt", "basic top", "camiseta", "jersey"],
            "sweater": ["camisola", "sueter", "sweater", "jumper", "knit"],
            "pants": ["pants", "pant", "trouser", "trousers", "jean", "jeans", "calças", "calcas", "calça", "calca"],
        }

        for key, aliases in {**type_aliases, **legacy_extra_aliases}.items():
            normalized_aliases = {self._normalize_text(alias) for alias in aliases}
            normalized_key = self._normalize_text(key)
            if required_type_lower == normalized_key or required_type_lower in normalized_aliases:
                if item_type_lower == normalized_key or item_type_lower in normalized_aliases:
                    return True

        return False

    def _color_matches(self, item_color: str, required_color: str) -> bool:
        """Check if item color matches required color."""
        item_color_lower = self._normalize_color(item_color)
        required_color_lower = self._normalize_color(required_color)

        # Exact match
        return item_color_lower == required_color_lower

    def _item_color_matches(self, item: Dict[str, Any], required_color: str) -> bool:
        """Check color metadata first, then fallback to old item names/types."""
        item_color = (
            item.get("color")
            or item.get("inferred_color")
            or item.get("dominant_color")
        )
        if item_color:
            return self._color_matches(item_color, required_color)

        required_color_lower = self._normalize_color(required_color)
        aliases = {
            alias
            for alias, canonical in COLOR_ALIASES.items()
            if canonical == required_color_lower
        }
        aliases.add(required_color_lower)

        fallback_text = self._normalize_text(
            f"{item.get('name', '')} {item.get('type', '')} {item.get('brand', '')}"
        )
        return any(
            re.search(r"\b" + re.escape(self._normalize_text(alias)) + r"\b", fallback_text)
            for alias in aliases
        )

    def _normalize_color(self, color: str) -> str:
        color_lower = self._normalize_text(color)
        return COLOR_ALIASES.get(color_lower, color_lower)

    def find_avoid_item_ids(
        self,
        avoid_constraints: Dict[str, Any],
        wardrobe: List[Dict[str, Any]],
    ) -> List[str]:
        """Find item IDs requested by the user to avoid."""
        if not avoid_constraints:
            return []

        names = self._as_list(avoid_constraints.get("name"))
        types = self._as_list(avoid_constraints.get("type"))
        colors = self._as_list(avoid_constraints.get("color"))
        if not names and not types and not colors:
            return []

        avoided_ids = []
        for item in wardrobe:
            matched = False
            for requested_name in names:
                requested = self._normalize_text(requested_name)
                if not requested:
                    continue
                item_name = self._normalize_text(item.get("name", ""))
                if item_name == requested or requested in item_name or item_name in requested:
                    matched = True

            if types and any(self._type_matches(item.get("type", ""), item_type) for item_type in types):
                matched = True

            if colors and any(self._item_color_matches(item, color) for color in colors):
                matched = True

            item_id = item.get("id")
            if matched and item_id and item_id not in avoided_ids:
                avoided_ids.append(item_id)

        return avoided_ids

    def validate_constraints_can_be_met(
        self,
        constraints: Dict[str, Any],
        wardrobe: List[Dict[str, Any]],
        debug_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all constraints can be met with available wardrobe.

        Returns:
            Tuple of (can_be_met, list_of_missing_items)
        """
        matches, unmatched = self.find_matching_items(
            constraints,
            wardrobe,
            debug_context=debug_context,
        )

        if unmatched:
            return False, unmatched

        return True, []
