"""
Prompt Service - Phase 3

Builds high-quality structured prompts for Visual Language Models (VLMs).
Specifically designed for LLaVA and similar multimodal models.

This service converts the AI-ready context (from Phase 2) into explicit,
deterministic prompts that reduce hallucination and guide the VLM toward
high-quality, parseable outfit recommendations.

Key Design Principles:
- Explicit: Every instruction is clear and unambiguous
- Deterministic: Response structure is fixed and predictable
- Non-generative: VLM only selects from provided items
- Reason-aware: VLM must explain its reasoning
- Layer-aware: Respects clothing layer structure
- Usage-aware: Considers item usage frequency
- Preference-aware: Incorporates user constraints
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from services.data_preparation_service import (
    AIReadyContext,
    AIReadyItem,
    AIReadyWeather,
)


class PromptService:
    """
    Service for building structured prompts for VLMs.

    Converts Phase 2 AI-ready context into high-quality prompts
    optimized for LLaVA and similar models.
    """

    def __init__(self):
        """Initialize prompt service."""
        self.layer_names = {
            1: "Base Layer",
            2: "Insulation Layer",
            3: "Outer Layer",
        }

    # ========================================================================
    # PRIMARY PROMPT BUILDERS (Phase 2 AIReadyContext → Final Prompts)
    # ========================================================================

    def build_daily_prompt_from_context(self, context: AIReadyContext) -> str:
        """
        Build a high-quality prompt for daily outfit recommendation.

        This prompt guides the VLM to:
        - Suggest exactly one complete outfit for today
        - Use ONLY items from the provided wardrobe
        - Consider weather conditions
        - Consider usage frequency (avoid overused items)
        - Respect realistic layering
        - Provide clear reasoning

        Args:
            context: AIReadyContext from Phase 2 data preparation

        Returns:
            Final prompt string ready for VLM submission
        """
        # Extract components from context
        weather = context.weather_current
        wardrobe_by_layer = context.wardrobe_by_layer
        constraints = context.user_constraints

        # Build the prompt in sections
        prompt_parts = []

        # 1. ROLE & SYSTEM MESSAGE
        prompt_parts.append(self._build_system_message_daily())

        # 2. WEATHER CONTEXT
        prompt_parts.append(self._format_weather_section(weather))

        # 3. WARDROBE INVENTORY (grouped by layer)
        prompt_parts.append(self._format_wardrobe_section(wardrobe_by_layer))

        # 4. USAGE FREQUENCY GUIDANCE
        prompt_parts.append(self._format_usage_frequency_section(wardrobe_by_layer))

        # 5. USER CONSTRAINTS & PREFERENCES
        prompt_parts.append(self._format_constraints_section(constraints))

        # 6. EXPLICIT RULES FOR REASONING
        prompt_parts.append(self._format_rules_section_daily())

        # 7. RESPONSE FORMAT SPECIFICATION
        prompt_parts.append(self._format_response_format_daily())

        # Combine all parts
        final_prompt = "\n".join(prompt_parts)
        return final_prompt

    def build_travel_prompt_from_context(self, context: AIReadyContext) -> str:
        """
        Build a high-quality prompt for travel outfit recommendations.

        This prompt guides the VLM to:
        - Suggest outfits for multiple days
        - Consider full weather forecast
        - Propose compact versatile packing
        - Use layering intelligently
        - Minimize repetition
        - Only use provided items
        - Provide reasoning for selections

        Args:
            context: AIReadyContext for travel (includes weather forecast)

        Returns:
            Final prompt string ready for VLM submission
        """
        wardrobe_by_layer = context.wardrobe_by_layer
        weather_forecast = context.weather_forecast
        constraints = context.user_constraints
        metadata = context.metadata

        # Extract number of days from metadata
        num_days = metadata.get("num_days", len(weather_forecast))
        luggage_limit = metadata.get("luggage_limit", 10)

        prompt_parts = []

        # 1. ROLE & SYSTEM MESSAGE
        prompt_parts.append(self._build_system_message_travel(num_days, luggage_limit))

        # 2. WEATHER FORECAST
        prompt_parts.append(
            self._format_weather_forecast_section(weather_forecast, num_days)
        )

        # 3. WARDROBE INVENTORY
        prompt_parts.append(self._format_wardrobe_section(wardrobe_by_layer))

        # 4. USAGE FREQUENCY GUIDANCE
        prompt_parts.append(self._format_usage_frequency_section(wardrobe_by_layer))

        # 5. USER CONSTRAINTS
        prompt_parts.append(self._format_constraints_section(constraints))

        # 6. PACKING REQUIREMENTS & RULES
        prompt_parts.append(self._format_rules_section_travel(num_days, luggage_limit))

        # 7. RESPONSE FORMAT
        prompt_parts.append(self._format_response_format_travel(num_days))

        final_prompt = "\n".join(prompt_parts)
        return final_prompt

    def build_alternative_prompt_from_context(
        self,
        context: AIReadyContext,
        current_outfit_item_ids: Optional[List[str]] = None,
    ) -> str:
        """
        Build a high-quality prompt for alternative outfit suggestions.

        This prompt guides the VLM to:
        - Suggest alternative outfits (not repeating the current one)
        - Preserve weather compatibility
        - Increase variety in suggestions
        - Use realistic combinations
        - Provide reasoning for each alternative

        Args:
            context: AIReadyContext for alternative recommendations
            current_outfit_item_ids: Item IDs of the current outfit (optional)

        Returns:
            Final prompt string ready for VLM submission
        """
        wardrobe_by_layer = context.wardrobe_by_layer
        weather = context.weather_current
        constraints = context.user_constraints

        prompt_parts = []

        # 1. ROLE & SYSTEM MESSAGE
        prompt_parts.append(self._build_system_message_alternative())

        # 2. CURRENT OUTFIT (if provided)
        if current_outfit_item_ids:
            prompt_parts.append(
                self._format_current_outfit_section(
                    wardrobe_by_layer, current_outfit_item_ids
                )
            )

        # 3. WEATHER CONTEXT
        prompt_parts.append(self._format_weather_section(weather))

        # 4. WARDROBE INVENTORY
        prompt_parts.append(self._format_wardrobe_section(wardrobe_by_layer))

        # 5. USAGE FREQUENCY
        prompt_parts.append(self._format_usage_frequency_section(wardrobe_by_layer))

        # 6. USER CONSTRAINTS
        prompt_parts.append(self._format_constraints_section(constraints))

        # 7. RULES FOR ALTERNATIVES
        prompt_parts.append(self._format_rules_section_alternative())

        # 8. RESPONSE FORMAT
        prompt_parts.append(self._format_response_format_alternative())

        final_prompt = "\n".join(prompt_parts)
        return final_prompt

    # ========================================================================
    # SYSTEM MESSAGE BUILDERS
    # ========================================================================

    def _build_system_message_daily(self) -> str:
        """Build the system/role message for daily recommendations."""
        return """================================================================================
