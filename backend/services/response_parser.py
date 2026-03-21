"""
Response Parser Service

Handles parsing and normalizing VLM outputs:
- Extracts outfit item IDs from VLM responses
- Validates and structures the data
- Handles malformed or incomplete responses
- Converts VLM output to frontend-friendly format
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class ResponseParser:
    """Service for parsing and normalizing VLM responses."""

    def __init__(self):
        """Initialize response parser."""
        pass

    def parse_outfit_recommendation(
        self,
        vlm_response: Dict[str, Any],
        wardrobe: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Parse a VLM outfit recommendation response.

        Args:
            vlm_response: Raw VLM response
            wardrobe: Available wardrobe items
            weather_context: Current weather data

        Returns:
            Structured outfit recommendation
        """
        try:
            # Extract item IDs from response
            item_ids = self._extract_item_ids(vlm_response)

            # Validate items exist in wardrobe
            wardrobe_by_id = {item["id"]: item for item in wardrobe}
            valid_items = [
                wardrobe_by_id[iid] for iid in item_ids if iid in wardrobe_by_id
            ]

            if not valid_items:
                valid_items = wardrobe[:5]  # Fallback to first items

            return {
                "items": valid_items,
                "item_ids": [item["id"] for item in valid_items],
                "reasoning": vlm_response.get("reasoning", ""),
                "confidence": vlm_response.get("confidence", 0.5),
                "weather_compatibility": self._analyze_weather_fit(
                    valid_items, weather_context
                ),
                "style_score": vlm_response.get("style_score", 0.7),
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Error parsing outfit recommendation: {e}")
            raise ResponseParserError(f"Failed to parse outfit: {str(e)}")

    def parse_travel_recommendations(
        self,
        vlm_responses: List[Dict[str, Any]],
        wardrobe: List[Dict[str, Any]],
        weather_forecast: List[Dict[str, Any]],
        num_days: int,
    ) -> Dict[str, Any]:
        """
        Parse travel outfit recommendations.

        Args:
            vlm_responses: List of VLM responses (one per day)
            wardrobe: Available wardrobe items
            weather_forecast: Weather forecast for each day
            num_days: Number of days

        Returns:
            Structured travel plan
        """
        try:
            wardrobe_by_id = {item["id"]: item for item in wardrobe}
            daily_outfits = []
            all_packed_items = set()

            for i, response in enumerate(vlm_responses[:num_days]):
                item_ids = self._extract_item_ids(response)
                valid_items = [
                    wardrobe_by_id[iid] for iid in item_ids if iid in wardrobe_by_id
                ]

                if valid_items:
                    all_packed_items.update(
                        iid for iid in item_ids if iid in wardrobe_by_id
                    )
                    daily_outfits.append(
                        {
                            "day": i + 1,
                            "items": valid_items,
                            "item_ids": [item["id"] for item in valid_items],
                            "weather": weather_forecast[i]
                            if i < len(weather_forecast)
                            else {},
                            "reasoning": response.get("reasoning", ""),
                        }
                    )

            # Get all unique items to pack
            packing_list = [
                wardrobe_by_id[iid] for iid in all_packed_items if iid in wardrobe_by_id
            ]

            return {
                "daily_outfits": daily_outfits,
                "packing_list": packing_list,
                "total_items": len(packing_list),
                "packing_notes": self._generate_packing_notes(packing_list),
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Error parsing travel recommendations: {e}")
            raise ResponseParserError(f"Failed to parse travel plan: {str(e)}")

    def parse_alternative_recommendations(
        self,
        vlm_responses: List[Dict[str, Any]],
        current_outfit: List[Dict[str, Any]],
        wardrobe: List[Dict[str, Any]],
        weather_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Parse alternative outfit recommendations.

        Args:
            vlm_responses: List of VLM responses
            current_outfit: Items in the primary outfit
            wardrobe: Available wardrobe items
            weather_context: Weather data

        Returns:
            List of alternative outfits
        """
        try:
            wardrobe_by_id = {item["id"]: item for item in wardrobe}
            alternatives = []

            for i, response in enumerate(vlm_responses):
                item_ids = self._extract_item_ids(response)
                valid_items = [
                    wardrobe_by_id[iid] for iid in item_ids if iid in wardrobe_by_id
                ]

                if valid_items:
                    alternatives.append(
                        {
                            "alternative_number": i + 1,
                            "items": valid_items,
                            "item_ids": [item["id"] for item in valid_items],
                            "reasoning": response.get("reasoning", ""),
                            "confidence": response.get("confidence", 0.6),
                            "style": response.get("style", "neutral"),
                            "weather_compatibility": self._analyze_weather_fit(
                                valid_items, weather_context
                            ),
                        }
                    )

            return alternatives

        except Exception as e:
            print(f"Error parsing alternatives: {e}")
            raise ResponseParserError(f"Failed to parse alternatives: {str(e)}")

    def _extract_item_ids(self, response: Dict[str, Any]) -> List[str]:
        """
        Extract item IDs from VLM response.

        Handles various response formats:
        - item_ids: [...]
        - outfit_items: [...]
        - selected_items: [...]
        - items: [...]
        """
        # Try different field names
        for field in ["item_ids", "outfit_items", "selected_items", "items"]:
            if field in response and isinstance(response[field], list):
                return response[field]

        # If response contains 'outfit_items' with id field
        if "outfit_items" in response and isinstance(response["outfit_items"], list):
            return [
                item["id"] if isinstance(item, dict) else item
                for item in response["outfit_items"]
            ]

        return []

    def _analyze_weather_fit(
        self, items: List[Dict[str, Any]], weather: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze how well the outfit fits the weather.

        Args:
            items: Selected outfit items
            weather: Weather conditions

        Returns:
            Analysis dictionary
        """
        if not items or not weather:
            return {"score": 0.5, "notes": "Unable to analyze"}

        temp = weather.get("temperature", 20)
        condition = weather.get("condition", "").lower()

        # Check temperature suitability
        temp_min = min(
            item.get("temperature_range", {}).get("min", -10) for item in items
        )
        temp_max = max(
            item.get("temperature_range", {}).get("max", 40) for item in items
        )

        temp_suitable = temp_min <= temp <= temp_max

        # Check weather-specific features
        has_waterproof = (
            any(item.get("waterproof") for item in items)
            if "rain" in condition
            else True
        )
        has_windproof = (
            any(item.get("windproof") for item in items)
            if "wind" in condition
            else True
        )

        score = 0.5
        if temp_suitable:
            score += 0.2
        if has_waterproof:
            score += 0.15
        if has_windproof:
            score += 0.15

        return {
            "score": min(score, 1.0),
            "temperature_suitable": temp_suitable,
            "has_waterproof": has_waterproof,
            "has_windproof": has_windproof,
            "notes": f"Outfit suitable for {temp}°C and {condition} conditions",
        }

    def _generate_packing_notes(self, items: List[Dict[str, Any]]) -> str:
        """
        Generate packing notes based on selected items.

        Args:
            items: Items to pack

        Returns:
            Packing notes string
        """
        if not items:
            return "No items selected for packing"

        types = {}
        for item in items:
            itype = item.get("type", "other")
            types[itype] = types.get(itype, 0) + 1

        notes = f"Packing {len(items)} items: "
        notes += ", ".join(
            f"{count} {itype}{'s' if count > 1 else ''}"
            for itype, count in types.items()
        )
        notes += ". Items can be mixed and matched for multiple outfit combinations."

        return notes

    def _validate_item_id(self, item_id: str, wardrobe: List[Dict[str, Any]]) -> bool:
        """
        Validate that an item ID exists in the wardrobe.

        Args:
            item_id: Item ID to validate
            wardrobe: Available wardrobe items

        Returns:
            True if item exists, False otherwise
        """
        return any(item["id"] == item_id for item in wardrobe)

    def parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from VLM text response.

        Attempts to extract and parse JSON from text that may contain
        extra text before or after the JSON.

        Args:
            response_text: Raw text response from VLM

        Returns:
            Parsed JSON dictionary

        Raises:
            ResponseParserError: If JSON cannot be extracted/parsed
        """
        try:
            # Try direct JSON parse first
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the text
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                json_str = response_text[start_idx : end_idx + 1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try to find JSON array
        start_idx = response_text.find("[")
        end_idx = response_text.rfind("]")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                json_str = response_text[start_idx : end_idx + 1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        raise ResponseParserError(
            f"Could not extract valid JSON from response: {response_text[:100]}"
        )


class ResponseParserError(Exception):
    """Exception raised by ResponseParser."""

    pass
