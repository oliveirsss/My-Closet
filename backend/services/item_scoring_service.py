"""
Item Scoring Service

Scores wardrobe items based on multiple criteria to filter and rank
the best candidates before sending to the AI.

Scoring Criteria:
- Temperature compatibility (warm/cold items match weather)
- Usage frequency (less used items get higher scores)
- Cleanliness (clean items only)
- Style match (formal/casual/sporty preferences)
- Must-include status (mandatory items get very high scores)

Penalties:
- Temperature mismatch
- Overused items
- Excluded items (very negative)
"""

import re
import random
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


class ItemScoringService:
    """
    Scores items to provide the best candidates for outfit recommendations.
    """

    def __init__(self):
        """Initialize the scoring service."""
        self.max_items_per_layer = 5
        self.min_score_to_keep = 25.0
        self.excluded_score = -1000.0

    def score_item(
        self,
        item: Dict[str, Any],
        temperature: float,
        style_preference: Optional[str] = None,
        must_include_ids: Optional[set] = None,
        exclude_ids: Optional[set] = None,
    ) -> float:
        """
        Calculate a comprehensive score for an item.

        Args:
            item: Item dict with id, name, type, layer, temp_min, temp_max, usage_metrics, etc
            temperature: Current temperature in Celsius
            style_preference: Style preference (formal, casual, sporty)
            must_include_ids: Set of item IDs that must be included (high score bonus)
            exclude_ids: Set of item IDs to exclude (heavy penalty)

        Returns:
            Score where higher is better. Dirty/excluded items receive -1000.
        """
        score = 40.0  # Base score

        must_include_ids = must_include_ids or set()
        exclude_ids = exclude_ids or set()
        item_id = item.get("id")

        # ===== PENALTIES (Heavy) =====
        # Excluded items - very negative
        if item_id in exclude_ids:
            return self.excluded_score

        # Dirty or damaged items - exclude completely
        if item.get("status") in {"dirty", "damaged"}:
            return self.excluded_score

        # ===== BONUS (Heavy) =====
        # Must-include items - very high bonus
        if item_id in must_include_ids:
            score += 500.0

        # ===== TEMPERATURE COMPATIBILITY =====
        temperature_range = item.get("temperature_range") or {}
        temp_min = item.get("temp_min", item.get("tempMin", temperature_range.get("min", -10)))
        temp_max = item.get("temp_max", item.get("tempMax", temperature_range.get("max", 40)))
        try:
            temperature = float(temperature)
            temp_min = float(temp_min)
            temp_max = float(temp_max)
        except (TypeError, ValueError):
            temp_min = -10.0
            temp_max = 40.0
        if temp_min > temp_max:
            temp_min, temp_max = temp_max, temp_min

        # Calculate temperature compatibility
        temp_score = self._score_temperature_compatibility(temperature, temp_min, temp_max)
        score += temp_score

        # ===== USAGE FREQUENCY =====
        # Prefer less-used items
        usage_score = self._score_usage_frequency(item.get("usage_metrics"))
        score += usage_score

        # ===== STYLE MATCHING =====
        if style_preference:
            style_score = self._score_style_match(item, style_preference)
            score += style_score

        # ===== LAYER & TYPE APPROPRIATENESS =====
        layer_score = self._score_layer_appropriateness(item)
        score += layer_score

        # ===== FAVORITE STATUS =====
        if item.get("favorite"):
            score += 5.0

        return score

    def _score_temperature_compatibility(self, current_temp: float, min_temp: float, max_temp: float) -> float:
        """
        Score how well an item matches the current temperature.

        Returns score between -80 and +35.
        """
        # Perfect match: temperature is within the item's range
        if min_temp <= current_temp <= max_temp:
            return 35.0

        # Acceptable: temperature is close to the range
        if min_temp - 5 <= current_temp <= max_temp + 5:
            return 10.0

        # Outside acceptable range
        distance_below = min_temp - 5 - current_temp if current_temp < min_temp - 5 else 0
        distance_above = current_temp - (max_temp + 5) if current_temp > max_temp + 5 else 0
        max_distance = max(distance_below, distance_above)

        if max_distance > 0:
            # Penalize based on distance from acceptable range
            penalty = min(80.0, 20.0 + max_distance * 4)
            return -penalty

        return 0.0

    def _score_usage_frequency(self, usage_metrics: Optional[Dict[str, Any]]) -> float:
        """
        Score based on how often an item has been used recently.

        Prefer less-used items. Returns score between -40 and +20.
        """
        if not usage_metrics:
            return 0.0

        recent_usage = usage_metrics.get("usage_frequency_last_7_days", 0) or 0
        monthly_usage = usage_metrics.get("usage_frequency_last_30_days", 0) or 0
        is_overused = usage_metrics.get("is_overused", False)

        if is_overused or monthly_usage >= 10:
            overuse_penalty = min(40.0, 25.0 + max(0, recent_usage - 3) * 3)
            return -overuse_penalty

        # Map usage frequency to score:
        # 0 uses -> +20 (best)
        # 1-2 uses -> +15
        # 3-4 uses -> +5
        # 5-6 uses -> -10
        # 7+ uses -> stronger penalty

        if recent_usage == 0:
            return 20.0
        elif recent_usage <= 2:
            return 15.0
        elif recent_usage <= 4:
            return 5.0
        elif recent_usage <= 6:
            return -10.0
        else:
            # Heavily penalize overused items
            overuse_penalty = min(40.0, 15.0 + (recent_usage - 6) * 5)
            return -overuse_penalty

    def _score_style_match(self, item: Dict[str, Any], style_preference: str) -> float:
        """
        Score based on style match. Returns meaningful boosts and penalties.
        """
        if not style_preference:
            return 0.0

        if isinstance(style_preference, list):
            style_preference = " ".join(str(style) for style in style_preference)

        style_preference_lower = self._normalize_text(style_preference)
        item_style = self._normalize_text(
            " ".join(
                str(value)
                for value in [item.get("style"), item.get("occasion")]
                if value
            )
        )
        searchable_text = self._normalize_text(
            " ".join(
                str(value)
                for value in [
                    item.get("name", ""),
                    item.get("type", ""),
                    item.get("style", ""),
                    item.get("occasion", ""),
                    " ".join(str(material) for material in item.get("materials", []) or []),
                ]
            )
        )

        requested_styles = [
            style
            for style in ("formal", "casual", "sporty")
            if style in style_preference_lower
        ]
        if not requested_styles:
            return 0.0

        score = 0.0
        profiles = {
            "formal": {
                "boost": [
                    "formal",
                    "camisa",
                    "shirt",
                    "blazer",
                    "coat",
                    "casaco",
                    "jacket",
                    "suit",
                    "oxford",
                    "loafer",
                    "trouser",
                    "trousers",
                    "calcas formais",
                    "calca formal",
                    "chino",
                    "slacks",
                    "work",
                    "office",
                    "business",
                    "elegant",
                ],
                "penalty": [
                    "jersey",
                    "t-shirt",
                    "tshirt",
                    "tee",
                    "sneaker",
                    "sneakers",
                    "sapatilhas",
                    "tenis",
                    "sportswear",
                    "sport",
                    "sporty",
                    "desportivo",
                    "hoodie",
                    "sweatshirt",
                    "gym",
                    "athletic",
                ],
            },
            "casual": {
                "boost": [
                    "casual",
                    "t-shirt",
                    "tshirt",
                    "tee",
                    "hoodie",
                    "sweatshirt",
                    "sneaker",
                    "sneakers",
                    "sapatilhas",
                    "tenis",
                    "jeans",
                    "denim",
                    "daily",
                    "everyday",
                ],
                "penalty": ["suit", "blazer", "formal", "oxford", "business"],
            },
            "sporty": {
                "boost": [
                    "sport",
                    "sporty",
                    "desportivo",
                    "athletic",
                    "gym",
                    "active",
                    "training",
                    "sneaker",
                    "sneakers",
                ],
                "penalty": ["suit", "blazer", "formal", "oxford"],
            },
        }

        for requested_style in requested_styles:
            profile = profiles[requested_style]

            if item_style and requested_style in item_style:
                score += 45.0

            if any(self._keyword_present(searchable_text, keyword) for keyword in profile["boost"]):
                score += 60.0 if requested_style == "formal" else 30.0

            if any(self._keyword_present(searchable_text, keyword) for keyword in profile["penalty"]):
                score -= 90.0 if requested_style == "formal" else 35.0

            if not item_style and not any(
                self._keyword_present(searchable_text, keyword)
                for keyword in profile["boost"]
            ):
                score -= 8.0

        return score

    def _keyword_present(self, text: str, keyword: str) -> bool:
        keyword = self._normalize_text(keyword)
        if not keyword:
            return False

        if keyword == "shirt":
            return re.search(r"(?<!t[-\s])\bshirt\b", text) is not None

        if " " in keyword or "-" in keyword:
            return keyword in text

        return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None

    def _normalize_text(self, value: Any) -> str:
        text = str(value or "")
        decomposed = unicodedata.normalize("NFD", text)
        without_accents = "".join(
            char for char in decomposed if unicodedata.category(char) != "Mn"
        )
        return without_accents.lower().strip()

    def _score_layer_appropriateness(self, item: Dict[str, Any]) -> float:
        """
        Score based on layer appropriateness. Returns score between -5 and +5.
        """
        layer = item.get("layer", 1)
        item_type = (item.get("type") or "").lower()

        # Verify type matches layer expectation
        if layer == 1:  # Base layer
            base_types = ["t-shirt", "shirt", "top", "blouse", "camiseta", "camisa"]
            if any(t in item_type for t in base_types):
                return 5.0

        elif layer == 2:  # Insulation layer
            insulation_types = ["sweater", "hoodie", "cardigan", "pants", "jeans", "trousers"]
            if any(t in item_type for t in insulation_types):
                return 5.0

        elif layer == 3:  # Outer layer
            outer_types = ["jacket", "coat", "shoes", "boots", "accessories"]
            if any(t in item_type for t in outer_types):
                return 5.0

        return 0.0

    def score_and_filter_items(
        self,
        wardrobe: List[Dict[str, Any]],
        temperature: float,
        style_preference: Optional[str] = None,
        must_include_ids: Optional[List[str]] = None,
        exclude_ids: Optional[List[str]] = None,
        max_per_layer: int = 5,
        min_score: Optional[float] = None,
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Score all items and filter to keep only top candidates per layer.

        Args:
            wardrobe: Full wardrobe list
            temperature: Current temperature
            style_preference: Style preference
            must_include_ids: IDs that must be included
            exclude_ids: IDs to exclude
            max_per_layer: Maximum items to keep per layer
            min_score: Minimum score for normal candidates

        Returns:
            Dict mapping layer -> list of scored items (sorted by score desc)
        """
        must_include_set = set(must_include_ids or [])
        exclude_set = set(exclude_ids or [])
        min_score = self.min_score_to_keep if min_score is None else min_score

        # Score all items
        scored_items: List[Tuple[Dict[str, Any], float]] = []

        for item in wardrobe:
            score = self.score_item(
                item,
                temperature,
                style_preference,
                must_include_set,
                exclude_set,
            )
            item_id = item.get("id")

            # Dirty and explicitly excluded items never reach the AI.
            if score <= self.excluded_score:
                continue

            # Keep strong candidates and valid mandatory items.
            if score >= min_score or item_id in must_include_set:
                scored_items.append((item, score))

        # Organize by layer
        by_layer: Dict[int, List[Tuple[Dict[str, Any], float]]] = {}
        for item, score in scored_items:
            layer = item.get("layer", 1)
            if layer not in by_layer:
                by_layer[layer] = []
            by_layer[layer].append((item, score))

        # Sort each layer by score (descending) and keep top N
        result: Dict[int, List[Dict[str, Any]]] = {}
        for layer in sorted(by_layer.keys()):
            # Sort by score descending
            sorted_layer = sorted(by_layer[layer], key=lambda x: x[1], reverse=True)

            # Ensure must-include items are kept even if not in top N
            must_include_items = [
                (item, score) for item, score in sorted_layer
                if item.get("id") in must_include_set
            ]
            other_items = [
                (item, score) for item, score in sorted_layer
                if item.get("id") not in must_include_set
            ]

            # Keep all must-include items + a randomized slice from the top 3-5 candidates.
            remaining_slots = max(0, max_per_layer - len(must_include_items))
            candidate_pool_size = min(len(other_items), max(remaining_slots, 5))
            candidate_pool = other_items[:candidate_pool_size]
            random.shuffle(candidate_pool)
            kept_items = must_include_items + candidate_pool[:remaining_slots]
            kept_items = sorted(kept_items, key=lambda x: x[1], reverse=True)

            # Add score to each item
            items_with_scores = [
                {**item, "score": round(score, 1)}
                for item, score in kept_items
            ]

            result[layer] = items_with_scores

        return result

    def format_items_for_prompt(
        self,
        scored_items: Dict[int, List[Dict[str, Any]]],
    ) -> Dict[int, List[str]]:
        """
        Format scored items for inclusion in the AI prompt.

        Each item includes: ID, Name, Type, Score

        Args:
            scored_items: Dict from score_and_filter_items

        Returns:
            Dict mapping layer -> list of formatted item strings
        """
        result: Dict[int, List[str]] = {}

        for layer, items in scored_items.items():
            formatted = []
            for item in items:
                item_id = item.get("id", "?")
                name = item.get("name", "Unknown")
                item_type = item.get("type", "")
                score = item.get("score", 0)
                
                # Format: ID: name (type) - Score: X
                formatted_str = f"ID: {item_id}, Name: {name}, Type: {item_type}, Score: {score:.0f}"
                formatted.append(formatted_str)

            result[layer] = formatted

        return result

    def get_item_diversity_metrics(
        self,
        wardrobe: List[Dict[str, Any]],
        recent_outfits: List[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get metrics about wardrobe diversity and usage.

        Args:
            wardrobe: Full wardrobe
            recent_outfits: List of recent outfit item lists

        Returns:
            Metrics dict with diversity info
        """
        recent_outfits = recent_outfits or []

        # Count frequency of each item in recent outfits
        item_frequency = {}
        for outfit in recent_outfits:
            for item_id in outfit:
                item_frequency[item_id] = item_frequency.get(item_id, 0) + 1

        # Find overused items
        overused = [item_id for item_id, count in item_frequency.items() if count > 3]

        # Find unused items
        unused = [
            item.get("id") for item in wardrobe
            if item.get("id") not in item_frequency
        ]

        return {
            "total_items": len(wardrobe),
            "overused_items": overused,
            "unused_items": unused,
            "item_frequency": item_frequency,
        }