OUTFIT RECOMMENDATION SYSTEM - DAILY OUTFIT SUGGESTION
================================================================================

You are an expert personal stylist and wardrobe consultant with deep knowledge of:
- Climate and weather-appropriate clothing
- Color coordination and style harmony
- Garment layering and construction
- Fashion practicality and real-world wearability

Your task is to suggest exactly ONE complete outfit for today.

CRITICAL INSTRUCTIONS:
1. You may ONLY select items from the wardrobe inventory below (Layers 1, 2, or 3)
2. You must NOT invent or suggest clothing that does not exist in the inventory
3. You must provide a complete outfit using items from available layers
4. You MUST explain your reasoning in detail
5. You MUST respect realistic garment layering (lighter under heavier)
6. You MUST consider item usage frequency to avoid over-wearing items

================================================================================
"""

    def _build_system_message_travel(self, num_days: int, luggage_limit: int) -> str:
        """Build the system/role message for travel recommendations."""
        return f"""================================================================================
OUTFIT RECOMMENDATION SYSTEM - TRAVEL WARDROBE PLANNING
================================================================================

You are an expert travel wardrobe strategist with expertise in:
- Packing efficiently for multi-day trips
- Creating versatile outfits from minimal items
- Layering for variable weather conditions
- Mixing and matching clothing for maximum variety

Your task is to plan a {num_days}-day wardrobe using items from Layers 1, 2, 3, staying within {luggage_limit} items maximum.

CRITICAL INSTRUCTIONS:
1. You may ONLY select items from the wardrobe inventory below (from Layers 1, 2, 3)
2. You must NOT invent or suggest clothing that does not exist
3. You must create {num_days} different daily outfit combinations
4. You must stay within the {luggage_limit}-item luggage limit
5. You MUST minimize repetition (same items should appear in different outfit combinations)
6. You MUST explain how items will be mixed and matched across days
7. You MUST respect realistic layering and weather appropriateness
8. You MUST provide clear reasoning for all selections

