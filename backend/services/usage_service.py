"""
Usage Frequency Service

Handles tracking and computing usage frequency of clothing items:
- Fetch usage history for items
- Compute usage scores/frequencies
- Identify favorite/frequently-worn items
- Support filtering by date range
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import supabase


class UsageService:
    """Service for managing clothing item usage frequency."""

    def __init__(self):
        """Initialize usage service."""
        self.supabase = supabase

    async def get_item_usage_count(
        self, user_id: str, item_id: str, days: Optional[int] = None
    ) -> int:
        """
        Get the number of times an item has been used.

        Args:
            user_id: The user's ID
            item_id: The item's ID
            days: If provided, only count usage in the last N days

        Returns:
            Number of times the item was used
        """
        try:
            # Phase 1: Mock implementation - usage_history table may not exist yet
            # Query usage history table (will be created in Phase 2)
            query = (
                self.supabase.table("usage_history")
                .select("id")
                .eq("user_id", user_id)
                .eq("clothing_id", item_id)
            )

            if days:
                cutoff_date = (datetime.now() - timedelta(days=days or 30)).isoformat()
                query = query.gte("worn_date", cutoff_date)

            response = query.execute()
            return len(response.data) if response.data else 0

        except Exception as e:
            # Phase 1: Table doesn't exist yet, return 0
            print(f"Info: Usage history not available (Phase 1): {e}")
            return 0

    async def get_user_item_usage_frequency(
        self, user_id: str, days: Optional[int] = 30
    ) -> Dict[str, float]:
        """
        Get usage frequency for all of a user's items.

        Returns a normalized score from 0.0 to 1.0 for each item.

        Args:
            user_id: The user's ID
            days: How many days of history to consider (default 30)

        Returns:
            Dictionary mapping item_id -> usage_frequency_score (0.0-1.0)
        """
        try:
            # Fetch all items for the user
            items_response = (
                self.supabase.table("clothes")
                .select("id")
                .eq("user_id", user_id)
                .execute()
            )
            item_ids = (
                [item["id"] for item in items_response.data]
                if items_response.data
                else []
            )

            if not item_ids:
                return {}

            try:
                # Fetch usage history for all items
                cutoff_date = (datetime.now() - timedelta(days=days or 30)).isoformat()
                usage_response = (
                    self.supabase.table("usage_history")
                    .select("clothing_id")
                    .eq("user_id", user_id)
                    .gte("worn_date", cutoff_date)
                    .execute()
                )

                # Count usage per item
                usage_counts = {}
                for usage in usage_response.data if usage_response.data else []:
                    item_id = usage["clothing_id"]
                    usage_counts[item_id] = usage_counts.get(item_id, 0) + 1

                # Normalize scores
                max_usage = max(usage_counts.values()) if usage_counts else 1
                normalized_scores = {}

                for item_id in item_ids:
                    count = usage_counts.get(item_id, 0)
                    normalized_scores[item_id] = (
                        min(count / max_usage, 1.0) if max_usage > 0 else 0.0
                    )

                return normalized_scores

            except Exception as e:
                # Phase 1: Table doesn't exist yet, return empty dict
                print(f"Info: Usage history not available (Phase 1): {e}")
                return {}

        except Exception as e:
            print(f"Error getting usage frequency for user {user_id}: {e}")
            return {}

    async def record_outfit_usage(
        self, user_id: str, item_ids: List[str], occasion: Optional[str] = None
    ) -> bool:
        """
        Record that a set of items were used together as an outfit.

        Args:
            user_id: The user's ID
            item_ids: List of item IDs used
            occasion: Optional occasion/context for the outfit

        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            timestamp = datetime.now().isoformat()

            # Phase 1: Table doesn't exist yet, just log
            # Record each item as used
            for item_id in item_ids:
                try:
                    self.supabase.table("usage_history").insert(
                        {
                            "user_id": user_id,
                            "clothing_id": item_id,
                            "worn_date": timestamp,
                            "weather_condition": occasion,
                        }
                    ).execute()
                except Exception as e:
                    # Phase 1: Table doesn't exist, skip
                    print(f"Info: Could not record usage (Phase 1): {e}")
                    continue

            return True

        except Exception as e:
            print(f"Error recording outfit usage: {e}")
            return False

    async def get_most_used_items(
        self, user_id: str, limit: int = 10, days: Optional[int] = 30
    ) -> List[Dict[str, Any]]:
        """
        Get the user's most frequently used items.

        Args:
            user_id: The user's ID
            limit: Maximum number of items to return
            days: Only consider usage in the last N days

        Returns:
            List of items sorted by usage frequency (most used first)
        """
        try:
            usage_freq = await self.get_user_item_usage_frequency(user_id, days)

            if not usage_freq:
                # Phase 1: Return all items as having equal frequency
                items_response = (
                    self.supabase.table("clothes")
                    .select("*")
                    .eq("user_id", user_id)
                    .limit(limit)
                    .execute()
                )

                result = []
                if items_response.data:
                    for item in items_response.data:
                        result.append(
                            {
                                "id": item.get("id"),
                                "name": item.get("name"),
                                "type": item.get("type"),
                                "usage_frequency": 0.5,  # Default for Phase 1
                                "usage_count": 0,
                            }
                        )
                return result

            # Sort by usage frequency
            sorted_items = sorted(usage_freq.items(), key=lambda x: x[1], reverse=True)

            # Fetch item details
            result = []
            for item_id, frequency in sorted_items[:limit]:
                item_response = (
                    self.supabase.table("clothes")
                    .select("*")
                    .eq("id", item_id)
                    .execute()
                )
                if item_response.data:
                    item = item_response.data[0]
                    result.append(
                        {
                            "id": item_id,
                            "name": item.get("name"),
                            "type": item.get("type"),
                            "usage_frequency": frequency,
                            "usage_count": await self.get_item_usage_count(
                                user_id, item_id, days
                            ),
                        }
                    )

            return result

        except Exception as e:
            print(f"Error getting most used items: {e}")
            return []

    async def get_unused_items(
        self, user_id: str, days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get items that haven't been used recently.

        Useful for recommendations to encourage wearing less-used items.

        Args:
            user_id: The user's ID
            days: Items unused for more than this many days

        Returns:
            List of unused items
        """
        try:
            # Get all clean items
            all_items = (
                self.supabase.table("clothes")
                .select("id, name, type")
                .eq("user_id", user_id)
                .eq("status", "clean")
                .execute()
            )

            if not all_items.data:
                return []

            try:
                # Get recently used items
                cutoff_date = (datetime.now() - timedelta(days=days or 30)).isoformat()
                used_recently = (
                    self.supabase.table("usage_history")
                    .select("clothing_id")
                    .eq("user_id", user_id)
                    .gte("worn_date", cutoff_date)
                    .execute()
                )

                used_item_ids = (
                    set(usage["clothing_id"] for usage in used_recently.data)
                    if used_recently.data
                    else set()
                )

                # Return items not in the recently-used set
                unused = [
                    item for item in all_items.data if item["id"] not in used_item_ids
                ]

                return [
                    {
                        "id": item["id"],
                        "name": item.get("name"),
                        "type": item.get("type"),
                    }
                    for item in unused
                ]

            except Exception as e:
                # Phase 1: Table doesn't exist, return all items as unused
                print(f"Info: Usage history not available (Phase 1): {e}")
                return [
                    {
                        "id": item["id"],
                        "name": item.get("name"),
                        "type": item.get("type"),
                    }
                    for item in all_items.data
                ]

        except Exception as e:
            print(f"Error getting unused items: {e}")
            return []


class UsageServiceError(Exception):
    """Exception raised by UsageService."""

    pass
