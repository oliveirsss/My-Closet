"""
Phase 3 - Prompt Engineering Examples

This script demonstrates how the PromptService generates high-quality prompts
from Phase 2 AI-ready context objects.

Three examples are provided:
1. Daily Outfit Recommendation Prompt
2. Travel Outfit Recommendation Prompt
3. Alternative Outfit Recommendation Prompt

Each example shows:
- How to construct an AIReadyContext
- How the PromptService converts it to a final VLM prompt
- What the generated prompt looks like

To run this script:
    python examples/phase3_prompt_examples.py
"""

from datetime import datetime, timedelta
from services.data_preparation_service import AIReadyContext, AIReadyItem, AIReadyWeather
from services.prompt_service import PromptService


def create_sample_wardrobe():
    """Create sample wardrobe items organized by layer."""

    # BASE LAYER ITEMS (touching skin)
    base_items = [
        AIReadyItem({
            "id": "base_001",
            "name": "Cotton T-Shirt (White)",
            "type": "T-Shirt",
            "brand": "Uniqlo",
            "color": "White",
            "size": "M",
            "layer": 1,
            "materials": ["100% Cotton"],
            "weight": 0.15,
            "temp_min": 10,
            "temp_max": 30,
            "waterproof": False,
            "windproof": False,
            "status": "clean",
            "favorite": True,
            "seasons": ["Spring", "Summer", "Fall"],
        }, usage_metrics={
            "usage_frequency_last_7_days": 2,
            "usage_frequency_last_30_days": 8,
            "last_used_days_ago": 1,
            "total_wears": 25,
            "is_overused": False
        }),

        AIReadyItem({
            "id": "base_002",
            "name": "Thermal Base Layer (Black)",
            "type": "Long Sleeve Base",
            "brand": "Patagonia",
            "color": "Black",
            "size": "M",
            "layer": 1,
            "materials": ["Merino Wool Blend"],
            "weight": 0.25,
            "temp_min": -5,
            "temp_max": 15,
            "waterproof": False,
            "windproof": False,
            "status": "clean",
            "favorite": False,
            "seasons": ["Fall", "Winter"],
        }, usage_metrics={
            "usage_frequency_last_7_days": 0,
            "usage_frequency_last_30_days": 3,
            "last_used_days_ago": 14,
            "total_wears": 12,
            "is_overused": False
        }),
    ]

    # INSULATION LAYER ITEMS (for warmth)
    insulation_items = [
        AIReadyItem({
            "id": "mid_001",
            "name": "Fleece Sweater (Navy)",
            "type": "Sweater",
            "brand": "Arc'teryx",
            "color": "Navy Blue",
            "size": "M",
            "layer": 2,
            "materials": ["Polyester Fleece"],
            "weight": 0.4,
            "temp_min": 0,
            "temp_max": 20,
            "waterproof": False,
            "windproof": False,
            "status": "clean",
            "favorite": False,
            "seasons": ["Fall", "Winter", "Spring"],
        }, usage_metrics={
            "usage_frequency_last_7_days": 1,
            "usage_frequency_last_30_days": 5,
            "last_used_days_ago": 3,
            "total_wears": 18,
            "is_overused": False
        }),

        AIReadyItem({
            "id": "mid_002",
            "name": "Wool Cardigan (Gray)",
            "type": "Cardigan",
            "brand": "Banana Republic",
            "color": "Gray",
            "size": "M",
            "layer": 2,
            "materials": ["Merino Wool"],
            "weight": 0.35,
            "temp_min": 5,
            "temp_max": 25,
            "waterproof": False,
            "windproof": False,
            "status": "clean",
            "favorite": True,
            "seasons": ["Fall", "Winter", "Spring"],
        }, usage_metrics={
            "usage_frequency_last_7_days": 3,
            "usage_frequency_last_30_days": 10,
            "last_used_days_ago": 0,
            "total_wears": 35,
            "is_overused": True
        }),
    ]

    # OUTER LAYER ITEMS (protection/shell)
    outer_items = [
        AIReadyItem({
            "id": "outer_001",
            "name": "Waterproof Rain Jacket (Teal)",
            "type": "Jacket",
            "brand": "The North Face",
            "color": "Teal",
            "size": "M",
            "layer": 3,
            "materials": ["Gore-Tex"],
            "weight": 0.55,
            "temp_min": 5,
            "temp_max": 25,
            "waterproof": True,
            "windproof": True,
            "status": "clean",
            "favorite": False,
            "seasons": ["Spring", "Fall", "Winter"],
        }, usage_metrics={
            "usage_frequency_last_7_days": 0,
            "usage_frequency_last_30_days": 2,
            "last_used_days_ago": 7,
            "total_wears": 8,
            "is_overused": False
        }),

        AIReadyItem({
            "id": "outer_002",
            "name": "Winter Puffer Coat (Black)",
            "type": "Coat",
            "brand": "Canada Goose",
            "color": "Black",
            "size": "M",
            "layer": 3,
            "materials": ["Down", "Nylon"],
            "weight": 0.9,
            "temp_min": -20,
            "temp_max": 5,
            "waterproof": True,
            "windproof": True,
            "status": "clean",
            "favorite": False,
            "seasons": ["Winter"],
        }, usage_metrics={
            "usage_frequency_last_7_days": 0,
            "usage_frequency_last_30_days": 0,
            "last_used_days_ago": 45,
            "total_wears": 15,
            "is_overused": False
        }),
    ]

    # ACCESSORIES (finishing touches)
    accessories_items = [
        AIReadyItem({
            "id": "acc_001",
            "name": "Canvas Sneakers (White)",
            "type": "Shoes",
            "brand": "Vans",
            "color": "White",
            "size": "M",
            "layer": 4,
            "materials": ["Canvas", "Rubber"],
            "weight": 0.3,
            "temp_min": 5,
            "temp_max": 30,
            "waterproof": False,
            "windproof": False,
            "status": "clean",
            "favorite": False,
            "seasons": ["Spring", "Summer", "Fall"],
        }, usage_metrics={
            "usage_frequency_last_7_days": 4,
            "usage_frequency_last_30_days": 15,
            "last_used_days_ago": 0,
            "total_wears": 60,
            "is_overused": True
        }),

        AIReadyItem({
            "id": "acc_002",
            "name": "Hiking Boots (Brown)",
            "type": "Shoes",
            "brand": "Merrell",
            "color": "Brown",
            "size": "M",
            "layer": 4,
            "materials": ["Leather", "Gore-Tex"],
            "weight": 0.6,
            "temp_min": -5,
            "temp_max": 25,
            "waterproof": True,
            "windproof": False,
            "status": "clean",
            "favorite": False,
            "seasons": ["Spring", "Fall", "Winter"],
        }, usage_metrics={
            "usage_frequency_last_7_days": 0,
            "usage_frequency_last_30_days": 2,
            "last_used_days_ago": 21,
            "total_wears": 12,
            "is_overused": False
        }),

        AIReadyItem({
            "id": "acc_003",
            "name": "Wool Beanie (Gray)",
            "type": "Hat",
            "brand": "Patagonia",
            "color": "Gray",
            "size": "One Size",
            "layer": 4,
            "materials": ["Wool"],
            "weight": 0.1,
            "temp_min": -10,
            "temp_max": 15,
            "waterproof": False,
            "windproof": False,
            "status": "clean",
            "favorite": True,
            "seasons": ["Fall", "Winter", "Spring"],
        }, usage_metrics={
            "usage_frequency_last_7_days": 1,
            "usage_frequency_last_30_days": 3,
            "last_used_days_ago": 5,
            "total_wears": 22,
            "is_overused": False
        }),
    ]

    return {
        1: base_items,
        2: insulation_items,
        3: outer_items,
        4: accessories_items,
    }