Goal: Pack smart, dress well, travel light.

================================================================================
"""

    def _build_system_message_alternative(self) -> str:
        """Build the system/role message for alternative recommendations."""
        return """================================================================================
OUTFIT RECOMMENDATION SYSTEM - ALTERNATIVE OUTFIT SUGGESTIONS
================================================================================

You are a fashion creative with expertise in:
- Finding fresh style directions while maintaining coherence
- Maximizing wardrobe versatility
- Creating outfit variety from a single closet
- Substituting pieces while preserving the overall aesthetic

Your task is to suggest 3 meaningfully different alternative outfits using items from Layers 1, 2, 3.

CRITICAL INSTRUCTIONS:
1. You may ONLY select items from the wardrobe inventory below (from Layers 1, 2, 3)
2. You must NOT invent or suggest clothing that does not exist
3. You must suggest 3 distinct alternatives - each should be noticeably different from the others
4. Each alternative must be weather-appropriate and realistic
5. You MUST avoid simply repeating the original outfit
6. You MUST explain what makes each alternative unique and why it works
7. You MUST respect realistic garment layering
8. All suggestions should maintain consistent quality and wearability

Each alternative should offer a genuinely different style direction or vibe.

================================================================================
"""

    # ========================================================================
    # CONTEXT FORMATTING SECTIONS
    # ========================================================================

    def _format_weather_section(self, weather: Optional[AIReadyWeather]) -> str:
        """Format weather conditions for the prompt."""
        if not weather:
            return """WEATHER CONDITIONS:
No weather data available - suggest all-purpose outfit.
"""

        temp = (
            weather.temperature
            if hasattr(weather, "temperature")
            else (weather.temperature_min + weather.temperature_max) / 2
        )
        feels_like = weather.feels_like if hasattr(weather, "feels_like") else temp

        section = f"""WEATHER CONDITIONS TODAY:
- Current Temperature: {temp}°C (feels like {feels_like}°C)
- Temperature Range: {weather.temperature_min}°C to {weather.temperature_max}°C
- Condition: {weather.condition.capitalize()}
- Humidity: {weather.humidity}%
- Wind Speed: {weather.wind_speed} km/h
- Description: {weather.description if hasattr(weather, "description") else "Standard conditions"}

WEATHER IMPLICATIONS:
- Temperature suggests layering strategy (warm/cool)
- Condition determines waterproofing/windproofing needs
- Humidity may require breathable fabrics

"""
        return section

    def _format_weather_forecast_section(
        self, weather_forecast: List[AIReadyWeather], num_days: int
    ) -> str:
        """Format weather forecast for the prompt."""
        section = f"""WEATHER FORECAST ({num_days} DAYS):
"""
        for i, day_weather in enumerate(weather_forecast[:num_days], 1):
            date_str = day_weather.date if hasattr(day_weather, "date") else f"Day {i}"
            precip_prob = (
                day_weather.precipitation_probability
                if hasattr(day_weather, "precipitation_probability")
                else "Unknown"
            )
            section += f"""
Day {i} ({date_str}):
  - Temperature Range: {day_weather.temperature_min}°C to {day_weather.temperature_max}°C
  - Condition: {day_weather.condition.capitalize()}
  - Precipitation Chance: {precip_prob}%
  - Humidity: {day_weather.humidity}%
  - Wind: {day_weather.wind_speed} km/h
"""

        section += """

FORECAST INTERPRETATION:
- Review all days to identify weather patterns
- Look for consistent conditions (all warm, all rainy, etc.) or variable conditions
- Select items that work across the temperature range
- Prioritize versatile pieces that adapt to multiple conditions

"""
        return section

    def _format_wardrobe_section(
        self, wardrobe_by_layer: Dict[int, List[AIReadyItem]]
    ) -> str:
        """Format wardrobe inventory grouped by layer."""
        section = """================================================================================
AVAILABLE WARDROBE INVENTORY (Organized by Layer):
================================================================================

