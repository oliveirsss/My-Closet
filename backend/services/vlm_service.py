"""
VLM (Visual Language Model) Service Interface.

This module defines the abstract interface for Visual Language Model integration.
It allows different VLM implementations (LLaVA, GPT-4V, Claude Vision, etc.) to be
swapped without changing the recommendation pipeline.

The interface is designed to be agnostic to the specific VLM used, focusing on
the contract: send wardrobe images and context, receive outfit recommendations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class VLMProviderEnum(str, Enum):
    """Enum of supported VLM providers."""

    LLAVA = "llava"
    GPT4V = "gpt4v"
    CLAUDE_VISION = "claude_vision"
    MOCK = "mock"  # For testing/development


@dataclass
class VLMResponse:
    """
    Standardized response from a VLM call.

    Attributes:
        success: Whether the VLM call was successful
        outfit_items: List of item IDs recommended for the outfit
        reasoning: Text explanation from the VLM about the recommendation
        confidence_score: Float 0-1 indicating confidence in the recommendation
        metadata: Additional metadata from the VLM (usage stats, etc.)
        error: Error message if success=False
    """

    success: bool
    outfit_items: List[str] = None
    reasoning: str = ""
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.outfit_items is None:
            self.outfit_items = []


class VLMServiceInterface(ABC):
    """
    Abstract base class for Visual Language Model services.

    All VLM implementations must inherit from this class and implement
    the required methods. This ensures consistency and allows for easy
    swapping of different VLM providers.

    Key responsibilities:
    - Accept wardrobe items with images and metadata
    - Accept weather context and user preferences
    - Call the VLM with appropriate prompts
    - Parse and normalize VLM responses
    - Handle errors gracefully with detailed messages
    """

    def __init__(
        self, provider: VLMProviderEnum, config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the VLM service.

        Args:
            provider: Which VLM provider this service uses
            config: Configuration dictionary specific to the provider
                   (API keys, model names, temperature, etc.)
        """
        self.provider = provider
        self.config = config or {}
        self._validate_config()

    @abstractmethod
    def _validate_config(self):
        """
        Validate that all required configuration is present.
        Should raise an exception if config is invalid.
        """
        pass

    @abstractmethod
    def recommend_outfit(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ) -> VLMResponse:
        """
        Generate outfit recommendation using the VLM.

        Args:
            wardrobe_items: List of dicts containing:
                - id: Item ID
                - name: Item name
                - type: Item type (shirt, pants, etc.)
                - image_url: URL to the item's image
                - metadata: Dict with materials, temperature range, etc.

            weather_context: Dict with:
                - temperature: Current temperature
                - condition: Weather condition (sunny, rainy, snowy)
                - humidity: Humidity percentage
                - wind_speed: Wind speed

            user_context: Optional dict with:
                - preferences: User style preferences
                - occasion: What the outfit is for
                - excluded_items: Item IDs to exclude
                - usage_frequency: Dict of item_id -> usage count

            prompt_template: Optional custom prompt template for the VLM.
                           If None, uses default.

        Returns:
            VLMResponse object with recommendations and reasoning
        """
        pass

    @abstractmethod
    def recommend_travel_outfits(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_forecast: List[Dict[str, Any]],
        num_days: int,
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ) -> List[VLMResponse]:
        """
        Generate multiple outfit recommendations for a trip.

        Args:
            wardrobe_items: List of available clothing items
            weather_forecast: List of dicts with daily weather data
            num_days: Number of days for the trip
            user_context: Optional user preferences and context
            prompt_template: Optional custom prompt template

        Returns:
            List of VLMResponse objects, one per day/scenario
        """
        pass

    @abstractmethod
    def recommend_alternatives(
        self,
        current_outfit_items: List[Dict[str, Any]],
        all_wardrobe_items: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
        num_alternatives: int = 3,
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ) -> List[VLMResponse]:
        """
        Generate alternative outfit suggestions.

        Args:
            current_outfit_items: Items in the current/primary outfit
            all_wardrobe_items: All available wardrobe items
            weather_context: Weather information
            num_alternatives: How many alternatives to suggest
            user_context: Optional user preferences
            prompt_template: Optional custom prompt template

        Returns:
            List of VLMResponse objects with alternative outfits
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the VLM service is available and working.

        Returns:
            True if service is healthy, False otherwise
        """
        pass

    def format_error_response(self, error: str) -> VLMResponse:
        """
        Helper method to create a standardized error response.

        Args:
            error: Error message

        Returns:
            VLMResponse with success=False and error message
        """
        return VLMResponse(
            success=False,
            error=error,
            outfit_items=[],
            reasoning="",
            confidence_score=0.0,
        )