def example_1_daily_recommendation():
    """
    Example 1: Daily Outfit Recommendation Prompt

    Scenario: Cool, rainy morning - need a weather-appropriate outfit
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: DAILY OUTFIT RECOMMENDATION PROMPT")
    print("=" * 80)
    print("\nScenario: Cool, rainy morning in fall")
    print("Goal: Generate a prompt for the VLM to suggest today's outfit\n")

    # Create weather context
    weather = AIReadyWeather({
        "temperature": 12,
        "temperature_min": 10,
        "temperature_max": 14,
        "condition": "rainy",
        "humidity": 85,
        "wind_speed": 15,
        "feels_like": 8,
        "description": "Light rain expected throughout the day"
    }, is_forecast=False)

    # Get sample wardrobe
    wardrobe_by_layer = create_sample_wardrobe()

    # Create user constraints
    user_constraints = {
        "style": "casual",
        "occasion": "working from home",
        "comfort_level": "cozy",
        "color_preferences": ["neutral", "warm tones"],
        "avoid_colors": ["bright neon"],
    }

    # Create AI-ready context
    context = AIReadyContext(
        user_id="user_123",
        recommendation_type="daily",
        weather=weather,
        wardrobe_by_layer=wardrobe_by_layer,
        user_constraints=user_constraints,
        metadata={"occasion": "work_from_home"}
    )

    # Generate prompt
    prompt_service = PromptService()
    prompt = prompt_service.build_daily_prompt_from_context(context)

    print("Generated Daily Prompt:\n")
    print(prompt)
    print("\n" + "-" * 80)


def example_2_travel_recommendation():
    """
    Example 2: Travel Outfit Recommendation Prompt

    Scenario: 4-day fall trip with varying weather
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: TRAVEL OUTFIT RECOMMENDATION PROMPT")
    print("=" * 80)
    print("\nScenario: 4-day fall trip with varying weather")
    print("Goal: Generate a prompt for packing smart outfits for multiple days\n")

    # Create multi-day weather forecast
    weather_forecast = [
        AIReadyWeather({
            "date": "2024-11-15",
            "temperature_min": 8,
            "temperature_max": 15,
            "condition": "rainy",
            "precipitation_probability": 75,
            "humidity": 80,
            "wind_speed": 12,
        }, is_forecast=True),

        AIReadyWeather({
            "date": "2024-11-16",
            "temperature_min": 6,
            "temperature_max": 12,
            "condition": "cloudy",
            "precipitation_probability": 40,
            "humidity": 65,
            "wind_speed": 8,
        }, is_forecast=True),

        AIReadyWeather({
            "date": "2024-11-17",
            "temperature_min": 10,
            "temperature_max": 16,
            "condition": "sunny",
            "precipitation_probability": 10,
            "humidity": 55,
            "wind_speed": 5,
        }, is_forecast=True),

        AIReadyWeather({
            "date": "2024-11-18",
            "temperature_min": 5,
            "temperature_max": 11,
            "condition": "rainy",
            "precipitation_probability": 80,
            "humidity": 85,
            "wind_speed": 14,
        }, is_forecast=True),
    ]

    # Get sample wardrobe
    wardrobe_by_layer = create_sample_wardrobe()

    # Create user constraints
    user_constraints = {
        "style": "casual_smart",
        "occasion": "city exploration",
        "comfort_level": "practical",
        "color_preferences": ["earth tones", "navy", "black"],
    }

    # Create travel context
    context = AIReadyContext(
        user_id="user_123",
        recommendation_type="travel",
        weather=weather_forecast,
        wardrobe_by_layer=wardrobe_by_layer,
        user_constraints=user_constraints,
        metadata={
            "destination": "Portland, OR",
            "num_days": 4,
            "luggage_limit": 10,
            "trip_type": "city_exploration"
        }
    )

    # Generate prompt
    prompt_service = PromptService()
    prompt = prompt_service.build_travel_prompt_from_context(context)

    print("Generated Travel Prompt:\n")
    print(prompt)
    print("\n" + "-" * 80)