"""
        for layer_num in sorted(wardrobe_by_layer.keys()):
            layer_name = self.layer_names.get(layer_num, f"Layer {layer_num}")
            items = wardrobe_by_layer[layer_num]

            if not items:
                section += f"\n{layer_name}: (No items available)\n"
                continue

            section += f"\n{layer_name}:\n"
            for item in items:
                section += f"  • {item.name} [ID: {item.id}]\n"
                section += f"      Type: {item.type} | Color: {item.color} | Brand: {item.brand}\n"
                section += (
                    f"      Temperature Range: {item.temp_min}°C to {item.temp_max}°C\n"
                )

                # Add special properties
                properties = []
                if item.waterproof:
                    properties.append("Waterproof")
                if item.windproof:
                    properties.append("Windproof")
                if item.favorite:
                    properties.append("Favorite")
                if properties:
                    section += f"      Properties: {', '.join(properties)}\n"

                # Add materials if available
                if item.materials:
                    section += f"      Materials: {', '.join(item.materials)}\n"

                # Add usage frequency
                usage = (
                    item.usage_metrics.get("usage_frequency_last_7_days", 0)
                    if item.usage_metrics
                    else 0
                )
                section += f"      Used in last 7 days: {usage} times\n"

        section += """
WARDROBE RULES:
- Items are organized by 3 layers: Base (Layer 1) → Insulation (Layer 2) → Outer (Layer 3)
- Layer 3 includes all outer items: jackets, coats, shoes, hats, scarves, and accessories
- Realistic outfits use ONE item from most layers (but not all layers are required)
- Base layer items go closest to skin; outer layer items go on top
- Shoes and accessories are selected from Layer 3 items by type

"""
        return section

    def _format_usage_frequency_section(
        self, wardrobe_by_layer: Dict[int, List[AIReadyItem]]
    ) -> str:
        """Format usage frequency guidance."""
        # Calculate average usage to determine "overused" threshold
        all_items = []
        for items in wardrobe_by_layer.values():
            all_items.extend(items)

        if not all_items:
            return ""

        usages = [
            item.usage_metrics.get("usage_frequency_last_7_days", 0)
            for item in all_items
            if item.usage_metrics
        ]
        avg_usage = sum(usages) / len(usages) if usages else 0

        section = f"""USAGE FREQUENCY GUIDANCE:

PRINCIPLE: Avoid over-wearing items when good alternatives exist.

- Average usage (last 7 days): {avg_usage:.1f} times per item
- Items used 0 times: Fresh options, good candidates
- Items used 1-2 times: Well-balanced usage
- Items used 3+ times: Popular items, consider alternatives if available

