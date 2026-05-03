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
- Hallucination-prevention: Strict rules against item invention
"""

from typing import Any, Dict, List

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
        if weather:
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

    def build_travel_prompt_from_context(
        self, context: AIReadyContext, num_days: int, luggage_limit: int
    ) -> str:
        """
        Build a prompt for travel wardrobe planning.

        This prompt guides the VLM to:
        - Create a {num_days}-day travel wardrobe
        - Use ONLY items from the provided wardrobe
        - Stay within luggage constraints
        - Create versatile outfit combinations
        - Provide clear packing and mixing strategy

        Args:
            context: AIReadyContext from Phase 2 data preparation
            num_days: Number of days for the trip
            luggage_limit: Maximum number of items to pack

        Returns:
            Final prompt string ready for VLM submission
        """
        # Extract components from context
        weather_forecast = context.weather_forecast
        wardrobe_by_layer = context.wardrobe_by_layer
        constraints = context.user_constraints

        # Build the prompt in sections
        prompt_parts = []

        # 1. ROLE & SYSTEM MESSAGE
        prompt_parts.append(self._build_system_message_travel(num_days, luggage_limit))

        # 2. WEATHER FORECAST
        prompt_parts.append(
            self._format_weather_forecast_section(weather_forecast, num_days)
        )

        # 3. WARDROBE INVENTORY (grouped by layer)
        prompt_parts.append(self._format_wardrobe_section(wardrobe_by_layer))

        # 4. USAGE FREQUENCY GUIDANCE
        prompt_parts.append(self._format_usage_frequency_section(wardrobe_by_layer))

        # 5. USER CONSTRAINTS & PREFERENCES
        prompt_parts.append(self._format_constraints_section(constraints))

        # 6. EXPLICIT RULES FOR TRAVEL
        prompt_parts.append(self._format_rules_section_travel(num_days, luggage_limit))

        # 7. RESPONSE FORMAT SPECIFICATION
        prompt_parts.append(self._format_response_format_travel(num_days))

        # Combine all parts
        final_prompt = "\n".join(prompt_parts)
        return final_prompt

    def build_alternative_prompt_from_context(self, context: AIReadyContext) -> str:
        """
        Build a prompt for alternative outfit suggestions.

        This prompt guides the VLM to:
        - Suggest 3 meaningfully different alternative outfits
        - Use ONLY items from the provided wardrobe
        - Maintain weather appropriateness
        - Provide variety while respecting realistic layering
        - Explain what makes each alternative unique

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
        prompt_parts.append(self._build_system_message_alternative())

        # 2. WEATHER CONTEXT
        if weather:
            prompt_parts.append(self._format_weather_section(weather))

        # 3. WARDROBE INVENTORY (grouped by layer)
        prompt_parts.append(self._format_wardrobe_section(wardrobe_by_layer))

        # 4. USAGE FREQUENCY GUIDANCE
        prompt_parts.append(self._format_usage_frequency_section(wardrobe_by_layer))

        # 5. USER CONSTRAINTS & PREFERENCES
        prompt_parts.append(self._format_constraints_section(constraints))

        # 6. EXPLICIT RULES FOR ALTERNATIVES
        prompt_parts.append(self._format_rules_section_alternative())

        # 7. CURRENT OUTFIT CONTEXT
        prompt_parts.append(self._format_current_outfit_section())

        # 8. RESPONSE FORMAT SPECIFICATION
        prompt_parts.append(self._format_response_format_alternative())

        # Combine all parts
        final_prompt = "\n".join(prompt_parts)
        return final_prompt

    # ========================================================================
    # SYSTEM MESSAGES (Role & Critical Instructions)
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
2. You MUST NOT invent or suggest any clothing that does not exist in the inventory
3. You MUST NOT output "PECAS_EM_FALTA", "Missing Items", or any mention of inventory gaps
4. You must provide a complete outfit using items from available layers
5. You MUST explain your reasoning in detail
6. You MUST respect realistic garment layering (lighter under heavier)
7. You MUST consider item usage frequency to avoid over-wearing items
8. If a layer has no suitable item, output "None" for that layer

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
2. You MUST NOT invent or suggest any clothing that does not exist
3. You MUST NOT output "PECAS_EM_FALTA", "Missing Items", or any mention of inventory gaps
4. You must create {num_days} different daily outfit combinations
5. You must stay within the {luggage_limit}-item luggage limit
6. You MUST minimize repetition (same items should appear in different outfit combinations)
7. You MUST explain how items will be mixed and matched across days
8. You MUST respect realistic layering and weather appropriateness
9. You MUST provide clear reasoning for all selections
10. If a layer has no suitable item for a day, output "None" for that layer

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
2. You MUST NOT invent or suggest any clothing that does not exist
3. You MUST NOT output "PECAS_EM_FALTA", "Missing Items", or any mention of inventory gaps
4. You must suggest 3 distinct alternatives - each should be noticeably different from the others
5. Each alternative must be weather-appropriate and realistic
6. You MUST avoid simply repeating the original outfit
7. You MUST explain what makes each alternative unique and why it works
8. You MUST respect realistic garment layering
9. All suggestions should maintain consistent quality and wearability
10. If a layer has no suitable item for an alternative, output "None" for that layer