def example_3_alternative_recommendation():
    """
    Example 3: Alternative Outfit Recommendation Prompt

    Scenario: User wants different outfit ideas for today's weather
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: ALTERNATIVE OUTFIT RECOMMENDATION PROMPT")
    print("=" * 80)
    print("\nScenario: User wants alternative outfits for cool morning")
    print("Goal: Generate prompt for suggesting 3 different outfit options\n")

    # Create weather context
    weather = AIReadyWeather({
        "temperature": 14,
        "temperature_min": 12,
        "temperature_max": 18,
        "condition": "cloudy",
        "humidity": 60,
        "wind_speed": 8,
        "feels_like": 12,
        "description": "Cool but no rain expected"
    }, is_forecast=False)

    # Get sample wardrobe
    wardrobe_by_layer = create_sample_wardrobe()

    # Current outfit selected by the user
    current_outfit_ids = ["base_001", "mid_002", "acc_001"]

    # Create user constraints
    user_constraints = {
        "style": "casual",
        "occasion": "errand day",
        "comfort_level": "comfortable",
        "color_preferences": ["neutral", "blue"],
    }

    # Create alternative context
    context = AIReadyContext(
        user_id="user_123",
        recommendation_type="alternative",
        weather=weather,
        wardrobe_by_layer=wardrobe_by_layer,
        user_constraints=user_constraints,
        metadata={
            "current_outfit_ids": current_outfit_ids,
            "num_alternatives": 3
        }
    )

    # Generate prompt
    prompt_service = PromptService()
    prompt = prompt_service.build_alternative_prompt_from_context(
        context,
        current_outfit_item_ids=current_outfit_ids
    )

    print("Generated Alternative Prompt:\n")
    print(prompt)
    print("\n" + "-" * 80)


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "PHASE 3 - PROMPT ENGINEERING EXAMPLES".center(78) + "║")
    print("║" + "AI Outfit Recommendation System - Prompt Generation".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")

    # Run all three examples
    example_1_daily_recommendation()
    example_2_travel_recommendation()
    example_3_alternative_recommendation()

    # Summary
    print("\n" + "=" * 80)
    print("EXAMPLES COMPLETE")
    print("=" * 80)
    print("""