STRATEGY:
1. Prefer items with lower recent usage (0-2 times in last week)
2. Only suggest heavily-used items if no suitable alternatives exist
3. Consider total outfit balance (don't put 2+ heavily-used items together)
4. Favorite items may be worn more but don't force them if alternatives are better

"""
        return section

    def _format_constraints_section(self, constraints: Optional[Dict[str, Any]]) -> str:
        """Format user preferences and constraints."""
        if not constraints:
            return """USER PREFERENCES & CONSTRAINTS:
No specific preferences provided. Suggest a practical, weather-appropriate outfit.

"""

        section = "USER PREFERENCES & CONSTRAINTS:\n"

        if "style" in constraints:
            section += f"- Preferred Style: {constraints['style']}\n"

        if "occasion" in constraints:
            section += f"- Occasion/Activity: {constraints['occasion']}\n"

        if "color_preferences" in constraints:
            colors = constraints["color_preferences"]
            section += f"- Preferred Colors: {', '.join(colors) if isinstance(colors, list) else colors}\n"

        if "avoid_colors" in constraints:
            colors = constraints["avoid_colors"]
            section += f"- Colors to Avoid: {', '.join(colors) if isinstance(colors, list) else colors}\n"

        if "avoid_items" in constraints:
            items = constraints["avoid_items"]
            section += f"- Items to Avoid: {', '.join(items) if isinstance(items, list) else items}\n"

        if "comfort_level" in constraints:
            section += f"- Comfort Level: {constraints['comfort_level']}\n"

        if "dress_code" in constraints:
            section += f"- Dress Code: {constraints['dress_code']}\n"

        if "additional_notes" in constraints:
            section += f"- Additional Notes: {constraints['additional_notes']}\n"

        section += "\nRESPECT ALL CONSTRAINTS in your recommendations.\n\n"

        return section

    def _format_rules_section_daily(self) -> str:
        """Format explicit reasoning rules for daily recommendations."""
        return """================================================================================
EXPLICIT RULES FOR REASONING:
================================================================================

1. TEMPERATURE MATCHING:
   ✓ Check each item's temperature range against today's weather
   ✓ Suggest items suitable for the temperature
   ✗ Do NOT suggest items outside their temperature range

2. WEATHER SUITABILITY:
   ✓ If rainy: select waterproof outer items
   ✓ If windy: select windproof items
   ✓ If sunny: consider light colors or sun-protective items
   ✗ Do NOT suggest inadequate protection

3. LAYER COHERENCE:
   ✓ Build from skin outward: base → insulation → outer
   ✓ Ensure layers work together visually and functionally
   ✓ Thickness should increase as temperature decreases
   ✗ Do NOT create nonsensical layer combinations

4. COLOR & STYLE COORDINATION:
   ✓ Colors should complement each other
   ✓ Style should be cohesive (all casual, all formal, or intentionally mixed)
   ✓ Consider contrast and balance
   ✗ Do NOT create clashing or discordant outfits

5. USAGE FREQUENCY:
   ✓ Prefer items with lower 7-day usage when alternatives exist
   ✓ Only select heavily-used items if they are the best fit
   ✗ Do NOT suggest the same items repeatedly

6. REALISM:
   ✓ Suggest only complete, wearable outfits
   ✓ Items should be appropriate for the context and occasion
   ✗ Do NOT suggest experimental or unrealistic combinations

================================================================================
"""

    def _format_rules_section_travel(self, num_days: int, luggage_limit: int) -> str:
        """Format explicit reasoning rules for travel recommendations."""
        return f"""================================================================================
EXPLICIT RULES FOR TRAVEL PACKING & OUTFIT PLANNING:
================================================================================

1. VERSATILITY PRINCIPLE:
   ✓ Select items that can be worn in multiple outfit combinations
   ✓ Prioritize pieces that work with many others
   ✗ Do NOT select single-use or one-outfit items

2. WEATHER COVERAGE:
   ✓ Review entire forecast - select items for the full range of conditions
   ✓ Choose layering pieces that adapt to temperature variations
   ✗ Do NOT optimize for only one day's weather

3. PACKING CONSTRAINTS:
   ✓ Total items to pack must NOT exceed {luggage_limit} items
   ✓ Focus on quantity that fits in {luggage_limit} pieces
   ✗ Do NOT suggest more items than the luggage limit

4. OUTFIT VARIETY (for {num_days} days):
   ✓ Create {num_days} distinctly different daily outfit combinations
   ✓ Minimize same-item repetition across consecutive days
   ✓ Use colors and pieces in different ways each day
   ✗ Do NOT repeat the exact same outfit on consecutive days

5. MIXING & MATCHING:
   ✓ Every selected item must work in at least 2 different outfit combinations
   ✓ Plan how items will be mixed across days (explain in packing notes)
   ✓ Ensure accessory/shoe variety without excessive packing
   ✗ Do NOT pack items that only work in one outfit

6. TEMPERATURE ADAPTATION:
   ✓ Pack layers to handle temperature range across all days
   ✓ Favor adjustable layers (add/remove as needed)
   ✗ Do NOT require entirely different wardrobes for different days

7. REALISTIC OUTFITS:
   ✓ Each day's outfit must be complete and wearable
   ✓ All items must be available from packing list
   ✗ Do NOT suggest items not in the packing list for any day

================================================================================
"""

    def _format_rules_section_alternative(self) -> str:
        """Format explicit reasoning rules for alternative recommendations."""
        return """================================================================================
EXPLICIT RULES FOR ALTERNATIVE SUGGESTIONS:
================================================================================

1. MEANINGFUL DIFFERENTIATION:
   ✓ Each alternative must be noticeably different from the original
   ✓ Alternatives should have distinct vibes or purposes
   ✓ Variety makes alternatives actually useful
   ✗ Do NOT suggest minor variations (same outfit + one swapped piece)

2. WEATHER COMPATIBILITY:
   ✓ Every alternative must be suitable for today's weather
   ✓ Cannot suggest alternatives that conflict with forecast
   ✗ Do NOT suggest weather-inappropriate outfits

3. UNIQUE STYLE DIRECTIONS:
   Consider these approaches for variety:
   - Alternative 1: Different occasion (casual vs. polished, sporty vs. formal, etc.)
   - Alternative 2: Different color palette or mood
   - Alternative 3: Different layer strategy (minimal vs. maximum, etc.)
   ✗ Do NOT suggest copies of the same base outfit

4. COHERENCE:
   ✓ Each alternative must be internally consistent
   ✓ Colors and style must work together within each alternative
   ✗ Do NOT create random or clashing combinations

5. USAGE FREQUENCY:
   ✓ Consider spreading usage across different items
   ✓ Use less-worn items in alternatives
   ✗ Do NOT suggest identical heavy-use patterns in all alternatives

6. PRACTICALITY:
   ✓ All suggestions must be genuinely wearable
   ✓ Consider the original outfit's context/occasion
   ✓ Alternatives should be real-world useful
   ✗ Do NOT suggest impractical or experimental outfits

================================================================================
"""

    def _format_current_outfit_section(
        self,
        wardrobe_by_layer: Dict[int, List[AIReadyItem]],
        current_outfit_item_ids: List[str],
    ) -> str:
        """Format the current outfit for reference when suggesting alternatives."""
        section = "ORIGINAL OUTFIT (For Reference - Do Not Simply Repeat):\n"

        # Find the current outfit items
        all_items = []
        for items in wardrobe_by_layer.values():
            all_items.extend(items)

        current_items = [
            item for item in all_items if item.id in current_outfit_item_ids
        ]

        if current_items:
            for item in current_items:
                section += f"  • {item.name} ({item.color}) [ID: {item.id}]\n"
        else:
            section += "  (No items identified)\n"

        section += """
Your alternatives must differ meaningfully from this original outfit.

"""
        return section

    # ========================================================================
    # RESPONSE FORMAT SPECIFICATIONS
    # ========================================================================

    def _format_response_format_daily(self) -> str:
        """Format the response specification for daily recommendations."""
        return """================================================================================
REQUIRED RESPONSE FORMAT:
================================================================================

You must provide your response in EXACTLY the following format.
Do not deviate from this structure. Use item IDs as shown in inventory above.
All items must come from Layers 1, 2, or 3 of the inventory.

Base Layer (Layer 1):
[item name and ID, or "None" if not needed]

Insulation Layer (Layer 2):
[item name and ID, or "None" if not needed]

Outer Layer (Layer 3):
[item name and ID, or "None" if not needed]

Shoes (from Layer 3):
[item name and ID, or "None" if not needed]

Accessories (from Layer 3):
[item name and ID, or multiple items comma-separated, or "None"]

Reasoning:
[Your detailed explanation of why this outfit works today, covering:
- How it addresses the weather
- Why each piece was selected
- How colors and styles coordinate
- Any usage frequency considerations
- Overall coherence and practicality]

================================================================================

BEGIN YOUR RECOMMENDATION:
"""

    def _format_response_format_travel(self, num_days: int) -> str:
        """Format the response specification for travel recommendations."""
        response = """================================================================================
REQUIRED RESPONSE FORMAT:
================================================================================

Provide your response in EXACTLY the following structure.
Use item IDs as shown in the inventory above. Do NOT deviate from this format.
All items must come from Layers 1, 2, or 3 of the inventory.

"""
        for day in range(1, num_days + 1):
            response += f"""Day {day}:
Base Layer (Layer 1): [item name and ID, or "None"]
Insulation Layer (Layer 2): [item name and ID, or "None"]
Outer Layer (Layer 3): [item name and ID, or "None"]
Shoes (Layer 3): [item name and ID]
Accessories (Layer 3): [items or "None"]

"""

        response += """Packing List Summary:
[List all unique items to pack with their IDs. This is your final inventory to pack.]

Mixing & Matching Strategy:
[Explain how the selected items create multiple outfit combinations despite limited packing]

Reasoning:
[Provide overall rationale covering:
- How the packing list addresses the weather forecast
- How items are versatile across different combinations
- How you stayed within luggage constraints
- How each day's outfit is distinct yet uses common items
- Travel practicality considerations]

================================================================================

BEGIN YOUR TRAVEL PLAN:
"""
        return response

    def _format_response_format_alternative(self) -> str:
        """Format the response specification for alternative recommendations."""
        return """================================================================================
REQUIRED RESPONSE FORMAT:
================================================================================

Provide EXACTLY 3 alternatives in the following format.
Use item IDs from the inventory. Do not deviate from this structure.
All items must come from Layers 1, 2, or 3 of the inventory.

ALTERNATIVE 1:
Base Layer (Layer 1): [item name and ID, or "None"]
Insulation Layer (Layer 2): [item name and ID, or "None"]
Outer Layer (Layer 3): [item name and ID, or "None"]
Shoes (Layer 3): [item name and ID]
Accessories (Layer 3): [items or "None"]
Style Direction: [Brief description of this alternative's vibe/occasion]
Reason: [Why this is a good alternative and how it differs from the original]

ALTERNATIVE 2:
Base Layer (Layer 1): [item name and ID, or "None"]
Insulation Layer (Layer 2): [item name and ID, or "None"]
Outer Layer (Layer 3): [item name and ID, or "None"]
Shoes (Layer 3): [item name and ID]
Accessories (Layer 3): [items or "None"]
Style Direction: [Brief description of this alternative's vibe/occasion]
Reason: [Why this is a good alternative and how it differs from the original]

ALTERNATIVE 3:
Base Layer (Layer 1): [item name and ID, or "None"]
Insulation Layer (Layer 2): [item name and ID, or "None"]
Outer Layer (Layer 3): [item name and ID, or "None"]
Shoes (Layer 3): [item name and ID]
Accessories (Layer 3): [items or "None"]
Style Direction: [Brief description of this alternative's vibe/occasion]
Reason: [Why this is a good alternative and how it differs from the original]

================================================================================

BEGIN YOUR ALTERNATIVES:
"""

    # ========================================================================
    # LEGACY SUPPORT (Keep existing methods for backward compatibility)
    # ========================================================================

    def build_daily_outfit_prompt(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_data: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]] = None,
        occasion: Optional[str] = None,
    ) -> str:
        """
        Legacy method - builds prompt from raw dictionaries.

        Maintained for backward compatibility with Phase 1/2 code that
        passes raw dicts instead of AIReadyContext objects.

        Args:
            wardrobe_items: List of clothing items as dictionaries
            weather_data: Weather data dictionary
            user_preferences: User preferences dictionary
            occasion: Occasion string

        Returns:
            Formatted prompt string
        """
        wardrobe_description = self._format_wardrobe_legacy(wardrobe_items)
        weather_description = self._format_weather_legacy(weather_data)
        preferences_description = self._format_preferences_legacy(user_preferences)

        prompt = f"""You are an expert fashion stylist and personal wardrobe advisor.
Your task is to recommend an outfit for today based on the provided information.

WARDROBE ITEMS AVAILABLE:
{wardrobe_description}

WEATHER CONDITIONS:
{weather_description}

USER PREFERENCES:
{preferences_description}

{f"OCCASION/ACTIVITY: {occasion}" if occasion else ""}

TASK:
1. Analyze the available wardrobe items and their properties
2. Consider the weather conditions and temperature
3. Take into account the user's style preferences
4. Recommend a complete outfit (base layer, insulation layer, outer layer, shoes, and accessories as appropriate)
5. Explain your reasoning for the selection
6. Consider color coordination, style harmony, and practicality

RESPONSE FORMAT:
Provide your response with the following structure:
Base Layer: [item or "None"]
Insulation Layer: [item or "None"]
Outer Layer: [item or "None"]
Shoes: [item]
Accessories: [items or "None"]
Reasoning: [Your explanation]
"""
        return prompt

    def build_travel_outfit_prompt(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_forecast: List[Dict[str, Any]],
        num_days: int,
        user_preferences: Optional[Dict[str, Any]] = None,
        luggage_limit: int = 10,
    ) -> str:
        """
        Legacy method - builds travel prompt from raw dictionaries.

        Maintained for backward compatibility.

        Args:
            wardrobe_items: Available items to pack
            weather_forecast: Weather for each day
            num_days: Number of days for the trip
            user_preferences: User preferences
            luggage_limit: Maximum items to pack

        Returns:
            Formatted prompt for travel planning
        """
        wardrobe_description = self._format_wardrobe_legacy(wardrobe_items)
        forecast_description = self._format_forecast_legacy(weather_forecast, num_days)
        preferences_description = self._format_preferences_legacy(user_preferences)

        prompt = f"""You are an expert travel wardrobe planner and fashion stylist.
Your task is to recommend outfits for a {num_days}-day trip, optimizing for luggage space and versatility.

WARDROBE ITEMS AVAILABLE:
{wardrobe_description}

WEATHER FORECAST:
{forecast_description}

USER PREFERENCES:
{preferences_description}

CONSTRAINTS:
- Maximum items to pack: {luggage_limit}
- Trip duration: {num_days} days
- Need to create {num_days} different outfit combinations from the selected items

TASK:
1. Select the most versatile items that can create multiple outfit combinations
2. Ensure items work across the different weather conditions
3. Create a day-by-day outfit plan
4. Ensure total items packed doesn't exceed the luggage limit
5. Explain how items can be mixed and matched

RESPONSE FORMAT:
For each day (Day 1, Day 2, etc.), provide:
Day N:
Base Layer: [item or "None"]
Insulation Layer: [item or "None"]
Outer Layer: [item or "None"]
Shoes: [item]
Accessories: [items or "None"]

Packing List Summary: [All items to pack]
Mixing & Matching Strategy: [How items work across days]
Reasoning: [Overall explanation]
"""
        return prompt

    def build_alternative_outfit_prompt(
        self,
        current_outfit_items: List[Dict[str, Any]],
        all_wardrobe_items: List[Dict[str, Any]],
        weather_data: Dict[str, Any],
        num_alternatives: int = 3,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Legacy method - builds alternative prompt from raw dictionaries.

        Maintained for backward compatibility.

        Args:
            current_outfit_items: Items in the primary outfit
            all_wardrobe_items: All available items
            weather_data: Weather conditions
            num_alternatives: How many alternatives to suggest
            user_preferences: User preferences

        Returns:
            Formatted prompt for alternatives
        """
        current_description = self._format_wardrobe_legacy(
            current_outfit_items, title="PRIMARY OUTFIT"
        )
        all_items_description = self._format_wardrobe_legacy(
            all_wardrobe_items, title="ALL AVAILABLE ITEMS"
        )
        weather_description = self._format_weather_legacy(weather_data)
        preferences_description = self._format_preferences_legacy(user_preferences)

        prompt = f"""You are an expert fashion stylist providing alternative outfit suggestions.
Your task is to suggest {num_alternatives} alternative outfits that work with the current weather.

{current_description}

{all_items_description}

WEATHER CONDITIONS:
{weather_description}

USER PREFERENCES:
{preferences_description}

TASK:
1. Analyze the primary outfit and understand the style direction
2. Suggest {num_alternatives} distinctly different alternatives
3. Each must be suitable for the weather
4. Vary the alternatives (e.g., casual, dressy, practical, trendy)
5. Explain what's different and why it works

RESPONSE FORMAT:
For each alternative:
ALTERNATIVE N:
Base Layer: [item or "None"]
Insulation Layer: [item or "None"]
Outer Layer: [item or "None"]
Shoes: [item]
Accessories: [items or "None"]
Style Direction: [vibe/purpose]
Reason: [explanation]
"""
        return prompt

    # ========================================================================
    # LEGACY HELPER METHODS
    # ========================================================================

    def _format_wardrobe_legacy(
        self, items: List[Dict[str, Any]], title: str = "WARDROBE ITEMS AVAILABLE"
    ) -> str:
        """Legacy wardrobe formatting."""
        if not items:
            return f"{title}:\nNo items available"

        formatted = f"{title}:\n"
        for item in items:
            item_id = item.get("id", "unknown")
            name = item.get("name", "Unknown")
            item_type = item.get("type", "")
            color = item.get("color", "")
            formatted += f"- {name} [ID: {item_id}] ({color}) - {item_type}\n"

        return formatted

    def _format_weather_legacy(self, weather: Dict[str, Any]) -> str:
        """Legacy weather formatting."""
        temp = weather.get("temperature", "unknown")
        condition = weather.get("condition", "unknown")
        return f"""Current Conditions:
- Temperature: {temp}°C
- Condition: {condition.capitalize()}
"""

    def _format_forecast_legacy(
        self, forecast: List[Dict[str, Any]], num_days: int
    ) -> str:
        """Legacy forecast formatting."""
        formatted = ""
        for i, day_forecast in enumerate(forecast[:num_days]):
            temp_min = day_forecast.get("temperature_min", "?")
            temp_max = day_forecast.get("temperature_max", "?")
            condition = day_forecast.get("condition", "unknown")
            formatted += (
                f"\nDay {i + 1}: {temp_min}°C to {temp_max}°C, {condition.capitalize()}"
            )
        return formatted

    def _format_preferences_legacy(self, preferences: Optional[Dict[str, Any]]) -> str:
        """Legacy preferences formatting."""
        if not preferences:
            return "No specific preferences provided"

        formatted = ""
        if "style" in preferences:
            formatted += f"- Style: {preferences['style']}\n"
        if "occasion" in preferences:
            formatted += f"- Occasion: {preferences['occasion']}\n"
        if "color_preferences" in preferences:
            formatted += (
                f"- Color Preferences: {', '.join(preferences['color_preferences'])}\n"
            )

        return formatted if formatted else "No specific preferences provided"


class PromptServiceError(Exception):
    """Exception raised by PromptService."""

    pass