Each alternative should offer a genuinely different style direction or vibe.

================================================================================
"""

    # ========================================================================
    # FORMATTING SECTIONS
    # ========================================================================

    def _format_weather_section(self, weather: AIReadyWeather) -> str:
        """Format current weather information."""
        section = """================================================================================
CURRENT WEATHER CONDITIONS:
================================================================================

"""
        section += f"Temperature: {weather.temperature}°C\n"
        section += f"Feels Like: {weather.feels_like}°C\n"
        section += f"Condition: {weather.condition}\n"
        section += f"Humidity: {weather.humidity}%\n"
        section += f"Wind Speed: {weather.wind_speed} km/h\n"

        if hasattr(weather, "description") and weather.description:
            section += f"Description: {weather.description}\n"

        section += "\n"
        return section

    def _format_weather_forecast_section(
        self, forecast: List[AIReadyWeather], num_days: int
    ) -> str:
        """Format weather forecast for multiple days."""
        section = f"""================================================================================
WEATHER FORECAST ({num_days} DAYS):
================================================================================

"""
        for i, day_weather in enumerate(forecast[:num_days], 1):
            section += f"Day {i}:\n"
            if hasattr(day_weather, "temperature"):
                section += f"  Temperature: {day_weather.temperature}°C\n"
            else:
                section += f"  Temperature Range: {day_weather.temperature_min}°C to {day_weather.temperature_max}°C\n"

            section += f"  Condition: {day_weather.condition}\n"
            section += f"  Humidity: {day_weather.humidity}%\n"
            section += f"  Wind Speed: {day_weather.wind_speed} km/h\n"

            if (
                hasattr(day_weather, "precipitation_probability")
                and day_weather.precipitation_probability
            ):
                section += f"  Precipitation Chance: {day_weather.precipitation_probability}%\n"
            section += "\n"

        return section

    def _format_wardrobe_section(
        self, wardrobe_by_layer: Dict[int, List[AIReadyItem]]
    ) -> str:
        """
        Format wardrobe inventory grouped by layer with strict layer metadata.

        This enhanced format prevents layer misclassification by including
        explicit layer rules and item metadata that helps the VLM understand
        which items belong in which layers.
        """
        section = """================================================================================
AVAILABLE WARDROBE INVENTORY (Organized by Layer):
================================================================================

LAYER STRUCTURE & VALIDATION RULES:
- Layer 1 (Base Layer): Closest to skin. MUST contain: t-shirt, tshirt, shirt, top, camiseta, camisola fina, base
- Layer 2 (Insulation Layer): Middle layer. MUST contain: sweater, hoodie, cardigan, pullover, trousers, pants, jeans, calças, camisola
- Layer 3 (Outer Layer): Outermost. MUST contain: jacket, coat, parka, blazer, casaco, SHOES, sneakers, boots, sapatilhas, calçado, hat, cap, beanie, accessories

