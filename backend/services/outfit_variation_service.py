"""
Outfit Variation Service

Ensures AI doesn't always return the same outfit by:
- Tracking recently used items
- Prioritizing less-used items
- Randomizing candidate selection
- Excluding previous outfit items on request
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple


class OutfitVariationService:
    """
    Manages outfit variation to prevent repetition.
    """

    def __init__(self, max_history_days: int = 7):
        """
        Initialize the variation service.

        Args:
            max_history_days: How many days of history to consider for variation
        """
        self.max_history_days = max_history_days

    def calculate_item_diversity_score(
        self,
        item_id: str,
        usage_metrics: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate a diversity score for an item (higher = better to use).

        Lower usage frequency = higher diversity score.

        Args:
            item_id: ID of the item
            usage_metrics: Item's usage metrics dict

        Returns:
            Diversity score (0-100)
        """
        if not usage_metrics:
            return 50.0  # Default middle score for unknown items

        # Get usage frequency in last 7 days
        recent_usage = usage_metrics.get("usage_frequency_last_7_days", 0)
        
        # Convert to score: 0 usage = 100 score, 7+ usage = 0 score
        if recent_usage >= 7:
            return 0.0
        
        # Linear scale: fewer uses = higher score
        score = (1 - (recent_usage / 7)) * 100
        return max(0.0, min(100.0, score))

    def score_items_for_variation(
        self,
        items: List[Dict[str, Any]],
        exclude_item_ids: Optional[Set[str]] = None,
    ) -> List[Tuple[str, float]]:
        """
        Score items based on diversity (less used items get higher scores).

        Args:
            items: List of wardrobe items
            exclude_item_ids: IDs to exclude from scoring

        Returns:
            List of (item_id, score) tuples sorted by score descending
        """
        exclude_item_ids = exclude_item_ids or set()
        scored = []

        for item in items:
            item_id = item.get("id")
            if item_id in exclude_item_ids:
                continue

            score = self.calculate_item_diversity_score(
                item_id,
                item.get("usage_metrics")
            )
            scored.append((item_id, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def add_variation_to_exclude_items(
        self,
        current_exclude_items: Optional[List[str]],
        recent_outfits: List[List[str]],
        max_items_to_exclude: int = 5,
    ) -> List[str]:
        """
        Add recently used items to exclude list for more variation.

        Args:
            current_exclude_items: Already excluded item IDs
            recent_outfits: List of recent outfit item lists (last N days)
            max_items_to_exclude: Maximum items to add to exclude list

        Returns:
            Updated exclude list
        """
        current_exclude_items = set(current_exclude_items or [])

        if not recent_outfits:
            return list(current_exclude_items)

        # Flatten all recent outfits
        all_recent_items = []
        for outfit in recent_outfits:
            all_recent_items.extend(outfit)

        # Count frequency of each item
        item_frequency = {}
        for item_id in all_recent_items:
            item_frequency[item_id] = item_frequency.get(item_id, 0) + 1

        # Sort by frequency and add to exclude (most frequent first)
        sorted_items = sorted(
            item_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )

        items_added = 0
        for item_id, frequency in sorted_items:
            if items_added >= max_items_to_exclude:
                break
            if item_id not in current_exclude_items:
                current_exclude_items.add(item_id)
                items_added += 1

        return list(current_exclude_items)

    def randomize_candidate_selection(
        self,
        candidates: List[Dict[str, Any]],
        selection_count: int = 3,
        prefer_diversity: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Randomize candidate selection with optional diversity preference.

        Args:
            candidates: Available candidate items
            selection_count: Number of items to select
            prefer_diversity: If True, prioritize less-used items

        Returns:
            Selected items
        """
        if len(candidates) <= selection_count:
            return candidates

        if prefer_diversity:
            # Score by usage and randomize top candidates
            scored = self.score_items_for_variation(candidates)
            candidates_by_id = {item.get("id"): item for item in candidates}
            
            # Take top candidates but randomize selection
            top_candidates = [
                candidates_by_id[item_id]
                for item_id, _ in scored[:selection_count * 2]
                if item_id in candidates_by_id
            ]
            selected = random.sample(top_candidates, min(selection_count, len(top_candidates)))
            return selected
        else:
            # Simple random selection
            return random.sample(candidates, min(selection_count, len(candidates)))

    def build_exclude_strategy(
        self,
        user_id: str,
        current_exclude_items: Optional[List[str]] = None,
        enable_variation: bool = True,
    ) -> List[str]:
        """
        Build the exclude items list considering variation strategy.

        Args:
            user_id: User ID (for future caching)
            current_exclude_items: Already excluded items
            enable_variation: Whether to enable variation logic

        Returns:
            Final exclude items list
        """
        if not enable_variation:
            return current_exclude_items or []

        # In a real implementation, fetch recent outfits from database
        # For now, just return the current exclude items
        return current_exclude_items or []
