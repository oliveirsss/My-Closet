"""
Services module for AI-powered outfit recommendation system.

This package contains all service layer components for the AI recommendation
pipeline, including:

PHASE 1 SERVICES:
- wardrobe_service: Fetches and manages wardrobe items
- weather_service: Handles weather data retrieval
- usage_service: Tracks clothing item usage frequency
- prompt_service: Builds structured prompts for VLM
- vlm_service: Interface for Visual Language Model integration
- recommendation_service: Orchestrates the full recommendation pipeline
- response_parser: Normalizes and parses VLM responses

PHASE 2 SERVICES:
- data_preparation_service: Prepares AI-ready context from raw data
"""

from services.data_preparation_service import (
    AIReadyContext,
    AIReadyItem,
    AIReadyWeather,
    DataPreparationService,
    DataPreparationServiceError,
)
from services.prompt_service import PromptService, PromptServiceError
from services.recommendation_service import (
    RecommendationService,
    RecommendationServiceError,
)
from services.response_parser import ResponseParser, ResponseParserError
from services.usage_service import UsageService, UsageServiceError
from services.vlm_service import (
    LLaVAService,
    MockVLMService,
    VLMProviderEnum,
    VLMResponse,
    VLMServiceInterface,
)
from services.wardrobe_service import WardrobeService, WardrobeServiceError
from services.weather_service import WeatherService, WeatherServiceError

__all__ = [
    # Phase 1
    "WardrobeService",
    "WardrobeServiceError",
    "WeatherService",
    "WeatherServiceError",
    "UsageService",
    "UsageServiceError",
    "PromptService",
    "PromptServiceError",
    "VLMServiceInterface",
    "VLMResponse",
    "LLaVAService",
    "MockVLMService",
    "VLMProviderEnum",
    "RecommendationService",
    "RecommendationServiceError",
    "ResponseParser",
    "ResponseParserError",
    # Phase 2
    "AIReadyItem",
    "AIReadyWeather",
    "AIReadyContext",
    "DataPreparationService",
    "DataPreparationServiceError",
]
