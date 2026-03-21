"""
Wardrobe Service

This module handles all wardrobe-related operations for the AI recommendation system.
It acts as an intermediary between the database and the recommendation pipeline,
providing clean methods to fetch, filter, and format wardrobe data.

Responsibilities:
- Fetch user's wardrobe items from the database
- Filter items based on status (clean/dirty), availability, etc.
- Format items for VLM consumption (include image URLs, metadata)
- Handle missing or invalid items gracefully
"""

from typing import Any, Dict, List, Optional

from database import supabase


class WardrobeService:
    """
    Service for managing wardrobe operations.

    Provides methods to retrieve and format wardrobe data for use
    in the outfit recommendation pipeline.
    """

    def __init__(self):
        """Initialize the wardrobe service."""
        self.supabase = supabase

    async def get_user_wardrobe(
        self,
        user_id: str,
        only_clean: bool = True,
        exclude_item_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all wardrobe items for a user.

        Args:
            user_id: The user's unique identifier
            only_clean: If True, only return items with status='clean'
            exclude_item_ids: List of item IDs to exclude from results

        Returns:
            List of wardrobe items formatted for the recommendation pipeline

        Raises:
            WardrobeServiceError: If database query fails
        """
        try:
            # Build the query
            query = self.supabase.table("clothes").select("*").eq("user_id", user_id)

            # Filter by status if needed
            if only_clean:
                query = query.eq("status", "clean")

            response = query.execute()
            items = response.data if response.data else []

            # Filter out excluded items
            if exclude_item_ids:
                items = [item for item in items if item["id"] not in exclude_item_ids]

            # Format items for the recommendation pipeline
            formatted_items = [self._format_item(item) for item in items]

            return formatted_items

        except Exception as e:
            raise WardrobeServiceError(
                f"Failed to fetch wardrobe for user {user_id}: {str(e)}"
            )

    async def get_item_by_id(
        self, item_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific wardrobe item by ID.

        Args:
            item_id: The item's unique identifier
            user_id: Optional user ID to verify ownership

        Returns:
            Formatted item data or None if not found

        Raises:
            WardrobeServiceError: If database query fails
        """
        try:
            query = self.supabase.table("clothes").select("*").eq("id", item_id)

            if user_id:
                query = query.eq("user_id", user_id)

            response = query.execute()

            if not response.data:
                return None

            return self._format_item(response.data[0])

        except Exception as e:
            raise WardrobeServiceError(f"Failed to fetch item {item_id}: {str(e)}")

    async def get_items_by_type(
        self,
        user_id: str,
        item_type: str,
        only_clean: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetch wardrobe items filtered by type.

        Args:
            user_id: The user's unique identifier
            item_type: The type of clothing (e.g., 'shirt', 'pants', 'jacket')
            only_clean: If True, only return clean items

        Returns:
            List of wardrobe items of the specified type

        Raises:
            WardrobeServiceError: If database query fails
        """
        try:
            query = (
                self.supabase.table("clothes")
                .select("*")
                .eq("user_id", user_id)
                .eq("type", item_type)
            )

            if only_clean:
                query = query.eq("status", "clean")

            response = query.execute()
            items = response.data if response.data else []

            return [self._format_item(item) for item in items]

        except Exception as e:
            raise WardrobeServiceError(
                f"Failed to fetch {item_type} items for user {user_id}: {str(e)}"
            )

    async def get_favorite_items(
        self,
        user_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch user's favorite wardrobe items.

        Useful for giving higher priority to items the user likes.

        Args:
            user_id: The user's unique identifier
            limit: Maximum number of items to return

        Returns:
            List of user's favorite items

        Raises:
            WardrobeServiceError: If database query fails
        """
        try:
            query = (
                self.supabase.table("clothes")
                .select("*")
                .eq("user_id", user_id)
                .eq("favorite", True)
                .eq("status", "clean")
            )

            response = query.execute()
            items = response.data if response.data else []

            if limit:
                items = items[:limit]

            return [self._format_item(item) for item in items]

        except Exception as e:
            raise WardrobeServiceError(
                f"Failed to fetch favorite items for user {user_id}: {str(e)}"
            )

    async def get_items_by_temperature_range(
        self,
        user_id: str,
        temp_min: float,
        temp_max: float,
        only_clean: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetch wardrobe items suitable for a temperature range.

        Args:
            user_id: The user's unique identifier
            temp_min: Minimum temperature in Celsius
            temp_max: Maximum temperature in Celsius
            only_clean: If True, only return clean items

        Returns:
            List of items suitable for the temperature range

        Raises:
            WardrobeServiceError: If database query fails
        """
        try:
            # Fetch all items and filter by temperature range
            # (Supabase doesn't support complex range queries easily)
            query = self.supabase.table("clothes").select("*").eq("user_id", user_id)

            if only_clean:
                query = query.eq("status", "clean")

            response = query.execute()
            items = response.data if response.data else []

            # Filter by temperature range
            suitable_items = [
                item
                for item in items
                if self._is_item_suitable_for_temp(item, temp_min, temp_max)
            ]

            return [self._format_item(item) for item in suitable_items]

        except Exception as e:
            raise WardrobeServiceError(
                f"Failed to fetch items for temperature range {temp_min}-{temp_max}: {str(e)}"
            )

    def _format_item(self, db_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a raw database item for use in the recommendation pipeline.

        Args:
            db_item: Raw item data from the database

        Returns:
            Formatted item with all necessary fields for recommendations
        """
        return {
            "id": db_item.get("id"),
            "name": db_item.get("name", "Unknown Item"),
            "type": db_item.get("type", ""),
            "brand": db_item.get("brand", ""),
            "size": db_item.get("size", ""),
            "layer": db_item.get("layer", 1),
            "materials": db_item.get("materials", []),
            "weight": db_item.get("weight", 0),
            "image_url": db_item.get("image", ""),
            "status": db_item.get("status", "clean"),
            "favorite": db_item.get("favorite", False),
            "waterproof": db_item.get("waterproof", False),
            "windproof": db_item.get("windproof", False),
            "seasons": db_item.get("seasons", []),
            "temperature_range": {
                "min": db_item.get("temp_min", -10),
                "max": db_item.get("temp_max", 30),
            },
            "color": db_item.get("color", ""),
            "metadata": {
                "created_at": db_item.get("created_at"),
                "updated_at": db_item.get("updated_at"),
            },
        }

    def _is_item_suitable_for_temp(
        self,
        item: Dict[str, Any],
        temp_min: float,
        temp_max: float,
    ) -> bool:
        """
        Check if an item is suitable for a temperature range.

        Args:
            item: The clothing item
            temp_min: Minimum temperature
            temp_max: Maximum temperature

        Returns:
            True if the item is suitable for the temperature range
        """
        item_temp_min = item.get("temp_min", -10)
        item_temp_max = item.get("temp_max", 30)

        # Item is suitable if its range overlaps with the required range
        return item_temp_min <= temp_max and item_temp_max >= temp_min


class WardrobeServiceError(Exception):
    """Exception raised by WardrobeService."""

    pass
