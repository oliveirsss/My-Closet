"""
Weather Service

Handles weather data retrieval and management:
- Fetch current weather conditions
- Retrieve weather forecasts
- Format weather data for AI recommendations
- Support multiple weather data sources
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class WeatherCondition(str, Enum):
    """Common weather conditions."""

    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    STORMY = "stormy"
    WINDY = "windy"
    HOT = "hot"
    COLD = "cold"
    MILD = "mild"
    HUMID = "humid"


class WeatherService:
    """
    Service for managing weather data for outfit recommendations.

    This service acts as an abstraction layer over weather data sources,
    allowing easy switching between different weather APIs or data providers.

    Responsibilities:
    - Fetch current weather for a location
    - Fetch weather forecasts
    - Format weather data for VLM consumption
    - Cache weather data to reduce API calls
    """

    def __init__(self, cache_duration_minutes: int = 30):
        """
        Initialize the weather service.

        Args:
            cache_duration_minutes: How long to cache weather data
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._weather_cache: Dict[str, tuple] = {}  # location -> (data, timestamp)

    async def get_current_weather(
        self, location: str, use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch current weather for a location.

        Args:
            location: Location/city name or coordinates
            use_cache: Whether to use cached data if available

        Returns:
            Dict containing:
            - temperature: Current temperature in Celsius
            - condition: Weather condition (sunny, rainy, etc.)
            - humidity: Humidity percentage (0-100)
            - wind_speed: Wind speed in km/h
            - description: Human-readable weather description
            - feels_like: How the temperature feels

        Raises:
            WeatherServiceError: If weather data cannot be fetched
        """
        # Check cache
        if use_cache and location in self._weather_cache:
            data, timestamp = self._weather_cache[location]
            if datetime.now() - timestamp < timedelta(
                minutes=self.cache_duration_minutes
            ):
                return data

        try:
            # Phase 1: Return mock weather data
            # Phase 2: Will integrate with real weather API (OpenWeatherMap, etc.)
            weather_data = self._get_mock_weather(location)

            # Cache the result
            self._weather_cache[location] = (weather_data, datetime.now())

            return weather_data

        except Exception as e:
            raise WeatherServiceError(
                f"Failed to fetch weather for {location}: {str(e)}"
            )

    async def get_weather_forecast(
        self, location: str, num_days: int = 5, use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch weather forecast for multiple days.

        Args:
            location: Location/city name or coordinates
            num_days: Number of days to forecast
            use_cache: Whether to use cached data if available

        Returns:
            List of daily forecast dicts, each containing:
            - date: Date of the forecast
            - temperature_min: Minimum temperature
            - temperature_max: Maximum temperature
            - condition: Expected weather condition
            - precipitation_probability: Chance of rain (0-100)
            - humidity: Expected humidity
            - wind_speed: Expected wind speed

        Raises:
            WeatherServiceError: If forecast data cannot be fetched
        """
        cache_key = f"{location}_forecast"

        # Check cache
        if use_cache and cache_key in self._weather_cache:
            data, timestamp = self._weather_cache[cache_key]
            if datetime.now() - timestamp < timedelta(
                minutes=self.cache_duration_minutes
            ):
                return data[:num_days]

        try:
            # Phase 1: Return mock forecast data
            # Phase 2: Will integrate with real weather API
            forecast_data = self._get_mock_forecast(location, num_days)

            # Cache the result
            self._weather_cache[cache_key] = (forecast_data, datetime.now())

            return forecast_data[:num_days]

        except Exception as e:
            raise WeatherServiceError(
                f"Failed to fetch forecast for {location}: {str(e)}"
            )

    async def get_temperature_range_forecast(
        self, location: str, num_days: int = 5
    ) -> List[Dict[str, float]]:
        """
        Get temperature range forecast (min/max for each day).

        Useful for filtering wardrobe items by suitable temperature range.

        Args:
            location: Location/city name or coordinates
            num_days: Number of days to forecast

        Returns:
            List of dicts with min/max temperature for each day
        """
        forecast = await self.get_weather_forecast(location, num_days)
        return [
            {
                "date": day["date"],
                "temp_min": day["temperature_min"],
                "temp_max": day["temperature_max"],
            }
            for day in forecast
        ]

    def clear_cache(self, location: Optional[str] = None) -> None:
        """
        Clear weather cache.

        Args:
            location: If provided, only clears cache for that location.
                     If None, clears entire cache.
        """
        if location:
            self._weather_cache.pop(location, None)
            self._weather_cache.pop(f"{location}_forecast", None)
        else:
            self._weather_cache.clear()

    def _get_mock_weather(self, location: str) -> Dict[str, Any]:
        """
        Generate mock current weather data for Phase 1.

        In Phase 2, this will be replaced with calls to a real weather API.
        """
        return {
            "temperature": 18,
            "condition": WeatherCondition.CLOUDY.value,
            "humidity": 65,
            "wind_speed": 12,
            "description": "Partly cloudy with moderate winds",
            "feels_like": 16,
            "location": location,
            "timestamp": datetime.now().isoformat(),
            "is_mock": True,
        }

    def _get_mock_forecast(self, location: str, num_days: int) -> List[Dict[str, Any]]:
        """
        Generate mock weather forecast for Phase 1.

        In Phase 2, this will be replaced with calls to a real weather API.
        """
        forecast = []
        conditions = [
            WeatherCondition.SUNNY.value,
            WeatherCondition.CLOUDY.value,
            WeatherCondition.RAINY.value,
            WeatherCondition.WINDY.value,
            WeatherCondition.MILD.value,
        ]

        for i in range(num_days):
            date = datetime.now() + timedelta(days=i)
            forecast.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "temperature_min": 12 + i,
                    "temperature_max": 22 + i,
                    "condition": conditions[i % len(conditions)],
                    "precipitation_probability": 30 + (i * 10),
                    "humidity": 60 + (i * 5),
                    "wind_speed": 10 + i,
                    "location": location,
                    "is_mock": True,
                }
            )

        return forecast


class WeatherServiceError(Exception):
    """Exception raised by WeatherService."""

    pass