WHAT YOU JUST SAW:

1. Example 1 (Daily): Shows how a single-day outfit recommendation prompt
   guides the VLM to suggest a complete outfit considering weather (rainy),
   temperature, user preferences, and usage frequency.

2. Example 2 (Travel): Shows how a multi-day travel prompt guides the VLM to
   pack smartly for 4 days with varying weather, respecting luggage limits
   and creating versatile outfit combinations.

3. Example 3 (Alternative): Shows how an alternative suggestion prompt guides
   the VLM to suggest 3 meaningfully different outfits for the same day/weather,
   avoiding repeating the current outfit.

KEY FEATURES OF PHASE 3 PROMPTS:

✓ Explicit: Every instruction is crystal clear
✓ Deterministic: Same context produces same prompt structure
✓ Non-generative: VLM only selects from provided items (no hallucinations)
✓ Reason-aware: VLM must explain its reasoning for selections
✓ Layer-aware: Respects realistic clothing layering
✓ Usage-aware: Considers item usage frequency
✓ Preference-aware: Incorporates user constraints
✓ Parseable: Fixed response format for Phase 5 parsing

NEXT PHASE (Phase 4):

These prompts are ready to be sent to a real VLM (LLaVA) with images attached.
The VLM will process the wardrobe images and generate structured recommendations
based on the explicit guidance in these prompts.

═" * 80)


if __name__ == "__main__":
    main()