STRICT LAYER RULES:
✓ A jacket/casaco MUST ONLY be in Outer Layer (Layer 3)
✓ Shoes/calçado/sneakers/boots MUST ONLY be in Outer Layer (Layer 3)
✓ T-shirts/tops MUST ONLY be in Base Layer (Layer 1)
✓ Trousers/pants/jeans/calças MUST ONLY be in Insulation Layer (Layer 2)
✗ A jacket can NEVER be in Base Layer or Insulation Layer
✗ Shoes can NEVER be in Base Layer or Insulation Layer
✗ T-shirts can NEVER be in Outer Layer or as shoes

"""

        for layer_num in sorted(wardrobe_by_layer.keys()):
            layer_name = self.layer_names.get(layer_num, f"Layer {layer_num}")
            items = wardrobe_by_layer[layer_num]

            if not items:
                section += f"\n{layer_name}: (No items available)\n"
                continue

            section += f"\n{layer_name} (Layer {layer_num}):\n"
            section += "─" * 80 + "\n"

            for item in items:
                # Format each item with detailed layer metadata
                section += f"ITEM ID: {item.id}\n"
                section += f"NAME: {item.name}\n"
                section += f"TYPE: {item.type}\n"
                section += f"LAYER: {layer_num} - {layer_name}\n"

                # Add layer-specific validity information
                if layer_num == 1:
                    section += "VALID ONLY FOR: Base Layer (Layer 1) - underwear, t-shirts, tops, base layers\n"
                elif layer_num == 2:
                    section += "VALID ONLY FOR: Insulation Layer (Layer 2) - sweaters, cardigans, trousers, pants\n"
                elif layer_num == 3:
                    section += "VALID ONLY FOR: Outer Layer (Layer 3) - jackets, coats, shoes, accessories\n"

                section += f"STATUS: {'Clean' if item.status == 'clean' else 'Dirty'}\n"
                section += f"TEMPERATURE: {item.temp_min}°C to {item.temp_max}°C\n"

                # Add color and brand
                section += f"COLOR: {item.color} | BRAND: {item.brand}\n"

                # Add special properties
                properties = []
                if item.waterproof:
                    properties.append("Waterproof")
                if item.windproof:
                    properties.append("Windproof")
                if item.favorite:
                    properties.append("Favorite")
                if properties:
                    section += f"PROPERTIES: {', '.join(properties)}\n"

                # Add materials if available
                if item.materials:
                    section += f"MATERIALS: {', '.join(item.materials)}\n"

                # Add usage frequency
                usage = (
                    item.usage_metrics.get("usage_frequency_last_7_days", 0)
                    if item.usage_metrics
                    else 0
                )
                section += f"USAGE (last 7 days): {usage} times\n"
                section += "\n"

        section += """================================================================================
INVENTORY USAGE INSTRUCTIONS:
- You MUST select items ONLY from the layers shown above
- You MUST respect the layer structure (Base → Insulation → Outer)
- You MUST NOT invent any items not listed here
- You MUST NOT mention any missing items or inventory gaps
- You MUST select items with STATUS: Clean only
- Items marked "Dirty" are NOT available for recommendation

================================================================================
"""
        return section

    def _format_usage_frequency_section(
        self, wardrobe_by_layer: Dict[int, List[AIReadyItem]]
    ) -> str:
        """Format usage frequency guidance to prevent over-wearing items."""
        section = """================================================================================
USAGE FREQUENCY GUIDANCE:
================================================================================

Items are tracked for usage frequency over the last 7 days.
When multiple items could work equally well, PREFER items with lower usage counts.

Rationale:
- Items with 0 times used should be prioritized (great opportunities to wear new items)
- Items used 1-2 times are good selections
- Items used 3+ times should only be selected if they are clearly the best fit
- Highly worn items (5+ times) should only be selected in exceptional cases

This helps maintain a healthy rotation and prevents outfit boredom.

Current usage summary by layer:

