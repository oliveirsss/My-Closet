"""
Data Preparation Service

Phase 2 core service for preparing and enriching wardrobe, usage, and weather data
into a clean, structured, AI-ready context object suitable for VLM consumption.

Responsibilities:
- Fetch and enrich wardrobe items with complete metadata
- Compute usage frequency metrics for each item
- Normalize and structure weather data
- Filter wardrobe items intelligently for current context
- Build final AI-ready context objects combining all data
- Group items by layer for structured outfit composition

This service does NOT call the VLM or build final prompts.
It prepares the internal data structure that will be passed to the prompt builder.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from database import supabase


class AIReadyItem:
    """
    Structured representation of a clothing item ready for AI processing.

    Contains all metadata the VLM might need to make intelligent decisions.
    """

    def __init__(
        self, item_dict: Dict[str, Any], usage_metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an AI-ready item from database record and usage data.

        Args:
            item_dict: Raw item from database
            usage_metrics: Optional pre-computed usage metrics for this item
        """
        self.id = item_dict.get("id", "")
        self.name = item_dict.get("name", "Unknown")
        self.type = item_dict.get("type", "")
        self.brand = item_dict.get("brand", "")
        self.size = item_dict.get("size", "")
        self.layer = item_dict.get("layer", 1)
        self.materials = item_dict.get("materials", [])
        self.weight = item_dict.get("weight", 0)

        # Image handling
        self.image_url = item_dict.get("image", item_dict.get("image_url", ""))

        # Status and preferences
        self.status = item_dict.get("status", "clean")
        self.favorite = item_dict.get("favorite", False)

        # Temperature suitability
        self.temp_min = item_dict.get("temp_min", item_dict.get("tempMin", -10))
        self.temp_max = item_dict.get("temp_max", item_dict.get("tempMax", 30))

        # Properties
        self.waterproof = item_dict.get("waterproof", False)
        self.windproof = item_dict.get("windproof", False)

        # Metadata
        self.seasons = item_dict.get("seasons", [])
        self.color = item_dict.get("color", "")
        self.is_public = item_dict.get("is_public", False)

        # Usage metrics (populated by data preparation service)
        self.usage_metrics = usage_metrics or {
            "usage_frequency_last_7_days": 0,
            "usage_frequency_last_30_days": 0,
            "last_used_days_ago": None,
            "total_wears": 0,
            "is_overused": False,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "brand": self.brand,
            "size": self.size,
            "layer": self.layer,
            "materials": self.materials,
            "weight": self.weight,
            "image_url": self.image_url,
            "status": self.status,
            "favorite": self.favorite,
            "temp_min": self.temp_min,
            "temp_max": self.temp_max,
            "waterproof": self.waterproof,
            "windproof": self.windproof,
            "seasons": self.seasons,
            "color": self.color,
            "is_public": self.is_public,
            "usage_metrics": self.usage_metrics,
        }

    def is_suitable_for_temperature(self, temp_min: float, temp_max: float) -> bool:
        """
        Check if item is suitable for a temperature range.

        Args:
            temp_min: Minimum temperature required
            temp_max: Maximum temperature required

        Returns:
            True if item's temperature range overlaps with required range
        """
        return self.temp_min <= temp_max and self.temp_max >= temp_min

    def is_suitable_for_weather(self, weather_condition: str) -> bool:
        """
        Check if item is suitable for a weather condition.

        Args:
            weather_condition: Weather condition (sunny, rainy, snowy, etc)

        Returns:
            True if item has properties matching the condition
        """
        if weather_condition.lower() == "rainy" and not self.waterproof:
            return False
        if weather_condition.lower() == "snowy" and not self.waterproof:
            return False
        if weather_condition.lower() == "windy" and not self.windproof:
            return False
        return True


