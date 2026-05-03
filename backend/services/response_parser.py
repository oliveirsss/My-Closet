"""
Response Parser Service

Handles parsing and normalizing VLM outputs with robust validation:
- Extracts outfit items from structured format (Base Layer, Insulation Layer, etc.)
- Validates items exist in wardrobe inventory
- Validates layer placement and corrects errors
- Filters dirty items
- Removes VLM artifacts (PECAS_EM_FALTA sections, missing items mentions)
- Converts VLM output to frontend-friendly format
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Layer mapping constants
LAYER_1_TYPES = [
    "t-shirt",
    "tshirt",
    "shirt",
    "top",
    "camiseta",
    "camisola fina",
    "base",
    "tank",
    "vest",
    "long sleeve base",
    "thermal base",
]
LAYER_2_TYPES = [
    "sweater",
    "hoodie",
    "cardigan",
    "pullover",
    "trousers",
    "pants",
    "jeans",
    "calças",
    "camisola",
    "turtleneck",
    "jumper",
    "fleece",
    "sweatshirt",
]
LAYER_3_TYPES = [
    "jacket",
    "coat",
    "parka",
    "blazer",
    "casaco",
    "puffer",
    "windbreaker",
    "rain jacket",
    "denim jacket",
]
SHOES_TYPES = [
    "shoes",
    "sneakers",
    "boots",
    "sapatilhas",
    "calçado",
    "trainers",
    "pumps",
    "sandals",
    "loafers",
    "athletic shoes",
    "dress shoes",
]
ACCESSORY_TYPES = [
    "hat",
    "cap",
    "beanie",
    "boné",
    "bone",
    "chapéu",
    "chapeu",
    "gorro",
    "scarf",
    "gloves",
    "socks",
    "belt",
    "bag",
    "watch",
    "sunglasses",
    "acessórios",
    "glasses",
    "mittens",
    "tie",
]

LAYER_MAPPING = {
    1: LAYER_1_TYPES,
    2: LAYER_2_TYPES,
    3: LAYER_3_TYPES,
    "shoes": SHOES_TYPES,
    "accessories": ACCESSORY_TYPES,
}


class ResponseParser:
    """Service for parsing and normalizing VLM responses with robust validation."""

    def __init__(self):
        """Initialize response parser."""
        self.warnings: List[str] = []

    def parse_daily_outfit(
        self,
        vlm_response: Dict[str, Any],
        wardrobe: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Parse a daily outfit recommendation from VLM response.

        Args:
            vlm_response: Raw VLM response containing structured outfit
            wardrobe: List of available wardrobe items
            weather_context: Current weather data

        Returns:
            Parsed dict with items, reasoning, warnings, and layer assignments

        Raises:
            ResponseParserError: If parsing fails critically
        """
        self.warnings = []

        try:
            response_text = vlm_response.get("response", "") or ""
            wardrobe_by_id = {
                str(item.get("id")): item for item in wardrobe if item.get("id") is not None
            }

            json_result = self._parse_json_daily_response(response_text, wardrobe_by_id)
            if json_result:
                print(f"[ResponseParser] raw_llava_response={response_text}")
                print(f"[ResponseParser] parsed_json_ids={json_result['item_ids']}")
                return json_result

            # Extract items from legacy structured text format
            items_data = self._extract_items_from_sections(response_text, wardrobe)

            if not items_data:
                return {
                    "success": False,
                    "items": [],
                    "item_ids": [],
                    "reasoning": self._clean_reasoning(
                        vlm_response.get("reasoning") or response_text
                    ),
                    "warnings": ["No valid items found in VLM response"],
                    "layer_assignments": {},
                    "raw_response": response_text,
                    "validation_errors": ["No parseable structured items found"],
                }

            # Validate and clean items
            validated_items = []
            layer_assignments = {1: [], 2: [], 3: [], "shoes": [], "accessories": []}
            used_ids = set()
            validation_errors = []

            for layer_num, item_name, item_id in items_data:
                # Check if item exists in wardrobe
                if not self._validate_item_exists(item_id, wardrobe_by_id):
                    message = (
                        f"Item '{item_name}' (ID: {item_id}) not found in wardrobe - discarded"
                    )
                    validation_errors.append(message)
                    self.warnings.append(message)
                    continue

                item = wardrobe_by_id[item_id]

                # Check if item is clean
                if not self._is_clean_item(item):
                    message = (
                        f"Item '{item_name}' is {item.get('status', 'unknown')} - discarded"
                    )
                    validation_errors.append(message)
                    self.warnings.append(message)
                    continue

                if item_id in used_ids:
                    self.warnings.append(
                        f"Duplicate item '{item_name}' (ID: {item_id}) removed"
                    )
                    continue

                # Validate layer assignment
                is_valid, corrected_layer = self._validate_layer_assignment(
                    item, layer_num
                )

                if not is_valid:
                    message = (
                        f"Item '{item_name}' (type: {item.get('type', 'unknown')}) "
                        f"could not be placed in a valid layer - discarded"
                    )
                    validation_errors.append(message)
                    self.warnings.append(message)
                    continue

                if corrected_layer != layer_num:
                    self.warnings.append(
                        f"Item '{item_name}' was in layer {layer_num}, "
                        f"corrected to layer {corrected_layer}"
                    )
                    layer_num = corrected_layer

                # Add to validated items
                validated_items.append(item)
                layer_assignments[corrected_layer].append(item_id)
                used_ids.add(item_id)

            # Clean reasoning
            reasoning_source = self._extract_reasoning_text(response_text) or vlm_response.get(
                "reasoning", ""
            )
            clean_reasoning = self._clean_reasoning(reasoning_source)

            return {
                "success": len(validated_items) > 0,
                "items": validated_items,
                "item_ids": [item["id"] for item in validated_items],
                "reasoning": clean_reasoning,
                "warnings": self.warnings,
                "layer_assignments": layer_assignments,
                "generated_at": datetime.now().isoformat(),
                "raw_response": response_text,
                "validation_errors": validation_errors,
            }

        except Exception as e:
            raise ResponseParserError(f"Failed to parse daily outfit: {str(e)}")

    def _parse_json_daily_response(
        self,
        response_text: str,
        wardrobe_by_id: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        raw_json = self._extract_json_object(response_text)
        if not raw_json:
            return None

        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            self.warnings.append(f"JSON parse failed, falling back to text parsing: {exc}")
            return None

        slots = [
            ("base_layer", 1),
            ("pants", 2),
            ("outer_layer", 3),
            ("shoes", "shoes"),
        ]
        item_ids: List[str] = []
        layer_assignments = {1: [], 2: [], 3: [], "shoes": [], "accessories": []}
        validation_errors = []

        for key, layer_key in slots:
            value = parsed.get(key)
            if value in (None, "", "null", "None"):
                continue
            item_id = str(value)
            item_ids.append(item_id)
            layer_assignments[layer_key].append(item_id)

        accessories = parsed.get("accessories") or []
        if isinstance(accessories, str):
            accessories = [accessories]
        if not isinstance(accessories, list):
            accessories = []
        for item_id in accessories:
            if item_id in (None, "", "null", "None"):
                continue
            item_id = str(item_id)
            item_ids.append(item_id)
            layer_assignments["accessories"].append(item_id)

        validated_items = []
        used_ids = set()
        for item_id in item_ids:
            if item_id not in wardrobe_by_id:
                validation_errors.append(f"Selected ID {item_id} not found in wardrobe")
                continue
            if item_id in used_ids:
                self.warnings.append(f"Duplicate selected ID {item_id} removed")
                continue
            item = wardrobe_by_id[item_id]
            if not self._is_clean_item(item):
                validation_errors.append(
                    f"Selected ID {item_id} is {item.get('status', 'unknown')}"
                )
                continue
            validated_items.append(item)
            used_ids.add(item_id)

        reasoning = self._clean_reasoning(str(parsed.get("reasoning") or ""))
        return {
            "success": len(validated_items) > 0,
            "items": validated_items,
            "item_ids": [item["id"] for item in validated_items],
            "reasoning": reasoning,
            "warnings": self.warnings,
            "layer_assignments": layer_assignments,
            "generated_at": datetime.now().isoformat(),
            "raw_response": response_text,
            "raw_json": raw_json,
            "validation_errors": validation_errors,
        }

    def _extract_json_object(self, text: str) -> Optional[str]:
        if not text:
            return None
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
            stripped = re.sub(r"\s*```$", "", stripped)
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return stripped[start : end + 1]

    def parse_travel_outfits(
        self,
        vlm_response: Dict[str, Any],
        wardrobe: List[Dict[str, Any]],
        weather_forecast: List[Dict[str, Any]],
        num_days: int,
    ) -> Dict[str, Any]:
        """
        Parse travel outfit recommendations from VLM response.

        Args:
            vlm_response: Raw VLM response containing structured travel plan
            wardrobe: List of available wardrobe items
            weather_forecast: Weather forecast for each day
            num_days: Number of days in travel

        Returns:
            Parsed dict with daily outfits, packing list, and warnings

        Raises:
            ResponseParserError: If parsing fails critically
        """
        self.warnings = []

        try:
            response_text = vlm_response.get("response", "")
            wardrobe_by_id = {item["id"]: item for item in wardrobe}

            daily_outfits = []
            all_packed_items = set()

            # Parse each day
            for day_num in range(1, num_days + 1):
                day_section = self._extract_day_section(response_text, day_num)
                if not day_section:
                    self.warnings.append(f"Could not extract Day {day_num} section")
                    continue

                items_data = self._extract_items_from_sections(day_section, wardrobe)
                day_items = []
                day_item_ids = []

                for layer_num, item_name, item_id in items_data:
                    if not self._validate_item_exists(item_id, wardrobe_by_id):
                        self.warnings.append(
                            f"Day {day_num}: Item '{item_name}' not found - discarded"
                        )
                        continue

                    item = wardrobe_by_id[item_id]

                    if not self._is_clean_item(item):
                        self.warnings.append(
                            f"Day {day_num}: Item '{item_name}' is {item.get('status')} - discarded"
                        )
                        continue

                    is_valid, corrected_layer = self._validate_layer_assignment(
                        item, layer_num
                    )
                    if not is_valid:
                        self.warnings.append(
                            f"Day {day_num}: Item '{item_name}' could not be placed - discarded"
                        )
                        continue

                    day_items.append(item)
                    day_item_ids.append(item_id)
                    all_packed_items.add(item_id)

                daily_outfits.append(
                    {
                        "day": day_num,
                        "items": day_items,
                        "item_ids": day_item_ids,
                        "weather": weather_forecast[day_num - 1]
                        if day_num - 1 < len(weather_forecast)
                        else {},
                    }
                )

            # Extract packing list
            packing_list = [
                wardrobe_by_id[iid] for iid in all_packed_items if iid in wardrobe_by_id
            ]

            # Check for duplicates in packing list
            if len(all_packed_items) < len(packing_list):
                self.warnings.append("Duplicate items removed from packing list")

            # Extract mixing & matching strategy
            mixing_strategy = self._extract_section(response_text, "Mixing & Matching")
            packing_summary = self._extract_section(
                response_text, "Packing List Summary"
            )
            clean_reasoning = self._clean_reasoning(vlm_response.get("reasoning", ""))

            return {
                "success": len(daily_outfits) > 0 and len(packing_list) > 0,
                "daily_outfits": daily_outfits,
                "packing_list": packing_list,
                "packing_summary": packing_summary,
                "mixing_strategy": mixing_strategy,
                "reasoning": clean_reasoning,
                "warnings": self.warnings,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            raise ResponseParserError(f"Failed to parse travel outfits: {str(e)}")

    def parse_alternative_outfits(
        self,
        vlm_responses: List[Dict[str, Any]],
        wardrobe: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Parse alternative outfit recommendations from VLM responses.

        Args:
            vlm_responses: List of VLM response dicts, one per alternative
            wardrobe: List of available wardrobe items
            weather_context: Current weather data

        Returns:
            Parsed dict with alternative outfits and warnings

        Raises:
            ResponseParserError: If parsing fails critically
        """
        self.warnings = []

        try:
            wardrobe_by_id = {item["id"]: item for item in wardrobe}
            alternatives = []

            for alt_num, vlm_response in enumerate(vlm_responses, 1):
                items_data = self._extract_items_from_sections(
                    vlm_response.get("response", ""), wardrobe
                )

                alt_items = []
                layer_assignments = {
                    1: [],
                    2: [],
                    3: [],
                    "shoes": [],
                    "accessories": [],
                }

                for layer_num, item_name, item_id in items_data:
                    if not self._validate_item_exists(item_id, wardrobe_by_id):
                        self.warnings.append(
                            f"Alt {alt_num}: Item '{item_name}' not found - discarded"
                        )
                        continue

                    item = wardrobe_by_id[item_id]

                    if not self._is_clean_item(item):
                        self.warnings.append(
                            f"Alt {alt_num}: Item '{item_name}' is {item.get('status')} - discarded"
                        )
                        continue

                    is_valid, corrected_layer = self._validate_layer_assignment(
                        item, layer_num
                    )
                    if not is_valid:
                        self.warnings.append(
                            f"Alt {alt_num}: Item '{item_name}' could not be placed - discarded"
                        )
                        continue

                    alt_items.append(item)
                    layer_assignments[corrected_layer].append(item_id)

                if alt_items:
                    clean_reasoning = self._clean_reasoning(
                        vlm_response.get("reasoning", "")
                    )
                    alternatives.append(
                        {
                            "alternative_number": alt_num,
                            "items": alt_items,
                            "item_ids": [item["id"] for item in alt_items],
                            "reasoning": clean_reasoning,
                            "layer_assignments": layer_assignments,
                        }
                    )

            return {
                "success": len(alternatives) > 0,
                "alternatives": alternatives,
                "warnings": self.warnings,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            raise ResponseParserError(f"Failed to parse alternative outfits: {str(e)}")

    def _extract_items_from_sections(
        self, text: str, wardrobe: List[Dict[str, Any]]
    ) -> List[Tuple[int, str, str]]:
        """
        Extract items from structured format sections.

        Parses "Base Layer:", "Insulation Layer:", "Outer Layer:", "Shoes:", "Accessories:" sections.

        Args:
            text: Text containing structured sections
            wardrobe: List of wardrobe items for reference

        Returns:
            List of (layer_num, item_name, item_id) tuples
        """
        items_data = []

        # Define section patterns and their layer numbers
        cleaned_text = self._remove_forbidden_sections(text)
        sections = [
            ("Base Layer", 1),
            ("Insulation Layer", 2),
            ("Outer Layer", 3),
            ("Shoes", "shoes"),
            ("Accessories", "accessories"),
        ]

        for idx, (section_name, layer_key) in enumerate(sections):
            pattern = rf"{re.escape(section_name)}(?:\s*\([^)]*\))?\s*:"
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if not match:
                continue

            start_pos = match.end()
            end_pos = len(cleaned_text)
            for next_section_name, _ in sections[idx + 1 :]:
                next_match = re.search(
                    rf"\n\s*{re.escape(next_section_name)}(?:\s*\([^)]*\))?\s*:",
                    cleaned_text[start_pos:],
                    re.IGNORECASE,
                )
                if next_match:
                    end_pos = start_pos + next_match.start()
                    break

            reasoning_match = re.search(
                r"\n\s*Reasoning\s*:",
                cleaned_text[start_pos:],
                re.IGNORECASE,
            )
            if reasoning_match:
                end_pos = min(end_pos, start_pos + reasoning_match.start())

            section_content = cleaned_text[start_pos:end_pos].strip()
            extracted = self._parse_layer_items(section_content, layer_key, wardrobe)
            items_data.extend(extracted)

        return items_data

    def _parse_layer_items(
        self,
        section_text: str,
        layer_key: Any,
        wardrobe: List[Dict[str, Any]],
    ) -> List[Tuple[int, str, str]]:
        """
        Parse items from a single layer section.

        Args:
            section_text: Text of a single layer section
            layer_key: Layer identifier (1, 2, 3, "shoes", "accessories")

        Returns:
            List of (layer_key, item_name, item_id) tuples
        """
        items = []
        section_text = section_text.strip()

        if not section_text or section_text.lower() in ["none", "n/a", ""]:
            return items

        item_entries = [
            item.strip()
            for item in re.split(r",|\n| and ", section_text, flags=re.IGNORECASE)
        ]

        for entry in item_entries:
            if not entry or entry.lower() in ["none", "n/a", ""]:
                continue

            if self._is_forbidden_entry(entry):
                continue

            item_name = re.sub(r"\[ID:\s*[^\]]+\]|\(([^)]+)\)$", "", entry).strip()
            item_id = self._extract_item_id(entry)

            if item_id:
                if any(str(w_item.get("id")) == str(item_id) for w_item in wardrobe):
                    items.append((layer_key, item_name, item_id))
                    continue
                self.warnings.append(
                    f"Item '{item_name}' (ID: {item_id}) not found in wardrobe - trying name match"
                )

            matched_item_id = self._match_item_name_to_wardrobe(item_name, wardrobe)
            if matched_item_id:
                items.append((layer_key, item_name, matched_item_id))

        return items

    def _match_item_name_to_wardrobe(
        self, item_name: str, wardrobe: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Fallback matcher for VLM outputs that contain names but no IDs.

        Matching strategy:
        1. Exact case-insensitive match
        2. Partial contains match
        3. Best score wins; ambiguous results are discarded
        """
        if not item_name:
            return None

        normalized_target = self._normalize_item_name(item_name)
        if not normalized_target or normalized_target in {"none", "n a"}:
            return None

        # Exact match first
        exact_matches = []
        for item in wardrobe:
            wardrobe_name = self._normalize_item_name(item.get("name", ""))
            if wardrobe_name == normalized_target:
                exact_matches.append(item)

        if len(exact_matches) == 1:
            return exact_matches[0].get("id")
        if len(exact_matches) > 1:
            return None

        # Partial match fallback with simple scoring
        scored_matches = []
        target_tokens = set(normalized_target.split())
        for item in wardrobe:
            wardrobe_name_raw = item.get("name", "")
            wardrobe_name = self._normalize_item_name(wardrobe_name_raw)
            if not wardrobe_name:
                continue

            if normalized_target in wardrobe_name or wardrobe_name in normalized_target:
                wardrobe_tokens = set(wardrobe_name.split())
                overlap = len(target_tokens & wardrobe_tokens)
                score = overlap * 10 - abs(len(wardrobe_name) - len(normalized_target))
                scored_matches.append((score, item))

        if not scored_matches:
            return None

        scored_matches.sort(key=lambda x: x[0], reverse=True)
        best_score, best_item = scored_matches[0]

        # If there is another candidate with the same score, treat as ambiguous
        if len(scored_matches) > 1 and scored_matches[1][0] == best_score:
            return None

        return best_item.get("id")

    def _normalize_item_name(self, name: str) -> str:
        normalized = (name or "").lower().strip()
        normalized = re.sub(r"\[id:\s*[^\]]+\]", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"[^a-z0-9\s]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _extract_item_id(self, text: str) -> Optional[str]:
        """
        Extract item ID from text.

        Looks for patterns like "UUID-style" or "ID-xxxx" or hex strings.

        Args:
            text: Text potentially containing an ID

        Returns:
            Extracted ID or None
        """
        bracket_id = re.search(r"\[ID:\s*([^\]]+)\]", text, re.IGNORECASE)
        if bracket_id:
            return bracket_id.group(1).strip()

        # Try to find UUID pattern (most common)
        uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
        match = re.search(uuid_pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

        # Try to find ID pattern like "id: xxx" or "(xxx)"
        id_pattern = r"\(([^)]+)\)$"
        match = re.search(id_pattern, text)
        if match:
            return match.group(1)

        # Try alphanumeric ID pattern
        id_pattern = r"[a-zA-Z0-9_-]{8,}"
        match = re.search(id_pattern, text)
        if match:
            return match.group(0)

        return None

    def _remove_forbidden_sections(self, text: str) -> str:
        cleaned = re.sub(
            r"PECAS_EM_FALTA.*?(?=\n[A-Z][A-Za-z ]+:\s*|\Z)",
            "",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        cleaned = re.sub(
            r"(Missing items|Items needed|Peças em falta).*?(?=\n[A-Z][A-Za-z ]+:\s*|\Z)",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return cleaned

    def _is_forbidden_entry(self, entry: str) -> bool:
        lowered = entry.lower().strip()
        forbidden_markers = [
            "pecas_em_falta",
            "peças em falta",
            "missing items",
            "items needed",
            "unavailable",
        ]
        return any(marker in lowered for marker in forbidden_markers)

    def _validate_item_exists(
        self, item_id: str, wardrobe_by_id: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Check if item ID exists in wardrobe.

        Args:
            item_id: Item ID to validate
            wardrobe_by_id: Dictionary of wardrobe items by ID

        Returns:
            True if item exists, False otherwise
        """
        return item_id in wardrobe_by_id

    def _validate_layer_assignment(
        self, item: Dict[str, Any], assigned_layer: Any
    ) -> Tuple[bool, Any]:
        """
        Check if item is assigned to correct layer.

        If item is in wrong layer, attempts to correct it.

        Args:
            item: Item dictionary with type and layer info
            assigned_layer: Layer item was assigned to (1, 2, 3, "shoes", "accessories")

        Returns:
            Tuple of (is_valid, corrected_layer)
        """
        item_type = (item.get("type", "") or "").lower()
        db_layer = item.get("layer", 1)

        normalized_type = item_type.replace("-", " ").strip()

        # Check if it's shoes or accessories (special cases)
        if assigned_layer == "shoes":
            for shoe_type in SHOES_TYPES:
                if shoe_type in normalized_type:
                    return (True, "shoes")
            for shoe_type in SHOES_TYPES:
                if shoe_type in normalized_type:
                    return (True, "shoes")
            return (False, assigned_layer)

        if assigned_layer == "accessories":
            for acc_type in ACCESSORY_TYPES:
                if acc_type in normalized_type:
                    return (True, "accessories")
            for acc_type in ACCESSORY_TYPES:
                if acc_type in normalized_type:
                    return (True, "accessories")
            return (False, assigned_layer)

        # For numeric layers (1, 2, 3), check type against layer mapping
        if assigned_layer in LAYER_MAPPING:
            layer_types = LAYER_MAPPING[assigned_layer]
            for layer_type in layer_types:
                if layer_type in normalized_type:
                    return (True, assigned_layer)

            # Try to correct to right layer based on database layer
            if db_layer in LAYER_MAPPING:
                layer_types = LAYER_MAPPING[db_layer]
                for layer_type in layer_types:
                    if layer_type in normalized_type:
                        return (True, db_layer)

            # If it's clearly a heavy item, assign to layer 3
            for layer_3_type in LAYER_3_TYPES:
                if layer_3_type in normalized_type:
                    return (True, 3)

            # If it's clearly a base layer item, assign to layer 1
            for layer_1_type in LAYER_1_TYPES:
                if layer_1_type in normalized_type:
                    return (True, 1)

            # If it's clearly a mid layer item, assign to layer 2
            for layer_2_type in LAYER_2_TYPES:
                if layer_2_type in normalized_type:
                    return (True, 2)

            return (False, assigned_layer)

        return (False, assigned_layer)

    def _clean_reasoning(self, reasoning: str) -> str:
        """
        Clean reasoning by removing VLM artifacts.

        Removes:
        - "PECAS_EM_FALTA" sections
        - "Missing items" text
        - "Items needed" text
        - "Unavailable" text
        - "Peças em falta" text
        - Extra whitespace

        Args:
            reasoning: Raw reasoning text from VLM

        Returns:
            Cleaned reasoning
        """
        if not reasoning:
            return ""

        reasoning = self._extract_reasoning_text(reasoning) or reasoning

        # Remove PECAS_EM_FALTA sections
        reasoning = re.sub(
            r"PECAS_EM_FALTA.*?(?=\n\n|\Z)",
            "",
            reasoning,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove "Missing items" sections
        reasoning = re.sub(
            r"Missing items?:?.*?(?=\n\n|\Z)",
            "",
            reasoning,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove "Items needed" sections
        reasoning = re.sub(
            r"Items needed:?.*?(?=\n\n|\Z)",
            "",
            reasoning,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove "Unavailable" sections
        reasoning = re.sub(
            r"Unavailable.*?(?=\n\n|\Z)",
            "",
            reasoning,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove "Peças em falta" sections
        reasoning = re.sub(
            r"Peças em falta.*?(?=\n\n|\Z)",
            "",
            reasoning,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove copied section labels and everything attached to them
        reasoning = re.sub(
            r"(Base Layer|Insulation Layer|Outer Layer|Shoes|Accessories)\s*:.*?(?=(Base Layer|Insulation Layer|Outer Layer|Shoes|Accessories|Reasoning)\s*:|\Z)",
            "",
            reasoning,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove repeated raw "None" artifacts and raw list fragments
        reasoning = re.sub(r"\bNone\b", "", reasoning, flags=re.IGNORECASE)
        reasoning = re.sub(r"\[ID:\s*[^\]]+\]", "", reasoning, flags=re.IGNORECASE)
        reasoning = re.sub(r"\([^)]*\bID\b[^)]*\)", "", reasoning, flags=re.IGNORECASE)
        reasoning = re.sub(r"\bITEM[_ -]?\d+\b", "", reasoning, flags=re.IGNORECASE)

        # Remove lines that still look like item listings
        reasoning = re.sub(
            r"^[A-Z][A-Za-z0-9'’\-\s]+(?:\[ID:[^\]]+\]|\([^)]+\))?\s*$",
            "",
            reasoning,
            flags=re.MULTILINE,
        )

        # Clean up multiple newlines
        reasoning = re.sub(r"\n\n+", "\n\n", reasoning)

        # Strip leading/trailing whitespace
        reasoning = reasoning.strip()

        # Remove section labels accidentally echoed by model
        reasoning = re.sub(
            r"^(Base Layer|Insulation Layer|Outer Layer|Shoes|Accessories)\s*:.*$",
            "",
            reasoning,
            flags=re.IGNORECASE | re.MULTILINE,
        ).strip()

        # Remove explicit wrong-layer phrases that are not safe to expose
        reasoning = re.sub(
            r"\b(is|as|for)\s+(the\s+)?(base layer|insulation layer|outer layer|shoes|accessories)\b",
            "",
            reasoning,
            flags=re.IGNORECASE,
        )
        reasoning = re.sub(
            r"\b(base layer|insulation layer|outer layer|shoes|accessories)\b",
            "",
            reasoning,
            flags=re.IGNORECASE,
        )

        # Collapse whitespace
        reasoning = re.sub(r"\s+", " ", reasoning).strip()

        return reasoning

    def _extract_reasoning_text(self, text: str) -> str:
        if not text:
            return ""

        match = re.search(r"Reasoning\s*:(.*)", text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _is_clean_item(self, item: Dict[str, Any]) -> bool:
        """
        Check if item is not dirty.

        Args:
            item: Item dictionary

        Returns:
            True if item is clean, False if dirty or unknown status
        """
        status = (item.get("status") or "").lower()
        return status != "dirty"

    def _extract_day_section(self, text: str, day_num: int) -> Optional[str]:
        """
        Extract section for a specific day from travel response.

        Args:
            text: Full response text
            day_num: Day number to extract

        Returns:
            Text for that day, or None if not found
        """
        # Look for "Day X:" pattern
        pattern = rf"Day\s+{day_num}\s*:"
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            return None

        # Find content from this match to next "Day" or end
        start_pos = match.end()
        next_day_match = re.search(r"\nDay\s+\d+\s*:", text[start_pos:], re.IGNORECASE)

        if next_day_match:
            end_pos = start_pos + next_day_match.start()
        else:
            # Look for next major section
            next_section = re.search(
                r"\n(Packing List|Mixing|Reasoning)", text[start_pos:], re.IGNORECASE
            )
            if next_section:
                end_pos = start_pos + next_section.start()
            else:
                end_pos = len(text)

        return text[start_pos:end_pos].strip()

    def _extract_section(self, text: str, section_name: str) -> str:
        """
        Extract a named section from text.

        Args:
            text: Full text
            section_name: Section name to find (e.g., "Reasoning", "Packing List")

        Returns:
            Section content, or empty string if not found
        """
        pattern = rf"{section_name}.*?:"
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            return ""

        start_pos = match.end()

        # Find next section or end
        next_section = re.search(r"\n[A-Z][A-Za-z\s]+:", text[start_pos:])
        if next_section:
            end_pos = start_pos + next_section.start()
        else:
            end_pos = len(text)

        return text[start_pos:end_pos].strip()

    def parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from VLM text response.

        Attempts to extract and parse JSON from text that may contain
        extra text before or after the JSON.

        Args:
            response_text: Raw text response from VLM

        Returns:
            Parsed JSON dictionary

        Raises:
            ResponseParserError: If JSON cannot be extracted/parsed
        """
        try:
            # Try direct JSON parse first
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the text
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                json_str = response_text[start_idx : end_idx + 1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try to find JSON array
        start_idx = response_text.find("[")
        end_idx = response_text.rfind("]")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                json_str = response_text[start_idx : end_idx + 1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        raise ResponseParserError(
            f"Could not extract valid JSON from response: {response_text[:100]}"
        )


class ResponseParserError(Exception):
    """Exception raised by ResponseParser."""

    pass