"""

        for layer_num in sorted(wardrobe_by_layer.keys()):
            layer_name = self.layer_names.get(layer_num, f"Layer {layer_num}")
            items = wardrobe_by_layer[layer_num]

            if not items:
                continue

            section += f"\n{layer_name}:\n"
            for item in items:
                usage = (
                    item.usage_metrics.get("usage_frequency_last_7_days", 0)
                    if item.usage_metrics
                    else 0
                )
                section += f"  • {item.name} [ID: {item.id}]: used {usage} times\n"

        section += "\n"
        return section

    def _format_constraints_section(self, constraints: Dict[str, Any]) -> str:
        """Format user constraints and preferences."""
        section = """================================================================================
USER PREFERENCES & CONSTRAINTS:
================================================================================

"""
        if constraints:
            if "forbidden_items" in constraints and constraints["forbidden_items"]:
                section += (
                    f"Forbidden Items: {', '.join(constraints['forbidden_items'])}\n"
                )
            if "preferred_colors" in constraints and constraints["preferred_colors"]:
                section += (
                    f"Preferred Colors: {', '.join(constraints['preferred_colors'])}\n"
                )
            if "preferred_styles" in constraints and constraints["preferred_styles"]:
                section += (
                    f"Preferred Styles: {', '.join(constraints['preferred_styles'])}\n"
                )
            if "occasion" in constraints and constraints["occasion"]:
                section += f"Occasion: {constraints['occasion']}\n"
        else:
            section += "No specific constraints provided.\n"

        section += "\n"
        return section

    def _format_rules_section_daily(self) -> str:
        """
        Format explicit reasoning rules for daily recommendations.

        These rules emphasize:
        - Strict layer validation
        - Prevention of hallucination/invention
        - Clean item selection only
        - Realistic layering
        """
        return """================================================================================
EXPLICIT RULES FOR REASONING:
================================================================================

RULE 0: STRICT INVENTORY COMPLIANCE
   ✓ You may ONLY use items provided in the inventory above
   ✓ You MUST select from Layer 1, Layer 2, and/or Layer 3 items
   ✗ You MUST NOT invent, assume, or mention any items not in the inventory
   ✗ You MUST NOT output "PECAS_EM_FALTA", "Missing Items", or item gaps
   ✗ Do NOT use items marked as "Dirty"

RULE 1: LAYER VALIDATION (CRITICAL)
   ✓ Check each item's LAYER assignment in the inventory above
   ✓ Base Layer (Layer 1): ONLY t-shirts, tops, base garments
   ✓ Insulation Layer (Layer 2): ONLY sweaters, cardigans, trousers, pants
   ✓ Outer Layer (Layer 3): ONLY jackets, coats, shoes, accessories
   ✗ A jacket can NEVER appear in Base Layer or Insulation Layer
   ✗ Shoes can NEVER appear in Base Layer or Insulation Layer
   ✗ T-shirts can NEVER appear in Outer Layer

RULE 2: TEMPERATURE MATCHING:
   ✓ Check each item's temperature range against today's weather
   ✓ Suggest items suitable for the temperature
   ✗ Do NOT suggest items outside their temperature range

RULE 3: WEATHER SUITABILITY:
   ✓ If rainy: select waterproof outer items
   ✓ If windy: select windproof items
   ✓ If sunny: consider light colors or sun-protective items
   ✗ Do NOT suggest inadequate protection

RULE 4: LAYER COHERENCE:
   ✓ Build from skin outward: Base → Insulation → Outer
   ✓ Ensure layers work together visually and functionally
   ✓ Thickness should increase as temperature decreases
   ✗ Do NOT create nonsensical layer combinations

RULE 5: COLOR & STYLE COORDINATION:
   ✓ Colors should complement each other
   ✓ Style should be cohesive (all casual, all formal, or intentionally mixed)
   ✓ Consider contrast and balance
   ✗ Do NOT create clashing or discordant outfits

RULE 6: USAGE FREQUENCY:
   ✓ Prefer items with lower 7-day usage when alternatives exist
   ✓ Only select heavily-used items if they are the best fit
   ✗ Do NOT suggest the same items repeatedly

RULE 7: CLEAN ITEMS ONLY:
   ✓ Check STATUS field - only select items marked "Clean"
   ✗ Do NOT recommend dirty items

RULE 8: COMPLETENESS:
   ✓ Every outfit MUST include Base Layer and Shoes
   ✓ Insulation Layer and Outer Layer are optional but recommended for cold weather
   ✓ Accessories are optional
   ✓ If a layer has no suitable item, output "None" for that layer