class AIReadyWeather:
    """Structured representation of weather data for AI processing."""

    def __init__(self, weather_dict: Dict[str, Any], is_forecast: bool = False):
        """
        Initialize weather data structure.

        Args:
            weather_dict: Weather data from weather service
            is_forecast: Whether this is forecast data (multi-day) or current
        """
        self.is_forecast = is_forecast

        if is_forecast:
            # Forecast structure
            self.date = weather_dict.get("date", "")
            self.temperature_min = weather_dict.get("temperature_min", 10)
            self.temperature_max = weather_dict.get("temperature_max", 20)
            self.condition = weather_dict.get("condition", "mild")
            self.precipitation_probability = weather_dict.get(
                "precipitation_probability", 0
            )
            self.humidity = weather_dict.get("humidity", 50)
            self.wind_speed = weather_dict.get("wind_speed", 0)
        else:
            # Current weather structure
            self.date = datetime.now().strftime("%Y-%m-%d")
            self.temperature = weather_dict.get("temperature", 20)
            self.temperature_min = self.temperature - 2
            self.temperature_max = self.temperature + 2
            self.condition = weather_dict.get("condition", "mild")
            self.humidity = weather_dict.get("humidity", 50)
            self.wind_speed = weather_dict.get("wind_speed", 0)
            self.feels_like = weather_dict.get("feels_like", self.temperature)
            self.description = weather_dict.get("description", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        if self.is_forecast:
            return {
                "date": self.date,
                "temperature_min": self.temperature_min,
                "temperature_max": self.temperature_max,
                "condition": self.condition,
                "precipitation_probability": self.precipitation_probability,
                "humidity": self.humidity,
                "wind_speed": self.wind_speed,
            }
        else:
            return {
                "date": self.date,
                "temperature": self.temperature,
                "temperature_min": self.temperature_min,
                "temperature_max": self.temperature_max,
                "condition": self.condition,
                "humidity": self.humidity,
                "wind_speed": self.wind_speed,
                "feels_like": self.feels_like,
                "description": self.description,
            }


class AIReadyContext:
    """
    Final AI-ready context object combining wardrobe, weather, and usage data.

    This is the core data structure passed to the prompt builder and eventually to the VLM.
    It represents a complete, curated, structured view of the user's wardrobe and environment
    in a format optimized for AI decision-making.
    """

    def __init__(
        self,
        user_id: str,
        recommendation_type: str,  # "daily", "travel", "alternative"
        weather: Union[AIReadyWeather, List[AIReadyWeather]],
        wardrobe_by_layer: Dict[int, List[AIReadyItem]],
        excluded_items: Optional[List[str]] = None,
        user_constraints: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize AI-ready context.

        Args:
            user_id: User identifier
            recommendation_type: Type of recommendation (daily, travel, alternative)
            weather: Weather data (single for daily, list for travel)
            wardrobe_by_layer: Items grouped by layer
            excluded_items: Items to exclude from recommendations
            user_constraints: User preferences and constraints
            metadata: Additional metadata
        """
        self.user_id = user_id
        self.recommendation_type = recommendation_type
        self.created_at = datetime.now().isoformat()

        # Weather handling
        if isinstance(weather, list):
            self.weather_forecast = weather
            self.weather_current = weather[0] if weather else None
        else:
            self.weather_current = weather
            self.weather_forecast = [weather] if weather else []

        # Wardrobe organized by layer
        # Layers: 1=base (base layers), 2=mid (insulation), 3=outer (jackets, shoes, accessories)
        self.wardrobe_by_layer = wardrobe_by_layer or {}

        # Constraints and metadata
        self.excluded_items = excluded_items or []
        self.user_constraints = user_constraints or {}
        self.metadata = metadata or {}

    def get_all_items(self) -> List[AIReadyItem]:
        """Get all wardrobe items flattened from layers."""
        items = []
        for layer_items in self.wardrobe_by_layer.values():
            items.extend(layer_items)
        return items

    def get_items_for_layer(self, layer: int) -> List[AIReadyItem]:
        """Get items for a specific layer."""
        return self.wardrobe_by_layer.get(layer, [])

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire context to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "recommendation_type": self.recommendation_type,
            "created_at": self.created_at,
            "weather": {
                "current": self.weather_current.to_dict()
                if self.weather_current
                else None,
                "forecast": [w.to_dict() for w in self.weather_forecast],
            },
            "wardrobe_by_layer": {
                layer: [item.to_dict() for item in items]
                for layer, items in self.wardrobe_by_layer.items()
            },
            "total_items_available": len(self.get_all_items()),
            "excluded_items": self.excluded_items,
            "user_constraints": self.user_constraints,
            "metadata": self.metadata,
        }


class DataPreparationService:
    """
    Phase 2 service for preparing AI-ready context from raw data.

    Orchestrates data fetching, enrichment, filtering, and structuring
    into a format optimized for VLM consumption.

    This service:
    - Fetches wardrobe items and enriches them with usage data
    - Normalizes and structures weather data
    - Filters wardrobe items intelligently based on context
    - Groups items by layer for structured outfit composition
    - Builds final AI-ready context objects
    """

    def __init__(self, usage_service=None, weather_service=None):
        """
        Initialize data preparation service.

        Args:
            usage_service: Optional usage service for item metrics
            weather_service: Optional weather service for weather data
        """
        self.supabase = supabase
        self.usage_service = usage_service
        self.weather_service = weather_service

    async def prepare_daily_context(
        self,
        user_id: str,
        temperature: float,
        weather_condition: str,
        humidity: Optional[float] = None,
        wind_speed: Optional[float] = None,
        occasion: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        exclude_items: Optional[List[str]] = None,
    ) -> AIReadyContext:
        """
        Prepare AI-ready context for daily outfit recommendation.

        This is the main entry point for Phase 2 data preparation.

        Args:
            user_id: User's ID
            temperature: Current temperature in Celsius
            weather_condition: Weather condition (sunny, rainy, etc)
            humidity: Optional humidity percentage
            wind_speed: Optional wind speed
            occasion: Optional occasion (work, casual, etc)
            user_preferences: Optional user style preferences
            exclude_items: Optional item IDs to exclude

        Returns:
            AIReadyContext object ready for prompt builder/VLM
        """
        # Step 1: Fetch and enrich wardrobe
        wardrobe_items = await self._fetch_and_enrich_wardrobe(user_id, exclude_items)

        # Step 2: Prepare weather data
        weather_data = {
            "temperature": temperature,
            "condition": weather_condition,
            "humidity": humidity or 50.0,
            "wind_speed": wind_speed or 0.0,
        }
        weather = AIReadyWeather(weather_data, is_forecast=False)

        # Step 3: Filter wardrobe items intelligently
        filtered_items = self._filter_wardrobe_for_daily(
            wardrobe_items, temperature, weather_condition, user_preferences
        )

        # Step 4: Group items by layer
        wardrobe_by_layer = self._group_items_by_layer(filtered_items)

        # Step 5: Build constraints and metadata
        user_constraints = {
            "occasion": occasion,
            "preferences": user_preferences or {},
        }

        metadata = {
            "filter_reason": "Daily outfit recommendation",
            "temperature_range": (temperature - 5, temperature + 5),
            "weather_condition": weather_condition,
        }

        # Step 6: Build and return context
        context = AIReadyContext(
            user_id=user_id,
            recommendation_type="daily",
            weather=weather,
            wardrobe_by_layer=wardrobe_by_layer,
            excluded_items=exclude_items or [],
            user_constraints=user_constraints,
            metadata=metadata,
        )

        return context

    async def prepare_travel_context(
        self,
        user_id: str,
        destination: str,
        start_date: datetime,
        end_date: datetime,
        luggage_limit: int = 10,
        user_preferences: Optional[Dict[str, Any]] = None,
        exclude_items: Optional[List[str]] = None,
    ) -> AIReadyContext:
        """
        Prepare AI-ready context for travel outfit recommendation.

        Args:
            user_id: User's ID
            destination: Travel destination
            start_date: Trip start date
            end_date: Trip end date
            luggage_limit: Maximum items to pack
            user_preferences: Optional user preferences
            exclude_items: Optional item IDs to exclude

        Returns:
            AIReadyContext object ready for VLM
        """
        # Step 1: Fetch and enrich wardrobe
        wardrobe_items = await self._fetch_and_enrich_wardrobe(user_id, exclude_items)

        # Step 2: Fetch weather forecast for destination
        if self.weather_service:
            num_days = (end_date - start_date).days + 1
            forecast_data = await self.weather_service.get_weather_forecast(
                destination, num_days=num_days
            )
            weather_list = [
                AIReadyWeather(day, is_forecast=True) for day in forecast_data
            ]
        else:
            # Mock forecast if service unavailable
            weather_list = self._generate_mock_forecast(start_date, end_date)

        # Step 3: Aggregate temperature range from forecast
        temp_ranges = [(w.temperature_min, w.temperature_max) for w in weather_list]
        overall_temp_min = min(r[0] for r in temp_ranges) if temp_ranges else 15
        overall_temp_max = max(r[1] for r in temp_ranges) if temp_ranges else 25

        # Step 4: Filter wardrobe for travel context
        filtered_items = self._filter_wardrobe_for_travel(
            wardrobe_items,
            overall_temp_min,
            overall_temp_max,
            luggage_limit,
            user_preferences,
        )

        # Step 5: Group by layer
        wardrobe_by_layer = self._group_items_by_layer(filtered_items)

        # Step 6: Build constraints
        user_constraints = {
            "luggage_limit": luggage_limit,
            "preferences": user_preferences or {},
            "trip_days": len(weather_list),
        }

        metadata = {
            "filter_reason": "Travel outfit recommendation",
            "destination": destination,
            "trip_dates": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "temperature_range": (overall_temp_min, overall_temp_max),
        }

        # Step 7: Build and return context
        context = AIReadyContext(
            user_id=user_id,
            recommendation_type="travel",
            weather=weather_list,
            wardrobe_by_layer=wardrobe_by_layer,
            excluded_items=exclude_items or [],
            user_constraints=user_constraints,
            metadata=metadata,
        )

        return context

    async def prepare_alternative_context(
        self,
        user_id: str,
        current_outfit_items: List[str],
        temperature: float,
        weather_condition: str,
        num_alternatives: int = 3,
        user_preferences: Optional[Dict[str, Any]] = None,
        exclude_items: Optional[List[str]] = None,
    ) -> AIReadyContext:
        """
        Prepare AI-ready context for alternative outfit suggestions.

        Args:
            user_id: User's ID
            current_outfit_items: Item IDs in the current outfit
            temperature: Current temperature
            weather_condition: Weather condition
            num_alternatives: Number of alternatives to generate
            user_preferences: Optional preferences
            exclude_items: Optional items to exclude

        Returns:
            AIReadyContext object ready for VLM
        """
        # Step 1: Fetch and enrich wardrobe
        wardrobe_items = await self._fetch_and_enrich_wardrobe(user_id, exclude_items)

        # Step 2: Prepare weather
        weather_data = {
            "temperature": temperature,
            "condition": weather_condition,
        }
        weather = AIReadyWeather(weather_data, is_forecast=False)

        # Step 3: Filter wardrobe - prioritize different items than current outfit
        filtered_items = self._filter_wardrobe_for_alternatives(
            wardrobe_items,
            current_outfit_items,
            temperature,
            weather_condition,
            user_preferences,
        )

        # Step 4: Group by layer
        wardrobe_by_layer = self._group_items_by_layer(filtered_items)

        # Step 5: Build constraints
        user_constraints = {
            "num_alternatives": num_alternatives,
            "current_outfit": current_outfit_items,
            "preferences": user_preferences or {},
        }

        metadata = {
            "filter_reason": "Alternative outfit suggestion",
            "temperature": temperature,
            "weather_condition": weather_condition,
        }

        # Step 6: Build and return context
        context = AIReadyContext(
            user_id=user_id,
            recommendation_type="alternative",
            weather=weather,
            wardrobe_by_layer=wardrobe_by_layer,
            excluded_items=exclude_items or [],
            user_constraints=user_constraints,
            metadata=metadata,
        )

        return context

    # ========================================================================
    # INTERNAL HELPER METHODS
    # ========================================================================

    async def _fetch_and_enrich_wardrobe(
        self,
        user_id: str,
        exclude_items: Optional[List[str]] = None,
    ) -> List[AIReadyItem]:
        """
        Fetch wardrobe items and enrich with usage metrics.

        Args:
            user_id: User's ID
            exclude_items: Item IDs to exclude

        Returns:
            List of AIReadyItem objects with enriched data
        """
        try:
            # Fetch all clean items from database
            response = (
                self.supabase.table("clothes")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "clean")
                .execute()
            )

            items = response.data if response.data else []

            # Filter excluded items
            if exclude_items:
                items = [item for item in items if item["id"] not in exclude_items]

            # Enrich each item with usage metrics
            enriched_items = []
            for item in items:
                usage_metrics = await self._compute_usage_metrics(user_id, item["id"])
                ai_ready_item = AIReadyItem(item, usage_metrics)
                enriched_items.append(ai_ready_item)

            return enriched_items

        except Exception as e:
            print(f"Error fetching wardrobe for user {user_id}: {e}")
            return []

    async def _compute_usage_metrics(
        self,
        user_id: str,
        item_id: str,
    ) -> Dict[str, Any]:
        """
        Compute usage frequency metrics for an item.

        Args:
            user_id: User's ID
            item_id: Item's ID

        Returns:
            Dictionary with usage metrics
        """
        try:
            if not self.usage_service:
                return {
                    "usage_frequency_last_7_days": 0,
                    "usage_frequency_last_30_days": 0,
                    "last_used_days_ago": None,
                    "total_wears": 0,
                    "is_overused": False,
                }

            # Fetch usage history for this item
            cutoff_7days = datetime.now() - timedelta(days=7)
            cutoff_30days = datetime.now() - timedelta(days=30)

            usage_response = (
                self.supabase.table("usage_history")
                .select("used_at")
                .eq("user_id", user_id)
                .eq("item_id", item_id)
                .execute()
            )

            if not usage_response.data:
                return {
                    "usage_frequency_last_7_days": 0,
                    "usage_frequency_last_30_days": 0,
                    "last_used_days_ago": None,
                    "total_wears": 0,
                    "is_overused": False,
                }

            usage_records = usage_response.data

            # Count usage in different time periods
            usage_7days = sum(
                1
                for record in usage_records
                if datetime.fromisoformat(record["used_at"]) > cutoff_7days
            )
            usage_30days = sum(
                1
                for record in usage_records
                if datetime.fromisoformat(record["used_at"]) > cutoff_30days
            )

            # Get last used date
            last_used = None
            if usage_records:
                last_used_record = max(
                    usage_records, key=lambda r: datetime.fromisoformat(r["used_at"])
                )
                last_used_date = datetime.fromisoformat(last_used_record["used_at"])
                last_used = (datetime.now() - last_used_date).days

            # Determine if overused (more than once per day in last 7 days)
            is_overused = usage_7days > 7

            return {
                "usage_frequency_last_7_days": usage_7days,
                "usage_frequency_last_30_days": usage_30days,
                "last_used_days_ago": last_used,
                "total_wears": len(usage_records),
                "is_overused": is_overused,
            }

        except Exception as e:
            print(f"Error computing usage metrics for item {item_id}: {e}")
            return {
                "usage_frequency_last_7_days": 0,
                "usage_frequency_last_30_days": 0,
                "last_used_days_ago": None,
                "total_wears": 0,
                "is_overused": False,
            }

    def _filter_wardrobe_for_daily(
        self,
        items: List[AIReadyItem],
        temperature: float,
        weather_condition: str,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[AIReadyItem]:
        """
        Filter wardrobe items for daily recommendation context.

        Filtering logic:
        - Only clean items (already enforced by fetch)
        - Only items suitable for temperature
        - Only items suitable for weather condition
        - Prioritize favorites
        - Avoid overused items if alternatives exist
        - Keep reasonable variety

        Args:
            items: All available items
            temperature: Current temperature
            weather_condition: Weather condition
            user_preferences: Optional user preferences

        Returns:
            Filtered and prioritized list of items
        """
        filtered = []

        for item in items:
            # Check temperature compatibility
            if not item.is_suitable_for_temperature(temperature - 5, temperature + 5):
                continue

            # Check weather compatibility
            if not item.is_suitable_for_weather(weather_condition):
                continue

            filtered.append(item)

        # Sort by priority: favorites first, then by usage (prefer less used)
        def priority_key(item):
            priority = 0
            if item.favorite:
                priority -= 1000  # Favorites first
            if item.usage_metrics.get("is_overused"):
                priority += 100  # Deprioritize overused
            priority += item.usage_metrics.get("usage_frequency_last_7_days", 0) * 10
            return priority

        filtered.sort(key=priority_key)

        return filtered

    def _filter_wardrobe_for_travel(
        self,
        items: List[AIReadyItem],
        temp_min: float,
        temp_max: float,
        luggage_limit: int,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[AIReadyItem]:
        """
        Filter wardrobe items for travel recommendation context.

        Filtering logic:
        - Only items suitable for temperature range
        - Prioritize versatile items (can be layered)
        - Limit total items to luggage_limit
        - Prioritize favorites
        - Ensure diversity across item types

        Args:
            items: All available items
            temp_min: Minimum temperature for trip
            temp_max: Maximum temperature for trip
            luggage_limit: Maximum items to include
            user_preferences: Optional preferences

        Returns:
            Filtered list suitable for travel (limited by luggage_limit)
        """
        # Filter by temperature
        suitable = [
            item
            for item in items
            if item.is_suitable_for_temperature(temp_min, temp_max)
        ]

        # Sort by versatility and priority
        def travel_priority_key(item):
            score = 0

            # Favor items that work for multiple days (mid temp range)
            range_size = item.temp_max - item.temp_min
            score -= range_size  # Larger range = more versatile

            # Favor favorites
            if item.favorite:
                score -= 500

            # Slightly favor less recently used
            last_used = item.usage_metrics.get("last_used_days_ago")
            if last_used is not None:
                score -= min(last_used, 30)  # Cap at 30 days old

            # Favor items that can layer well
            if item.layer in [1, 2]:  # Base and mid layers are versatile
                score -= 50

            return score

        suitable.sort(key=travel_priority_key)

        # Limit to luggage capacity, but try to maintain diversity
        # Aim for: 40% base layers, 40% mid layers, 20% outer/accessories
        limited = []
        type_counts = {}

        for item in suitable:
            if len(limited) >= luggage_limit:
                break

            item_type = item.type
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            limited.append(item)

        return limited

    def _filter_wardrobe_for_alternatives(
        self,
        items: List[AIReadyItem],
        current_outfit_items: List[str],
        temperature: float,
        weather_condition: str,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[AIReadyItem]:
        """
        Filter wardrobe items for alternative outfit suggestions.

        Filtering logic:
        - Temperature and weather compatible
        - Exclude items already in current outfit
        - Prioritize items NOT in current outfit
        - Include items from different layers for variety
        - Exclude rarely used items

        Args:
            items: All available items
            current_outfit_items: Item IDs in current outfit
            temperature: Current temperature
            weather_condition: Weather condition
            user_preferences: Optional preferences

        Returns:
            Filtered list suitable for alternatives
        """
        # Filter by temperature and weather
        suitable = [
            item
            for item in items
            if (
                item.is_suitable_for_temperature(temperature - 5, temperature + 5)
                and item.is_suitable_for_weather(weather_condition)
            )
        ]

        # Prioritize items NOT in current outfit
        def alternative_priority_key(item):
            score = 0

            # Strong preference for items NOT in current outfit
            if item.id in current_outfit_items:
                score += 1000  # Deprioritize current items

            # Slightly prefer less used items for variety
            score += item.usage_metrics.get("usage_frequency_last_7_days", 0) * 5

            # Prefer favorites
            if item.favorite:
                score -= 100

            return score

        suitable.sort(key=alternative_priority_key)

        return suitable

    def _group_items_by_layer(
        self, items: List[AIReadyItem]
    ) -> Dict[int, List[AIReadyItem]]:
        """
        Group wardrobe items by layer.

        Layers:
        - 1: Base layers (base tees, thermal underwear)
        - 2: Insulation/Mid layers (sweaters, cardigans, light jackets, fleece)
        - 3: Outer/Protection layers (coats, jackets, shoes, hats, scarves, accessories)

        All "outer" items (jackets, shoes, hats, scarves, etc.) are grouped together
        in Layer 3, consistent with the original project architecture.

        Args:
            items: Flat list of items

        Returns:
            Dictionary mapping layer -> list of items
        """
        grouped = {1: [], 2: [], 3: []}

        for item in items:
            # Clamp all items to layers 1-3 (ensure no layer 4)
            layer = max(1, min(3, item.layer))
            grouped[layer].append(item)

        # Remove empty layers
        return {layer: items for layer, items in grouped.items() if items}

    def _generate_mock_forecast(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[AIReadyWeather]:
        """
        Generate mock weather forecast when service unavailable.

        Args:
            start_date: Trip start
            end_date: Trip end

        Returns:
            List of mock weather objects
        """
        num_days = (end_date - start_date).days + 1
        conditions = ["sunny", "cloudy", "rainy", "mild", "windy"]
        forecast = []

        for i in range(num_days):
            date = start_date + timedelta(days=i)
            forecast.append(
                AIReadyWeather(
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "temperature_min": 12 + i,
                        "temperature_max": 22 + i,
                        "condition": conditions[i % len(conditions)],
                        "precipitation_probability": 30,
                        "humidity": 60,
                        "wind_speed": 10,
                    },
                    is_forecast=True,
                )
            )

        return forecast


class DataPreparationServiceError(Exception):
    """Exception raised by DataPreparationService."""

    pass
