"""
Test script for DataPreparationService
Tests prepare_daily_context() with sample data
"""

import asyncio
import json
from datetime import datetime

# Mock database setup for testing
from unittest.mock import AsyncMock, MagicMock, patch

from services.data_preparation_service import (
    AIReadyContext,
    AIReadyItem,
    AIReadyWeather,
    DataPreparationService,
)


async def test_prepare_daily_context():
    """Test prepare_daily_context with mock data"""
    print("=" * 80)
    print("TESTING DataPreparationService.prepare_daily_context()")
    print("=" * 80)

    # Create service instance
    service = DataPreparationService(usage_service=None, weather_service=None)

    # Mock wardrobe data (simulating database response)
    mock_wardrobe_data = [
        {
            "id": "item-001",
            "name": "Cotton T-Shirt",
            "type": "shirt",
            "brand": "Gap",
            "size": "M",
            "layer": 1,
            "materials": ["cotton"],
            "weight": 0.15,
            "image": "https://example.com/tshirt.jpg",
            "status": "clean",
            "favorite": True,
            "temp_min": 5,
            "temp_max": 30,
            "waterproof": False,
            "windproof": False,
            "seasons": ["spring", "summer", "fall"],
            "color": "navy",
            "is_public": False,
        },
        {
            "id": "item-002",
            "name": "Wool Sweater",
            "type": "sweater",
            "brand": "J.Crew",
            "size": "M",
            "layer": 2,
            "materials": ["wool"],
            "weight": 0.35,
            "image": "https://example.com/sweater.jpg",
            "status": "clean",
            "favorite": False,
            "temp_min": 0,
            "temp_max": 20,
            "waterproof": False,
            "windproof": False,
            "seasons": ["fall", "winter"],
            "color": "grey",
            "is_public": False,
        },
        {
            "id": "item-003",
            "name": "Waterproof Jacket",
            "type": "jacket",
            "brand": "Uniqlo",
            "size": "M",
            "layer": 3,
            "materials": ["polyester"],
            "weight": 0.45,
            "image": "https://example.com/jacket.jpg",
            "status": "clean",
            "favorite": True,
            "temp_min": -10,
            "temp_max": 15,
            "waterproof": True,
            "windproof": True,
            "seasons": ["fall", "winter"],
            "color": "black",
            "is_public": False,
        },
        {
            "id": "item-004",
            "name": "Jeans",
            "type": "pants",
            "brand": "Levi",
            "size": "32",
            "layer": 2,
            "materials": ["denim"],
            "weight": 0.6,
            "image": "https://example.com/jeans.jpg",
            "status": "clean",
            "favorite": False,
            "temp_min": 0,
            "temp_max": 25,
            "waterproof": False,
            "windproof": False,
            "seasons": ["spring", "summer", "fall", "winter"],
            "color": "blue",
            "is_public": False,
        },
        {
            "id": "item-005",
            "name": "Canvas Belt",
            "type": "accessory",
            "brand": "Fossil",
            "size": "M",
            "layer": 4,
            "materials": ["canvas"],
            "weight": 0.08,
            "image": "https://example.com/belt.jpg",
            "status": "clean",
            "favorite": False,
            "temp_min": -20,
            "temp_max": 40,
            "waterproof": False,
            "windproof": False,
            "seasons": ["spring", "summer", "fall", "winter"],
            "color": "brown",
            "is_public": False,
        },
    ]

    # Mock the database query to return wardrobe data
    mock_response = MagicMock()
    mock_response.data = mock_wardrobe_data

    # Patch the supabase client
    with patch.object(service.supabase, "table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        # Mock usage history (empty for simplicity)
        usage_response = MagicMock()
        usage_response.data = []

        mock_table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = (
            usage_response
        )

        # Call the service
        context = await service.prepare_daily_context(
            user_id="test-user-123",
            temperature=18,
            weather_condition="cloudy",
            humidity=65,
            wind_speed=12,
            occasion="work",
            user_preferences={"style": "smart casual", "colors": ["blue", "grey"]},
            exclude_items=None,
        )

        # Verify the context
        print("\n✓ prepare_daily_context() executed successfully")
        print(f"  User ID: {context.user_id}")
        print(f"  Recommendation Type: {context.recommendation_type}")
        print(f"  Created At: {context.created_at}")

        # Check wardrobe by layer
        print(f"\n✓ Wardrobe organized by layer:")
        for layer, items in context.wardrobe_by_layer.items():
            print(f"  Layer {layer}: {len(items)} items")
            for item in items:
                print(f"    - {item.name} (ID: {item.id})")
                print(f"      Type: {item.type}, Temp: {item.temp_min}°-{item.temp_max}°C")
                print(
                    f"      Usage (7d): {item.usage_metrics['usage_frequency_last_7_days']}, (30d): {item.usage_metrics['usage_frequency_last_30_days']}"
                )

        # Check weather
        print(f"\n✓ Weather Data:")
        if context.weather_current:
            weather_dict = context.weather_current.to_dict()
            print(f"  Condition: {weather_dict['condition']}")
            print(f"  Temperature: {weather_dict['temperature']}°C")
            print(f"  Humidity: {weather_dict['humidity']}%")
            print(f"  Wind Speed: {weather_dict['wind_speed']} km/h")

        # Check constraints
        print(f"\n✓ User Constraints:")
        print(f"  Occasion: {context.user_constraints.get('occasion')}")
        print(f"  Preferences: {context.user_constraints.get('preferences')}")

        # Check metadata
        print(f"\n✓ Metadata:")
        print(f"  Filter Reason: {context.metadata.get('filter_reason')}")
        print(f"  Temperature Range: {context.metadata.get('temperature_range')}")
        print(f"  Weather Condition: {context.metadata.get('weather_condition')}")

        # Print full JSON output
        print("\n" + "=" * 80)
        print("FULL JSON OUTPUT")
        print("=" * 80)
        context_dict = context.to_dict()
        print(json.dumps(context_dict, indent=2, default=str))

        return context_dict


if __name__ == "__main__":
    result = asyncio.run(test_prepare_daily_context())
    print("\n" + "=" * 80)
    print("✓ TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