================================================================================
"""

    def _format_rules_section_travel(self, num_days: int, luggage_limit: int) -> str:
        """
        Format explicit reasoning rules for travel recommendations.

        These rules emphasize:
        - Strict inventory compliance
        - Packing constraints
        - Versatility and mixing
        - Layer validation
        """
        return f"""================================================================================
EXPLICIT RULES FOR TRAVEL PACKING & OUTFIT PLANNING:
================================================================================

RULE 0: STRICT INVENTORY COMPLIANCE
   ✓ You may ONLY use items provided in the inventory above
   ✓ You MUST select from Layer 1, Layer 2, and/or Layer 3 items
   ✗ You MUST NOT invent, assume, or mention any items not in the inventory
   ✗ You MUST NOT output "PECAS_EM_FALTA", "Missing Items", or item gaps
   ✗ Do NOT use items marked as "Dirty"

RULE 1: LAYER VALIDATION (CRITICAL)
   ✓ Check each item's LAYER assignment in the inventory above
   ✓ Base Layer (Layer 1): ONLY t-shirts, tops, base garments
   ✓ Insulation Layer (Layer 2): ONLY sweaters, cardigans, trousers, pants
   ✓ Outer Layer (Layer 3): ONLY jackets, coats, shoes, accessories
   ✗ A jacket can NEVER appear in Base Layer or Insulation Layer
   ✗ Shoes can NEVER appear in Base Layer or Insulation Layer
   ✗ T-shirts can NEVER appear in Outer Layer

RULE 2: PACKING CONSTRAINTS
   ✓ Total items to pack must NOT exceed {luggage_limit} items
   ✓ Focus on quantity that fits in {luggage_limit} pieces
   ✗ Do NOT suggest more items than the luggage limit

RULE 3: VERSATILITY PRINCIPLE:
   ✓ Select items that can be worn in multiple outfit combinations
   ✓ Prioritize pieces that work with many others
   ✗ Do NOT select single-use or one-outfit items

RULE 4: WEATHER COVERAGE:
   ✓ Review entire forecast - select items for the full range of conditions
   ✓ Choose layering pieces that adapt to temperature variations
   ✗ Do NOT optimize for only one day's weather

RULE 5: OUTFIT VARIETY (for {num_days} days):
   ✓ Create {num_days} distinctly different daily outfit combinations
   ✓ Minimize same-item repetition across consecutive days
   ✓ Use colors and pieces in different ways each day
   ✗ Do NOT repeat the exact same outfit on consecutive days

RULE 6: MIXING & MATCHING:
   ✓ Every selected item must work in at least 2 different outfit combinations
   ✓ Plan how items will be mixed across days (explain in packing notes)
   ✓ Ensure accessory/shoe variety without excessive packing
   ✗ Do NOT pack items that only work in one outfit

RULE 7: TEMPERATURE ADAPTATION:
   ✓ Pack layers to handle temperature range across all days
   ✓ Favor adjustable layers (add/remove as needed)
   ✗ Do NOT require entirely different wardrobes for different days

RULE 8: CLEAN ITEMS ONLY:
   ✓ Check STATUS field - only select items marked "Clean"
   ✗ Do NOT recommend dirty items

RULE 9: REALISTIC OUTFITS:
   ✓ Each day's outfit must be complete and wearable
   ✓ All items must be available from packing list
   ✗ Do NOT suggest items not in the packing list for any day

================================================================================
"""

    def _format_rules_section_alternative(self) -> str:
        """
        Format explicit reasoning rules for alternative recommendations.

        These rules emphasize:
        - Meaningful differentiation
        - Layer validation
        - Hallucination prevention
        - Weather compatibility
        """
        return """================================================================================
EXPLICIT RULES FOR ALTERNATIVE SUGGESTIONS:
================================================================================

