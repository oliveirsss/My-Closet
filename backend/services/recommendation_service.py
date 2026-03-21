"""
Recommendation Service

Orchestrates the complete outfit recommendation pipeline.
Coordinates between:
- Data preparation service (prepares AI-ready context)
- Wardrobe service (fallback for direct item fetching)
- Weather service (fallback for weather data)
- Usage service (fallback for usage metrics)
- Prompt service (builds VLM prompts from context)
- VLM service (generates recommendations)
- Response parser (normalizes output)

Also provides fallback to rule-based recommendations if VLM fails.

PHASE 2 UPDATE:
Now uses DataPreparationService to build AI-ready context before VLM processing.
Flow: route → recommend_* → prepare_*_context → wardrobe/weather/usage services
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from services.data_preparation_service import DataPreparationService
from services.prompt_service import PromptService
from services.response_parser import ResponseParser
from services.usage_service import UsageService
from services.vlm_service import VLMServiceInterface
from services.wardrobe_service import WardrobeService
from services.weather_service import WeatherService


class RecommendationService:
    """
    Main orchestrator for the outfit recommendation pipeline.

    Coordinates all services to provide outfit recommendations using the VLM,
    with fallback to rule-based recommendations if needed.

    Phase 2 Enhancement:
    - Now uses DataPreparationService to build AI-ready context
    - Context is prepared before VLM processing
    - Ensures all data is properly enriched and filtered
    """

    def __init__(
        self,
        vlm_service: VLMServiceInterface,
        wardrobe_service: Optional[WardrobeService] = None,
        weather_service: Optional[WeatherService] = None,
        usage_service: Optional[UsageService] = None,
        prompt_service: Optional[PromptService] = None,
        response_parser: Optional[ResponseParser] = None,
    ):
        """
        Initialize the recommendation service.

        Args:
            vlm_service: VLM service implementation (required)
            wardrobe_service: Wardrobe service (created if not provided)
            weather_service: Weather service (created if not provided)
            usage_service: Usage service (created if not provided)
            prompt_service: Prompt service (created if not provided)
            response_parser: Response parser (created if not provided)
        """
        self.vlm_service = vlm_service
        self.wardrobe_service = wardrobe_service or WardrobeService()
        self.weather_service = weather_service or WeatherService()
        self.usage_service = usage_service or UsageService()
        self.prompt_service = prompt_service or PromptService()
        self.response_parser = response_parser or ResponseParser()

        # Phase 2: Data preparation service
        self.data_preparation_service = DataPreparationService(
            usage_service=self.usage_service,
            weather_service=self.weather_service,
        )

    async def recommend_daily_outfit(
        self,
        user_id: str,
        temperature: float,
        weather_condition: str,
        humidity: Optional[float] = None,
        wind_speed: Optional[float] = None,
        occasion: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
        exclude_items: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a daily outfit recommendation.

        Phase 2 Flow:
        1. Prepare AI-ready context using DataPreparationService
        2. Context includes enriched wardrobe, weather, and usage data
        3. Pass context to VLM or fallback logic
        4. Return structured recommendation

        Args:
            user_id: User's ID
            temperature: Current temperature in Celsius
            weather_condition: Weather condition (sunny, rainy, snowy, etc)
            humidity: Optional humidity percentage
            wind_speed: Optional wind speed in km/h
            occasion: Optional occasion (work, casual, sports, etc)
            preferences: Optional user style preferences
            exclude_items: Optional list of item IDs to exclude

        Returns:
            Dictionary with recommended outfit and metadata
        """
        try:
            # Phase 2: Prepare AI-ready context
            ai_context = await self.data_preparation_service.prepare_daily_context(
                user_id=user_id,
                temperature=temperature,
                weather_condition=weather_condition,
                humidity=humidity,
                wind_speed=wind_speed,
                occasion=occasion,
                user_preferences=preferences,
                exclude_items=exclude_items,
            )

            # Check if we have any items to work with
            if not ai_context.get_all_items():
                return self._create_error_response(
                    "No suitable wardrobe items available for recommendation"
                )

            # For now (Phase 2), we don't call VLM yet
            # Just return the prepared context as a response for Phase 3 integration
            # When Phase 3 is ready, VLM call will go here

            # Fallback: Return best option from available items
            return await self._fallback_daily_recommendation_from_context(ai_context)

        except Exception as e:
            print(f"Error in daily recommendation: {e}")
            return self._create_error_response(f"Daily recommendation failed: {str(e)}")

    async def recommend_travel_outfits(
        self,
        user_id: str,
        destination: str,
        start_date: datetime,
        end_date: datetime,
        weather_forecast: Optional[List[Dict[str, Any]]] = None,
        luggage_limit: int = 10,
        preferences: Optional[Dict[str, Any]] = None,
        exclude_items: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate travel outfit recommendations.

        Phase 2 Flow:
        1. Prepare AI-ready context for travel using DataPreparationService
        2. Context includes weather forecast, luggage constraints, versatile items
        3. Pass context to VLM or fallback logic
        4. Return packing list and daily outfit suggestions

        Args:
            user_id: User's ID
            destination: Travel destination
            start_date: Start date of trip
            end_date: End date of trip
            weather_forecast: Optional weather forecast (will be fetched if not provided)
            luggage_limit: Maximum items to pack
            preferences: Optional user preferences
            exclude_items: Optional item IDs to exclude

        Returns:
            Dictionary with recommended outfits and packing list
        """
        try:
            # Phase 2: Prepare AI-ready context for travel
            ai_context = await self.data_preparation_service.prepare_travel_context(
                user_id=user_id,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                luggage_limit=luggage_limit,
                user_preferences=preferences,
                exclude_items=exclude_items,
            )

            # Check if we have items
            if not ai_context.get_all_items():
                return self._create_error_response(
                    "No suitable wardrobe items available for travel planning"
                )

            # For now (Phase 2), we don't call VLM yet
            # Just return the prepared context as a response for Phase 3 integration

            # Fallback: Return packing list from available items
            return await self._fallback_travel_recommendation_from_context(ai_context)

        except Exception as e:
            print(f"Error in travel recommendation: {e}")
            return self._create_error_response(f"Travel recommendation failed: {str(e)}")

    async def recommend_alternatives(
        self,
        user_id: str,
        current_outfit_item_ids: List[str],
        temperature: float,
        weather_condition: str,
        humidity: Optional[float] = None,
        wind_speed: Optional[float] = None,
        num_alternatives: int = 3,
        preferences: Optional[Dict[str, Any]] = None,
        exclude_items: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate alternative outfit suggestions.

        Phase 2 Flow:
        1. Prepare AI-ready context with alternatives focus
        2. Deprioritize items from current outfit
        3. Pass context to VLM or fallback logic
        4. Return alternative outfit suggestions

        Args:
            user_id: User's ID
            current_outfit_item_ids: Item IDs in current outfit
            temperature: Current temperature
            weather_condition: Weather condition
            humidity: Optional humidity
            wind_speed: Optional wind speed
            num_alternatives: Number of alternatives to suggest
            preferences: Optional user preferences
            exclude_items: Optional item IDs to exclude

        Returns:
            Dictionary with alternative outfit suggestions
        """
        try:
            # Phase 2: Prepare AI-ready context for alternatives
            ai_context = await self.data_preparation_service.prepare_alternative_context(
                user_id=user_id,
                current_outfit_items=current_outfit_item_ids,
                temperature=temperature,
                weather_condition=weather_condition,
                humidity=humidity,
                wind_speed=wind_speed,
                num_alternatives=num_alternatives,
                user_preferences=preferences,
                exclude_items=exclude_items,
            )

            # Check if we have alternatives
            if not ai_context.get_all_items():
                return self._create_error_response(
                    "No alternative wardrobe items available"
                )

            # For now (Phase 2), we don't call VLM yet
            # Just return the prepared context as a response for Phase 3 integration

            # Fallback: Return alternatives from available items
            return await self._fallback_alternative_recommendation_from_context(
                ai_context, num_alternatives
            )

        except Exception as e:
            print(f"Error in alternative recommendation: {e}")
            return self._create_error_response(
                f"Alternative recommendation failed: {str(e)}"
            )

    # ========================================================================
    # FALLBACK METHODS (Rule-based recommendations when VLM not available)
    # ========================================================================

    async def _fallback_daily_recommendation_from_context(self, ai_context):
        """
        Fallback recommendation using AI-ready context.

        Selects best items from each layer using available data.
        """
        try:
            outfit_items = []

            # Select one item from each available layer
            for layer in sorted(ai_context.wardrobe_by_layer.keys()):
                items = ai_context.wardrobe_by_layer[layer]
                if items:
                    # Select item: prefer favorites, then least used
                    selected = min(
                        items,
                        key=lambda x: (
                            not x.favorite,
                            x.usage_metrics.get("usage_frequency_last_7_days", 0),
                        ),
                    )
                    outfit_items.append(selected)

            return {
                "success": True,
                "outfit": {
                    "items": [item.to_dict() for item in outfit_items],
                    "reasoning": "Fallback rule-based selection from available items",
                },
                "model_used": "rule_based",
                "context_used": "ai_ready_context",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return self._create_error_response(f"Fallback recommendation failed: {e}")

    async def _fallback_travel_recommendation_from_context(self, ai_context):
        """
        Fallback travel recommendation using AI-ready context.

        Returns all available items as packing list.
        """
        try:
            all_items = ai_context.get_all_items()

            return {
                "success": True,
                "travel_plan": {
                    "packing_list": [item.to_dict() for item in all_items],
                    "packing_notes": "Rule-based packing: all suitable items selected",
                },
                "model_used": "rule_based",
                "context_used": "ai_ready_context",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return self._create_error_response(f"Travel fallback failed: {e}")

    async def _fallback_alternative_recommendation_from_context(
        self, ai_context, num_alternatives
    ):
        """
        Fallback alternative recommendations using AI-ready context.

        Selects diverse items from different layers.
        """
        try:
            alternatives = []
            all_items = ai_context.get_all_items()

            # Create simple alternatives by grouping items differently
            for i in range(min(num_alternatives, len(all_items))):
                outfit = [all_items[j] for j in range(i, min(i + 3, len(all_items)))]
                if outfit:
                    alternatives.append(
                        {
                            "items": [item.to_dict() for item in outfit],
                            "reasoning": f"Alternative {i + 1}: different item combination",
                        }
                    )

            return {
                "success": True,
                "alternatives": alternatives,
                "model_used": "rule_based",
                "context_used": "ai_ready_context",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return self._create_error_response(f"Alternative fallback failed: {e}")

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Create a standardized error response.

        Args:
            error_message: Error description

        Returns:
            Dictionary with error info
        """
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
        }


class RecommendationServiceError(Exception):
    """Exception raised by RecommendationService."""

    pass
