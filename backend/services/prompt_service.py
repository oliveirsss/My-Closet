"""
Prompt Service - Phase 3
"""

from typing import Any, Dict, List

from services.data_preparation_service import (
    AIReadyContext,
    AIReadyItem,
    AIReadyWeather,
)


class PromptService:
    def __init__(self):
        self.layer_names = {
            1: "Base Layer",
            2: "Insulation Layer",
            3: "Outer Layer",
        }

    # =========================================================
    # DAILY PROMPT
    # =========================================================

    def build_daily_prompt_from_context(
        self, 
        context: AIReadyContext,
        must_include_items: List[Dict[str, Any]] = None,
        user_request_text: str = None,
    ) -> str:
        """
        Build daily outfit prompt.

        Args:
            context: AI-ready context from data preparation
            must_include_items: List of items that MUST be included in the outfit
            user_request_text: Original user request text for context
        """

        weather = context.weather_current
        wardrobe_by_layer = context.wardrobe_by_layer
        constraints = context.user_constraints

        prompt_parts = []

        prompt_parts.append(self._build_system_message_daily())
        
        # Add user request if provided
        if user_request_text:
            prompt_parts.append(self._format_user_request_section(user_request_text))
        
        # Add mandatory items section if provided
        if must_include_items:
            prompt_parts.append(self._format_must_include_section(must_include_items))
        
        prompt_parts.append(self._format_weather_section(weather))
        prompt_parts.append(self._format_wardrobe_section(wardrobe_by_layer))
        prompt_parts.append(self._format_usage_frequency_section(wardrobe_by_layer))
        prompt_parts.append(self._format_constraints_section(constraints))
        prompt_parts.append(self._format_rules_section_daily(must_include_items))
        prompt_parts.append(self._format_response_format_daily())

        return "\n".join(prompt_parts)

    # =========================================================
    # SYSTEM MESSAGE
    # =========================================================

    def _build_system_message_daily(self) -> str:
        return """========================================
OUTFIT RECOMMENDATION SYSTEM
========================================

You are an expert stylist.

STRICT RULES:
- Use ONLY provided items
- DO NOT invent items
- DO NOT mention missing items
- Respect layers strictly

Layers:
1 = Base (t-shirts, tops)
2 = Insulation (hoodies, jeans, trousers)
3 = Outer (jackets, shoes, accessories)

========================================
"""

    # =========================================================
    # WEATHER
    # =========================================================

    def _format_weather_section(self, weather: AIReadyWeather) -> str:
        return f"""WEATHER:
Temp: {getattr(weather, "temperature", None)}°C
Condition: {getattr(weather, "condition", "unknown")}
Humidity: {getattr(weather, "humidity", "unknown")}
Wind: {getattr(weather, "wind_speed", "unknown")}
"""

    # =========================================================
    # WARDROBE
    # =========================================================

    def _format_wardrobe_section(
        self, wardrobe_by_layer: Dict[int, List[AIReadyItem]]
    ) -> str:

        section = "WARDROBE ID CATALOG:\nHigher Score means a better candidate for this request. Select by ID only.\n"

        for layer, items in wardrobe_by_layer.items():
            section += f"\nLayer {layer}:\n"

            for item in items:
                score = getattr(item, "score", 0)
                if score is None:
                    score = 0
                section += f"""
ID: {item.id}
Name: {item.name}
Type: {item.type}
Section: {self._section_for_item(item)}
Normalized type: {self._normalized_type(item)}
Color: {getattr(item, "color", "") or "unknown"}
Style: {getattr(item, "style", "") or "unknown"}
Occasion: {getattr(item, "occasion", "") or "unknown"}
Layer: {layer}
Status: {item.status}
Score: {score:.0f}
Temp: {item.temp_min}-{item.temp_max}
"""

        return section

    def _normalized_text(self, value: Any) -> str:
        import unicodedata

        decomposed = unicodedata.normalize("NFD", str(value or ""))
        without_accents = "".join(
            char for char in decomposed if unicodedata.category(char) != "Mn"
        )
        return without_accents.lower().strip()

    def _normalized_type(self, item: AIReadyItem) -> str:
        text = self._normalized_text(f"{item.type} {item.name}")
        if any(token in text for token in ["calcado", "sapatilha", "tenis", "sneaker", "shoe", "boot", "sapato"]):
            return "shoes"
        if any(token in text for token in ["calca", "pants", "trouser", "jeans", "short"]):
            return "pants"
        if any(token in text for token in ["casaco", "jacket", "coat", "blazer"]):
            return "outer_layer"
        if any(token in text for token in ["camisola", "sweater", "hoodie", "cardigan"]):
            return "insulation"
        if any(token in text for token in ["acessor", "scarf", "belt", "tie", "hat", "cap"]):
            return "accessories"
        return "base_layer"

    def _section_for_item(self, item: AIReadyItem) -> str:
        normalized_type = self._normalized_type(item)
        if normalized_type in {"shoes", "pants", "accessories"}:
            return normalized_type
        if normalized_type == "outer_layer":
            return "outer_layer"
        if normalized_type == "insulation":
            return "base_layer"
        return "base_layer"

    # =========================================================
    # USAGE
    # =========================================================

    def _format_usage_frequency_section(
        self, wardrobe_by_layer: Dict[int, List[AIReadyItem]]
    ) -> str:

        section = "USAGE:\n"

        for items in wardrobe_by_layer.values():
            for item in items:
                usage = 0
                if item.usage_metrics:
                    usage = item.usage_metrics.get(
                        "usage_frequency_last_7_days", 0
                    )
                section += f"{item.name}: {usage} times\n"

        return section

    # =========================================================
    # CONSTRAINTS
    # =========================================================

    def _format_user_request_section(self, user_request_text: str) -> str:
        """Format the user's original request."""
        return f"""========================================
MANDATORY USER REQUEST
========================================

User said: "{user_request_text}"

This is what the user wants - you MUST incorporate this into the outfit.

========================================
"""

    def _format_must_include_section(self, must_include_items: List[Dict[str, Any]]) -> str:
        """
        Format the MUST_INCLUDE items that were matched from the wardrobe.
        
        These items MUST appear in the final outfit recommendation.
        """
        if not must_include_items:
            return ""

        section = """========================================
STRICT REQUIREMENT - MUST INCLUDE ITEMS
========================================

The user specifically requested these items. They MUST be in the outfit:

MUST INCLUDE:
"""
        mandatory_assignments = []
        for item in must_include_items:
            item_name = item.get("name", "Unknown")
            item_id = item.get("id", "?")
            constraint_match = item.get("constraint_match", "")
            item_type = item.get("type", "")
            json_field = self._json_field_for_text(f"{item_type} {item_name}")
            mandatory_assignments.append(f"{json_field} = {item_id}")
            section += f"\n- ID: {item_id}\n"
            section += f"  Name: {item_name}\n"
            if item_type:
                section += f"  Type: {item_type}\n"
            section += f"  Required JSON field: {json_field}\n"
            if item.get("score") is not None:
                section += f"  Score: {item.get('score'):.0f}\n"
            section += f"  Match reason: {constraint_match}\n"

        section += "\nMandatory item JSON assignments:\n"
        for assignment in mandatory_assignments:
            section += f"{assignment}\n"

        section += """
CRITICAL: Do NOT exclude these items. Include ALL of them in your outfit recommendation using their IDs in the required JSON fields exactly as assigned above.
========================================
"""
        return section

    def _json_field_for_text(self, value: str) -> str:
        text = self._normalized_text(value)
        if any(token in text for token in ["calcado", "sapatilha", "tenis", "sneaker", "shoe", "boot", "sapato"]):
            return "shoes"
        if any(token in text for token in ["calca", "pants", "trouser", "jeans"]):
            return "pants"
        if any(token in text for token in ["casaco", "jacket", "coat", "blazer"]):
            return "outer_layer"
        if any(token in text for token in ["acessor", "scarf", "belt", "tie", "hat", "cap"]):
            return "accessories"
        return "base_layer"

    def _format_constraints_section(self, constraints: Dict[str, Any]) -> str:

        if not constraints:
            return "No additional constraints\n"

        return f"Additional Constraints: {constraints}\n"

    # =========================================================
    # RULES
    # =========================================================

    def _format_rules_section_daily(self, must_include_items: List[Dict[str, Any]] = None) -> str:
        """Format rules section. Emphasize must_include items if provided."""
        rules = """RULES:
- Only clean items
- Respect layers
- No duplicates
- Weather appropriate
- Prefer higher-score candidates unless a mandatory item is listed
"""
        if must_include_items:
            rules += f"""- MANDATORY: Include ALL {len(must_include_items)} user-requested item(s)
- NEVER exclude user-requested items
- Adapt the rest of the outfit around the mandatory items
"""
        return rules

    # =========================================================
    # RESPONSE FORMAT
    # =========================================================

    def _format_response_format_daily(self) -> str:
        return """RESPONSE FORMAT - JSON ONLY:

Return exactly one JSON object. No markdown. No extra text.

{
  "base_layer": "item_id_or_null",
  "pants": "item_id_or_null",
  "outer_layer": "item_id_or_null",
  "shoes": "item_id_or_null",
  "accessories": ["item_id"],
  "reasoning": "short explanation"
}

STRICT JSON RULES:
- Use only IDs from the provided wardrobe catalog.
- Do not return item names as selected values.
- If a slot is not used, return null for that slot.
- accessories must always be an array.
- If user requested a must_include item, its ID must appear in the correct field exactly as listed in "Mandatory item JSON assignments".
- Do not put another item in a field that has a mandatory assignment.
- If user requested yellow sneakers, "shoes" must be the ID of Mexico 66 yellow.
- If user requested a green jacket, "outer_layer" must be the ID of casaco com botoes.
- Selected values must be IDs only, never item names.

FEW-SHOT EXAMPLES:

User: "quero um outfit com sapatilhas amarelas"
Matching item:
ID: 0a35fb81-e32d-413e-89d7-6b0ad05628aa
Name: Mexico 66 yellow
Correct JSON:
{
  "base_layer": null,
  "pants": null,
  "outer_layer": null,
  "shoes": "0a35fb81-e32d-413e-89d7-6b0ad05628aa",
  "accessories": [],
  "reasoning": "Includes the requested yellow sneakers."
}

User: "quero um look com um casaco verde"
Matching item:
ID: 26d3f03d-a15b-4354-8166-ea006182b546
Name: casaco com botoes
Correct JSON:
{
  "base_layer": null,
  "pants": null,
  "outer_layer": "26d3f03d-a15b-4354-8166-ea006182b546",
  "shoes": null,
  "accessories": [],
  "reasoning": "Includes the requested green jacket."
}
"""

# =========================================================
# EXCEPTION
# =========================================================

class PromptServiceError(Exception):
    pass