RULE 0: STRICT INVENTORY COMPLIANCE
   ✓ You may ONLY use items provided in the inventory above
   ✓ You MUST select from Layer 1, Layer 2, and/or Layer 3 items
   ✗ You MUST NOT invent, assume, or mention any items not in the inventory
   ✗ You MUST NOT output "PECAS_EM_FALTA", "Missing Items", or item gaps
   ✗ Do NOT use items marked as "Dirty"

RULE 1: LAYER VALIDATION (CRITICAL)
   ✓ Check each item's LAYER assignment in the inventory above
   ✓ Base Layer (Layer 1): ONLY t-shirts, tops, base garments
   ✓ Insulation Layer (Layer 2): ONLY sweaters, cardigans, trousers, pants
   ✓ Outer Layer (Layer 3): ONLY jackets, coats, shoes, accessories
   ✗ A jacket can NEVER appear in Base Layer or Insulation Layer
   ✗ Shoes can NEVER appear in Base Layer or Insulation Layer
   ✗ T-shirts can NEVER appear in Outer Layer

RULE 2: MEANINGFUL DIFFERENTIATION:
   ✓ Each alternative must be noticeably different from the original
   ✓ Alternatives should have distinct vibes or purposes
   ✓ Variety makes alternatives actually useful
   ✗ Do NOT suggest minor variations (same outfit + one swapped piece)

RULE 3: WEATHER COMPATIBILITY:
   ✓ Every alternative must be suitable for today's weather
   ✓ Cannot suggest alternatives that conflict with forecast
   ✗ Do NOT suggest weather-inappropriate outfits

RULE 4: UNIQUE STYLE DIRECTIONS:
   Consider these approaches for variety:
   - Alternative 1: Different occasion (casual vs. polished, sporty vs. formal, etc.)
   - Alternative 2: Different color palette or mood
   - Alternative 3: Different layer strategy (minimal vs. maximum, etc.)
   ✗ Do NOT suggest copies of the same base outfit

RULE 5: COHERENCE:
   ✓ Each alternative must be internally consistent
   ✓ Colors and style must work together within each alternative
   ✗ Do NOT create random or clashing combinations

RULE 6: USAGE FREQUENCY:
   ✓ Consider spreading usage across different items
   ✓ Use less-worn items in alternatives
   ✗ Do NOT suggest identical heavy-use patterns in all alternatives

RULE 7: CLEAN ITEMS ONLY:
   ✓ Check STATUS field - only select items marked "Clean"
   ✗ Do NOT recommend dirty items

RULE 8: PRACTICALITY:
   ✓ All suggestions must be genuinely wearable
   ✓ Consider the original outfit's context/occasion
   ✓ Alternatives should be real-world useful
   ✗ Do NOT suggest impractical or experimental outfits

================================================================================
"""

    def _format_current_outfit_section(self) -> str:
        """Format context about the current outfit being replaced."""
        return """================================================================================
CONTEXT: ORIGINAL OUTFIT
================================================================================

You are creating alternatives to an original outfit recommendation.
Each alternative should be materially different while remaining weather-appropriate
and realistic. Use this context to understand what NOT to repeat.

================================================================================
"""

    # ========================================================================
    # RESPONSE FORMAT SPECIFICATIONS (STRICT)
    # ========================================================================

    def _format_response_format_daily(self) -> str:
        """
        Format the response specification for daily recommendations.

        STRICT FORMAT that prevents hallucinations and layer misclassification.
        """
        return """================================================================================
REQUIRED RESPONSE FORMAT (STRICT):
================================================================================

You MUST provide your response in EXACTLY this format.
Do not deviate from this structure. Do not invent items. Do not mention missing items.

Base Layer:
[item name] [ID: item_id] OR None

Insulation Layer:
[item name] [ID: item_id] OR None

Outer Layer:
[item name] [ID: item_id] OR None

Shoes:
[item name] [ID: item_id] OR None

Accessories:
[item name] [ID: item_id] OR None (multiple items comma-separated, or None)

Reasoning:
[Short explanation only. Focus on: weather match, layer fit, color coordination, usage considerations. Do NOT mention missing items or inventory gaps. Keep to 3-5 sentences.]

================================================================================

BEGIN YOUR RECOMMENDATION:
"""

    def _format_response_format_travel(self, num_days: int) -> str:
        """
        Format the response specification for travel recommendations.

        STRICT FORMAT that prevents hallucinations and layer misclassification.
        """
        response = """================================================================================