class LLaVAService(VLMServiceInterface):
    """
    LLaVA (Large Language and Vision Assistant) service implementation.

    This is the primary VLM service for the outfit recommendation system.
    LLaVA combines vision understanding with language generation to analyze
    wardrobe items and suggest outfits.

    Note: This is a placeholder for Phase 1. Full implementation comes in Phase 2.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize LLaVA service."""
        super().__init__(VLMProviderEnum.LLAVA, config)

    def _validate_config(self):
        """
        Validate LLaVA configuration.

        Required config keys (in Phase 2):
        - model_name: Name of the LLaVA model to use
        - api_endpoint: URL to the LLaVA API
        - timeout: Request timeout in seconds
        """
        # Phase 1: Placeholder validation
        # Phase 2: Will validate API endpoints, model availability, etc.
        pass

    def recommend_outfit(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ) -> VLMResponse:
        """
        Generate outfit recommendation using LLaVA.

        Phase 1: Placeholder that returns empty response
        Phase 2: Will call actual LLaVA model
        """
        # TODO: Phase 2 - Implement actual LLaVA call
        return VLMResponse(
            success=False,
            error="LLaVA integration not yet implemented (Phase 2)",
            outfit_items=[],
            reasoning="Placeholder response - LLaVA integration pending",
        )

    def recommend_travel_outfits(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_forecast: List[Dict[str, Any]],
        num_days: int,
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ) -> List[VLMResponse]:
        """Generate travel outfit recommendations using LLaVA."""
        # TODO: Phase 2 - Implement actual LLaVA call
        return [
            VLMResponse(
                success=False,
                error="LLaVA integration not yet implemented (Phase 2)",
                outfit_items=[],
                reasoning="Placeholder response - LLaVA integration pending",
            )
            for _ in range(num_days)
        ]

    def recommend_alternatives(
        self,
        current_outfit_items: List[Dict[str, Any]],
        all_wardrobe_items: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
        num_alternatives: int = 3,
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ) -> List[VLMResponse]:
        """Generate alternative outfit suggestions using LLaVA."""
        # TODO: Phase 2 - Implement actual LLaVA call
        return [
            VLMResponse(
                success=False,
                error="LLaVA integration not yet implemented (Phase 2)",
                outfit_items=[],
                reasoning="Placeholder response - LLaVA integration pending",
            )
            for _ in range(num_alternatives)
        ]

    def health_check(self) -> bool:
        """Check if LLaVA service is available."""
        # TODO: Phase 2 - Implement actual health check
        return False


class MockVLMService(VLMServiceInterface):
    """
    Mock VLM service for testing and development.

    Returns pre-defined outfit recommendations without calling any real VLM.
    Useful for frontend development and testing the recommendation pipeline.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize mock VLM service."""
        super().__init__(VLMProviderEnum.MOCK, config)

    def _validate_config(self):
        """Mock validation - always passes."""
        pass

    def recommend_outfit(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ) -> VLMResponse:
        """Return a mock outfit recommendation."""
        # Return first 3-4 items as a mock outfit
        mock_items = (
            [item["id"] for item in wardrobe_items[:4]] if wardrobe_items else []
        )

        return VLMResponse(
            success=True,
            outfit_items=mock_items,
            reasoning="Mock recommendation: Selected items based on weather and wardrobe availability",
            confidence_score=0.85,
            metadata={"model": "mock", "response_time_ms": 50},
        )

    def recommend_travel_outfits(
        self,
        wardrobe_items: List[Dict[str, Any]],
        weather_forecast: List[Dict[str, Any]],
        num_days: int,
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ) -> List[VLMResponse]:
        """Return mock travel outfit recommendations."""
        responses = []
        for day in range(num_days):
            mock_items = [
                item["id"]
                for item in wardrobe_items[
                    day % len(wardrobe_items) : (day + 1) % len(wardrobe_items) + 4
                ]
            ]
            responses.append(
                VLMResponse(
                    success=True,
                    outfit_items=mock_items,
                    reasoning=f"Mock recommendation for day {day + 1}",
                    confidence_score=0.8,
                    metadata={"day": day + 1},
                )
            )
        return responses

    def recommend_alternatives(
        self,
        current_outfit_items: List[Dict[str, Any]],
        all_wardrobe_items: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
        num_alternatives: int = 3,
        user_context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ) -> List[VLMResponse]:
        """Return mock alternative outfit suggestions."""
        responses = []
        for i in range(num_alternatives):
            # Rotate through wardrobe items for different alternatives
            start_idx = (i * 2) % len(all_wardrobe_items)
            end_idx = min(start_idx + 4, len(all_wardrobe_items))
            mock_items = [item["id"] for item in all_wardrobe_items[start_idx:end_idx]]

            responses.append(
                VLMResponse(
                    success=True,
                    outfit_items=mock_items,
                    reasoning=f"Mock alternative outfit {i + 1}",
                    confidence_score=0.75,
                    metadata={"alternative_number": i + 1},
                )
            )
        return responses

    def health_check(self) -> bool:
        """Mock service is always healthy."""
        return True