REQUIRED RESPONSE FORMAT (STRICT):
================================================================================

You MUST provide your response in EXACTLY this structure.
Do not deviate from this format. Do not invent items. Do not mention missing items.

"""
        for day in range(1, num_days + 1):
            response += f"""Day {day}:
Base Layer: [item name and ID, or "None"]
Insulation Layer: [item name and ID, or "None"]
Outer Layer: [item name and ID, or "None"]
Shoes: [item name and ID]
Accessories: [items or "None"]

"""

        response += """Packing List Summary:
[List all unique items to pack with their IDs. Format: Item Name [ID: xxx]]

Mixing & Matching Strategy:
[Explain how selected items create multiple outfit combinations despite limited packing. Reference which items appear in which day's outfits.]

Reasoning:
[Provide overall rationale covering: weather adaptation across days, versatility strategy, how you stayed within luggage constraints, how each day's outfit differs. Do NOT mention missing items or inventory gaps. Keep to clear, concise explanation.]

================================================================================

BEGIN YOUR TRAVEL PLAN:
"""
        return response

    def _format_response_format_alternative(self) -> str:
        """
        Format the response specification for alternative recommendations.

        STRICT FORMAT that prevents hallucinations and layer misclassification.
        """
        return """================================================================================
REQUIRED RESPONSE FORMAT (STRICT):
================================================================================

Provide EXACTLY 3 alternatives in this format.
Do not deviate from this structure. Do not invent items. Do not mention missing items.

ALTERNATIVE 1:
Base Layer: [item name and ID, or "None"]
Insulation Layer: [item name and ID, or "None"]
Outer Layer: [item name and ID, or "None"]
Shoes: [item name and ID]
Accessories: [items or "None"]
Style Direction: [Brief description of this alternative's vibe/occasion]
Reason: [Why this is a good alternative and how it differs from the original]

ALTERNATIVE 2:
Base Layer: [item name and ID, or "None"]
Insulation Layer: [item name and ID, or "None"]
Outer Layer: [item name and ID, or "None"]
Shoes: [item name and ID]
Accessories: [items or "None"]
Style Direction: [Brief description of this alternative's vibe/occasion]
Reason: [Why this is a good alternative and how it differs from the original]

ALTERNATIVE 3:
Base Layer: [item name and ID, or "None"]
Insulation Layer: [item name and ID, or "None"]
Outer Layer: [item name and ID, or "None"]
Shoes: [item name and ID]
Accessories: [items or "None"]
Style Direction: [Brief description of this alternative's vibe/occasion]
Reason: [Why this is a good alternative and how it differs from the original]

================================================================================

BEGIN YOUR ALTERNATIVES:
"""

    # ========================================================================
    # LEGACY PROMPT BUILDERS (Deprecated - for backward compatibility)
    # ========================================================================

    def build_daily_outfit_prompt(
        self,
        weather: AIReadyWeather,
        wardrobe_by_layer: Dict[int, List[AIReadyItem]],
        usage_metrics: Dict[str, Any],
        constraints: Dict[str, Any],
    ) -> str:
        """
        Build a daily outfit prompt (legacy method).

        Deprecated: Use build_daily_prompt_from_context() instead.
        """
        prompt_parts = []

        # System message
        prompt_parts.append(self._build_system_message_daily())

        # Weather
        if weather:
            prompt_parts.append(self._format_weather_section(weather))

        # Wardrobe
        prompt_parts.append(self._format_wardrobe_section(wardrobe_by_layer))

        # Usage frequency
        prompt_parts.append(self._format_usage_frequency_section(wardrobe_by_layer))

        # Constraints
        prompt_parts.append(self._format_constraints_section(constraints))

        # Rules
        prompt_parts.append(self._format_rules_section_daily())

        # Response format
        prompt_parts.append(self._format_response_format_daily())

        return "\n".join(prompt_parts)

    def build_travel_outfit_prompt(
        self,
        forecast: List[AIReadyWeather],
        wardrobe_by_layer: Dict[int, List[AIReadyItem]],
        num_days: int,
        luggage_limit: int,
        constraints: Dict[str, Any],
    ) -> str:
        """
        Build a travel outfit prompt (legacy method).

        Deprecated: Use build_travel_prompt_from_context() instead.
        """
        prompt_parts = []

        # System message
        prompt_parts.append(self._build_system_message_travel(num_days, luggage_limit))

        # Forecast
        prompt_parts.append(self._format_weather_forecast_section(forecast, num_days))

        # Wardrobe
        prompt_parts.append(self._format_wardrobe_section(wardrobe_by_layer))

        # Usage frequency
        prompt_parts.append(self._format_usage_frequency_section(wardrobe_by_layer))

        # Constraints
        prompt_parts.append(self._format_constraints_section(constraints))

        # Rules
        prompt_parts.append(self._format_rules_section_travel(num_days, luggage_limit))

        # Response format
        prompt_parts.append(self._format_response_format_travel(num_days))

        return "\n".join(prompt_parts)

    def build_alternative_outfit_prompt(
        self,
        weather: AIReadyWeather,
        wardrobe_by_layer: Dict[int, List[AIReadyItem]],
        constraints: Dict[str, Any],
    ) -> str:
        """
        Build an alternative outfit prompt (legacy method).

        Deprecated: Use build_alternative_prompt_from_context() instead.
        """
        prompt_parts = []

        # System message
        prompt_parts.append(self._build_system_message_alternative())

        # Weather
        if weather:
            prompt_parts.append(self._format_weather_section(weather))

        # Wardrobe
        prompt_parts.append(self._format_wardrobe_section(wardrobe_by_layer))

        # Usage frequency
        prompt_parts.append(self._format_usage_frequency_section(wardrobe_by_layer))

        # Constraints
        prompt_parts.append(self._format_constraints_section(constraints))

        # Rules
        prompt_parts.append(self._format_rules_section_alternative())

        # Current outfit context
        prompt_parts.append(self._format_current_outfit_section())

        # Response format
        prompt_parts.append(self._format_response_format_alternative())

        return "\n".join(prompt_parts)

    # ========================================================================
    # UTILITY METHODS FOR FORMATTING
    # ========================================================================

    def _format_wardrobe_legacy(
        self, wardrobe_by_layer: Dict[int, List[AIReadyItem]]
    ) -> str:
        """Format wardrobe (legacy format)."""
        section = "WARDROBE BY LAYER:\n"
        for layer_num in sorted(wardrobe_by_layer.keys()):
            layer_name = self.layer_names.get(layer_num, f"Layer {layer_num}")
            items = wardrobe_by_layer[layer_num]
            section += f"\n{layer_name}:\n"
            for item in items:
                section += f"  • {item.name} [ID: {item.id}] - {item.type}\n"
        return section

    def _format_weather_legacy(self, weather: AIReadyWeather) -> str:
        """Format weather (legacy format)."""
        return f"""WEATHER:
Temperature: {weather.temperature}°C
Condition: {weather.condition}
Humidity: {weather.humidity}%
Wind: {weather.wind_speed} km/h
"""

    def _format_forecast_legacy(
        self, forecast: List[AIReadyWeather], num_days: int
    ) -> str:
        """Format forecast (legacy format)."""
        section = f"FORECAST ({num_days} DAYS):\n"
        for i, day_weather in enumerate(forecast[:num_days], 1):
            if hasattr(day_weather, "temperature"):
                section += (
                    f"Day {i}: {day_weather.temperature}°C, {day_weather.condition}\n"
                )
            else:
                section += f"Day {i}: {day_weather.temperature_min}°C to {day_weather.temperature_max}°C, {day_weather.condition}\n"
        return section

    def _format_preferences_legacy(self, constraints: Dict[str, Any]) -> str:
        """Format preferences (legacy format)."""
        section = "USER PREFERENCES:\n"
        if constraints:
            for key, value in constraints.items():
                section += f"  • {key}: {value}\n"
        else:
            section += "  • No constraints specified\n"
        return section


class PromptServiceError(Exception):
    """Exception for prompt service errors."""

    pass
