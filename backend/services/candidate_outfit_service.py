"""
Candidate Outfit Service

Builds deterministic complete outfit candidates before any visual AI selection.
This service does not call LLaVA. It only groups wardrobe items, enforces hard
user constraints, and returns valid candidate outfit combinations for debugging
or later visual ranking.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import unicodedata


COLOR_ALIASES = {
    "amarelo": "yellow",
    "amarela": "yellow",
    "amarelas": "yellow",
    "amarelos": "yellow",
    "yellow": "yellow",
    "azul": "blue",
    "azuis": "blue",
    "blue": "blue",
    "verde": "green",
    "verdes": "green",
    "green": "green",
    "preto": "black",
    "preta": "black",
    "pretas": "black",
    "pretos": "black",
    "black": "black",
    "branco": "white",
    "branca": "white",
    "brancas": "white",
    "brancos": "white",
    "white": "white",
    "vermelho": "red",
    "vermelha": "red",
    "vermelhas": "red",
    "vermelhos": "red",
    "red": "red",
    "cinza": "gray",
    "cinzas": "gray",
    "cinzento": "gray",
    "cinzenta": "gray",
    "cinzentos": "gray",
    "cinzentas": "gray",
    "gray": "gray",
    "grey": "gray",
    "castanho": "brown",
    "castanha": "brown",
    "castanhos": "brown",
    "castanhas": "brown",
    "brown": "brown",
    "bege": "beige",
    "beges": "beige",
    "beige": "beige",
    "rosa": "pink",
    "rosas": "pink",
    "pink": "pink",
    "roxo": "purple",
    "roxa": "purple",
    "roxos": "purple",
    "roxas": "purple",
    "purple": "purple",
    "laranja": "orange",
    "laranjas": "orange",
    "orange": "orange",
}


TYPE_ALIASES = {
    "calcado": "shoes",
    "calçado": "shoes",
    "sapatilha": "shoes",
    "sapatilhas": "shoes",
    "tenis": "shoes",
    "ténis": "shoes",
    "sneaker": "shoes",
    "sneakers": "shoes",
    "shoe": "shoes",
    "shoes": "shoes",
    "sapato": "shoes",
    "sapatos": "shoes",
    "bota": "shoes",
    "botas": "shoes",
    "casaco": "outer_layer",
    "casacos": "outer_layer",
    "jacket": "outer_layer",
    "coat": "outer_layer",
    "blazer": "outer_layer",
    "sobretudo": "outer_layer",
    "calca": "pants",
    "calcas": "pants",
    "calça": "pants",
    "calças": "pants",
    "pants": "pants",
    "trousers": "pants",
    "jeans": "pants",
    "calcoes": "pants",
    "calções": "pants",
    "shorts": "pants",
    "tshirt": "base_layer",
    "t-shirt": "base_layer",
    "camiseta": "base_layer",
    "camisa": "base_layer",
    "shirt": "base_layer",
    "top": "base_layer",
    "blusa": "base_layer",
    "blouse": "base_layer",
    "jersey": "base_layer",
    "camisola": "insulation_layer",
    "sweater": "insulation_layer",
    "hoodie": "insulation_layer",
    "knit": "insulation_layer",
    "malha": "insulation_layer",
    "sweatshirt": "insulation_layer",
    "cardigan": "insulation_layer",
    "vestido": "base_layer",
    "dress": "base_layer",
    "acessorio": "accessories",
    "acessorios": "accessories",
    "acessório": "accessories",
    "acessórios": "accessories",
    "accessory": "accessories",
    "accessories": "accessories",
    "cinto": "accessories",
    "belt": "accessories",
    "gravata": "accessories",
    "tie": "accessories",
    "lenco": "accessories",
    "lenço": "accessories",
    "scarf": "accessories",
    "bone": "accessories",
    "boné": "accessories",
    "hat": "accessories",
    "cap": "accessories",
}


SECTION_ORDER = [
    "base_layer",
    "insulation_layer",
    "pants",
    "outer_layer",
    "shoes",
    "accessories",
]
REQUIRED_SECTIONS = ["base_layer", "pants", "shoes"]

NEUTRAL_COLORS = {"black", "white", "gray", "grey", "beige", "brown", "navy", "blue"}
STRONG_COLORS = {"yellow", "red", "green", "pink", "purple", "orange"}
FORMALITY_BY_STYLE = {
    "sporty": 1,
    "sport": 1,
    "desportivo": 1,
    "streetwear": 1,
    "casual": 2,
    "daily": 2,
    "dia a dia": 2,
    "comfortable": 2,
    "confortavel": 2,
    "smart casual": 3,
    "smart_casual": 3,
    "classic": 4,
    "classico": 4,
    "classica": 4,
    "formal": 5,
    "elegant": 5,
    "elegante": 5,
}
OCCASION_STYLE_FIT = {
    "work": {"formal", "classic", "smart casual", "elegant"},
    "trabalho": {"formal", "classic", "smart casual", "elegant"},
    "dinner": {"smart casual", "classic", "formal", "elegant"},
    "jantar": {"smart casual", "classic", "formal", "elegant"},
    "daily": {"casual", "streetwear", "smart casual"},
    "dia a dia": {"casual", "streetwear", "smart casual"},
    "sport": {"sporty"},
    "desporto": {"sporty"},
    "night": {"streetwear", "smart casual", "elegant"},
    "noite": {"streetwear", "smart casual", "elegant"},
    "sair": {"streetwear", "smart casual", "elegant"},
}


@dataclass
class CandidateOutfit:
    candidate_id: str
    items: List[Dict[str, Any]]
    item_ids: List[str]
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "items": self.items,
            "item_ids": self.item_ids,
            "score": round(self.score, 3),
            "metadata": self.metadata,
        }


class CandidateOutfitService:
    """Generate deterministic candidate outfits from wardrobe items."""

    def generate_candidate_outfits(
        self,
        user_id: str,
        wardrobe_items: List[Dict[str, Any]],
        weather: Optional[Dict[str, Any]],
        parsed_intent: Optional[Dict[str, Any]],
        current_outfit_items: Optional[List[str]] = None,
        exclude_items: Optional[List[str]] = None,
        max_candidates: int = 5,
    ) -> Dict[str, Any]:
        weather = weather or {}
        parsed_intent = parsed_intent or {}
        current_outfit_items = current_outfit_items or []
        exclude_items = exclude_items or []
        rejected_candidates: List[Dict[str, Any]] = []

        print(f"[CandidateOutfit] parsed_intent={parsed_intent}")
        self._log_wardrobe(user_id, wardrobe_items)

        clean_items = self.filter_clean_items(wardrobe_items)
        excluded_ids = set(exclude_items or [])
        if excluded_ids:
            clean_items = [
                item for item in clean_items if str(item.get("id")) not in excluded_ids
            ]

        temp_items, used_temp_filter = self.filter_temperature_compatible(
            clean_items,
            weather,
        )

        grouped_all = self._group_by_section(clean_items)
        grouped_temp = self._group_by_section(temp_items)
        grouped = grouped_temp if self._has_required_sections(grouped_temp) else grouped_all
        if not self._has_required_sections(grouped_temp):
            used_temp_filter = False

        print(f"[CandidateOutfit] grouped_items={self._debug_grouped(grouped)}")

        must_include_result = self.find_must_include_items(
            grouped_items=grouped,
            clean_items=clean_items,
            parsed_intent=parsed_intent,
            excluded_ids=excluded_ids,
        )
        if must_include_result.get("error"):
            print(f"[CandidateOutfit] must_include_error={must_include_result['error']}")
            return {
                "success": False,
                "error": must_include_result["error"],
                "parsed_intent": parsed_intent,
                "must_include_items": [],
                "candidates": [],
                "debug": {
                    "grouped_items": self._debug_grouped(grouped),
                    "rejected_candidates": rejected_candidates,
                },
            }

        must_include_items = must_include_result["items"]
        self._force_must_include_into_groups(grouped, clean_items, must_include_items)
        print(f"[CandidateOutfit] must_include_items={must_include_items}")

        candidates = self.build_candidate_combinations(
            grouped_items=grouped,
            parsed_intent=parsed_intent,
            must_include_items=must_include_items,
            weather=weather,
            rejected_candidates=rejected_candidates,
            max_candidates=max_candidates,
        )

        print(
            "[CandidateOutfit] generated_candidates="
            f"{[candidate.to_dict() for candidate in candidates]}"
        )
        print(f"[CandidateOutfit] rejected_candidates={rejected_candidates}")

        if not candidates:
            missing = [
                section for section in REQUIRED_SECTIONS
                if not grouped.get(section)
            ]
            reason = (
                f"Could not generate complete outfit candidates. Missing clean items for: {', '.join(missing)}."
                if missing
                else "Could not generate valid outfit candidates from the available wardrobe."
            )
            return {
                "success": False,
                "error": reason,
                "parsed_intent": parsed_intent,
                "must_include_items": must_include_items,
                "candidates": [],
                "debug": {
                    "grouped_items": self._debug_grouped(grouped),
                    "rejected_candidates": rejected_candidates,
                },
            }

        return {
            "success": True,
            "parsed_intent": parsed_intent,
            "must_include_items": must_include_items,
            "candidates": [candidate.to_dict() for candidate in candidates],
            "debug": {
                "weather": weather,
                "used_temperature_filter": used_temp_filter,
                "current_outfit_items": current_outfit_items,
                "exclude_items": exclude_items,
                "grouped_items": self._debug_grouped(grouped),
                "rejected_candidates": rejected_candidates,
            },
        }

    def normalize_type(self, value: Any) -> str:
        text = self._normalize_text(value)
        for alias, section in TYPE_ALIASES.items():
            if alias in text.split() or alias in text:
                return section
        return text

    def normalize_color(self, value: Any) -> str:
        text = self._normalize_text(value)
        return COLOR_ALIASES.get(text, text)

    def get_section(self, item: Dict[str, Any]) -> str:
        text = self._normalize_text(
            f"{item.get('type', '')} {item.get('name', '')} {item.get('brand', '')}"
        )
        for alias, section in TYPE_ALIASES.items():
            if alias in text.split() or alias in text:
                return section
        layer = item.get("layer")
        if layer == 3:
            return "outer_layer"
        if layer == 2 and any(
            token in text
            for token in ["calca", "calcas", "pants", "trousers", "jeans", "short", "calcoes"]
        ):
            return "pants"
        if layer == 2:
            return "insulation_layer"
        return "base_layer"

    def filter_clean_items(self, wardrobe_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            item for item in wardrobe_items
            if self._normalize_text(item.get("status") or "clean") == "clean"
        ]

    def filter_temperature_compatible(
        self,
        items: List[Dict[str, Any]],
        weather: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], bool]:
        temp = weather.get("temp", weather.get("temperature"))
        if temp is None:
            return items, False
        try:
            temp_value = float(temp)
        except (TypeError, ValueError):
            return items, False

        compatible = [
            item for item in items
            if self._item_temperature_match(item, temp_value)
        ]
        return compatible, True

    def find_must_include_items(
        self,
        grouped_items: Dict[str, List[Dict[str, Any]]],
        clean_items: List[Dict[str, Any]],
        parsed_intent: Dict[str, Any],
        excluded_ids: Optional[set] = None,
    ) -> Dict[str, Any]:
        excluded_ids = excluded_ids or set()
        requested_items = parsed_intent.get("must_include_items") or []
        must_include: List[Dict[str, Any]] = []

        for request in requested_items:
            requested_section = self._request_section(request)
            requested_color = self.normalize_color(request.get("color"))
            requested_name = self._normalize_text(request.get("name"))

            if not requested_section and not requested_color and not requested_name:
                continue

            candidates = clean_items
            matches = []
            rejections = []
            for item in candidates:
                item_id = str(item.get("id"))
                section = self.get_section(item)
                item_color = self.normalize_color(item.get("color"))
                item_name = self._normalize_text(item.get("name"))

                if item_id in excluded_ids:
                    rejections.append({"id": item_id, "reason": "excluded"})
                    continue
                if requested_section and section != requested_section:
                    rejections.append({"id": item_id, "reason": "type_mismatch"})
                    continue
                if requested_color and item_color != requested_color:
                    rejections.append({"id": item_id, "reason": "color_mismatch"})
                    continue
                if requested_name and requested_name not in item_name:
                    rejections.append({"id": item_id, "reason": "name_mismatch"})
                    continue
                matches.append(item)

            if not matches:
                label = self._request_label(request)
                print(
                    "[CandidateOutfit] must_include_rejections "
                    f"request={request} rejections={rejections}"
                )
                return {"error": f"I could not find {label} in your wardrobe."}

            selected = self._sort_items(matches, parsed_intent)[0]
            must_include.append(
                self._candidate_item(
                    selected,
                    requested_section or self.get_section(selected),
                )
            )

        deduped = []
        seen_sections = {}
        for item in must_include:
            previous = seen_sections.get(item["section"])
            if previous and previous["id"] != item["id"]:
                return {
                    "error": (
                        f"Conflicting required items for {item['section']}: "
                        f"{previous['name']} and {item['name']}."
                    )
                }
            if item["id"] not in {existing["id"] for existing in deduped}:
                deduped.append(item)
                seen_sections[item["section"]] = item
        return {"items": deduped}

    def build_candidate_combinations(
        self,
        grouped_items: Dict[str, List[Dict[str, Any]]],
        parsed_intent: Dict[str, Any],
        must_include_items: List[Dict[str, Any]],
        weather: Dict[str, Any],
        rejected_candidates: List[Dict[str, Any]],
        max_candidates: int = 5,
    ) -> List[CandidateOutfit]:
        must_by_section = {
            item["section"]: item for item in must_include_items
        }
        sorted_groups = {
            section: self._sort_items(items, parsed_intent)[:8]
            for section, items in grouped_items.items()
        }

        base_options = self._forced_or_options("base_layer", sorted_groups, must_by_section)
        pants_options = self._forced_or_options("pants", sorted_groups, must_by_section)
        shoes_options = self._forced_or_options("shoes", sorted_groups, must_by_section)
        insulation_options = self._forced_or_optional_options("insulation_layer", sorted_groups, must_by_section)
        outer_options = self._forced_or_optional_options("outer_layer", sorted_groups, must_by_section)
        accessories_options = [None] + sorted_groups.get("accessories", [])[:3]

        raw_combinations = []
        max_seed = max(
            len(base_options),
            len(pants_options),
            len(shoes_options),
            len(insulation_options),
            len(outer_options),
            len(accessories_options),
            max_candidates,
        )

        # First pass deliberately rotates the main sections together. This gives
        # visible variety before scoring gets a chance to cluster around one look.
        for index in range(max_seed * 2):
            raw_combinations.append((
                self._cyclic_pick(base_options, index),
                self._cyclic_pick(insulation_options, index),
                self._cyclic_pick(pants_options, index),
                self._cyclic_pick(shoes_options, index),
                self._cyclic_pick(outer_options, index),
                self._cyclic_pick(accessories_options, index),
            ))

        # Second pass explores cross-pairs so small wardrobes can still produce
        # 3-5 candidates without duplicating the first few section choices.
        for base_index, base in enumerate(base_options):
            for pants_index, pants in enumerate(pants_options):
                outer_index = base_index + pants_index
                accessory_index = base_index + (pants_index * 2)
                raw_combinations.append((
                    base,
                    self._cyclic_pick(insulation_options, base_index + pants_index),
                    pants,
                    self._cyclic_pick(shoes_options, base_index + pants_index),
                    self._cyclic_pick(outer_options, outer_index),
                    self._cyclic_pick(accessories_options, accessory_index),
                ))

        candidate_pool: List[CandidateOutfit] = []
        seen_signatures = set()

        for base, insulation, pants, shoes, outer, accessory in raw_combinations:
            raw_items = {
                "base_layer": base,
                "insulation_layer": insulation,
                "pants": pants,
                "outer_layer": outer,
                "shoes": shoes,
                "accessories": accessory,
            }
            is_valid, reason = self.validate_candidate(raw_items, must_by_section)
            if not is_valid:
                rejected_candidates.append({
                    "item_ids": [
                        item.get("id") for item in raw_items.values() if item
                    ],
                    "reason": reason,
                })
                continue

            candidate_items = [
                self._candidate_item(raw_items[section], section)
                for section in SECTION_ORDER
                if raw_items.get(section)
            ]
            signature = tuple(sorted(item["id"] for item in candidate_items))
            if signature in seen_signatures:
                rejected_candidates.append({
                    "item_ids": list(signature),
                    "reason": "duplicate_candidate",
                })
                continue
            seen_signatures.add(signature)

            scoring_items = [
                {
                    **self._candidate_item(raw_items[section], section),
                    "source": raw_items[section],
                }
                for section in SECTION_ORDER
                if raw_items.get(section)
            ]
            item_ids = [item["id"] for item in candidate_items]
            score, metadata = self._score_candidate(
                scoring_items,
                parsed_intent,
                must_by_section,
                weather,
            )
            metadata["diversity_reason"] = self._diversity_reason(
                candidate_items,
                candidate_pool,
            )
            candidate_pool.append(
                CandidateOutfit(
                    candidate_id="",
                    items=candidate_items,
                    item_ids=item_ids,
                    score=score,
                    metadata=metadata,
                )
            )

        candidates = self._select_diverse_candidates(candidate_pool, max_candidates)
        for index, candidate in enumerate(candidates):
            candidate.candidate_id = chr(ord("A") + index)
            candidate.metadata["diversity_reason"] = self._diversity_reason(
                candidate.items,
                candidates[:index],
            )
        return candidates

    def validate_candidate(
        self,
        raw_items: Dict[str, Optional[Dict[str, Any]]],
        must_by_section: Dict[str, Dict[str, Any]],
    ) -> Tuple[bool, str]:
        for section in REQUIRED_SECTIONS:
            if not raw_items.get(section):
                return False, f"missing_required_section:{section}"

        ids = [
            str(item.get("id")) for item in raw_items.values() if item
        ]
        if len(ids) != len(set(ids)):
            return False, "duplicate_item"

        for section, required_item in must_by_section.items():
            selected = raw_items.get(section)
            if not selected:
                return False, f"missing_must_include:{section}"
            if str(selected.get("id")) != str(required_item["id"]):
                return False, f"must_include_mismatch:{section}"

        for section, item in raw_items.items():
            if not item:
                continue
            actual_section = self.get_section(item)
            if actual_section != section:
                return False, f"section_mismatch:{section}:{actual_section}"

        return True, ""

    def _select_diverse_candidates(
        self,
        candidate_pool: List[CandidateOutfit],
        max_candidates: int,
    ) -> List[CandidateOutfit]:
        remaining = sorted(
            candidate_pool,
            key=lambda candidate: candidate.score,
            reverse=True,
        )
        selected: List[CandidateOutfit] = []
        seen_signatures = set()

        while remaining and len(selected) < max_candidates:
            best_index = 0
            best_value = None
            for index, candidate in enumerate(remaining):
                signature = tuple(sorted(candidate.item_ids))
                if signature in seen_signatures:
                    continue
                diversity_bonus = self._diversity_bonus(candidate, selected)
                value = candidate.score + diversity_bonus
                if best_value is None or value > best_value:
                    best_value = value
                    best_index = index

            candidate = remaining.pop(best_index)
            signature = tuple(sorted(candidate.item_ids))
            if signature in seen_signatures:
                continue
            selected.append(candidate)
            seen_signatures.add(signature)

        return selected

    def _diversity_bonus(
        self,
        candidate: CandidateOutfit,
        selected: List[CandidateOutfit],
    ) -> float:
        if not selected:
            return 20.0

        candidate_by_section = self._candidate_by_section(candidate.items)
        selected_by_section = [
            self._candidate_by_section(existing.items) for existing in selected
        ]
        bonus = 0.0
        for section in ["base_layer", "insulation_layer", "pants", "outer_layer", "accessories", "shoes"]:
            candidate_id = candidate_by_section.get(section)
            if not candidate_id:
                continue
            seen_ids = {
                existing.get(section) for existing in selected_by_section
                if existing.get(section)
            }
            if candidate_id not in seen_ids:
                if section == "base_layer":
                    bonus += 14
                elif section == "insulation_layer":
                    bonus += 6
                elif section == "pants":
                    bonus += 14
                elif section == "outer_layer":
                    bonus += 8
                elif section == "accessories":
                    bonus += 4
                elif section == "shoes":
                    bonus += 2

        has_outer = bool(candidate_by_section.get("outer_layer"))
        selected_outer_states = {
            bool(existing.get("outer_layer")) for existing in selected_by_section
        }
        if has_outer not in selected_outer_states:
            bonus += 5

        return bonus

    def _diversity_reason(
        self,
        items: List[Dict[str, Any]],
        previous_candidates: List[CandidateOutfit],
    ) -> str:
        if not previous_candidates:
            return "baseline candidate"

        current = self._candidate_by_section(items)
        previous = self._candidate_by_section(previous_candidates[-1].items)
        reasons = []
        if current.get("base_layer") != previous.get("base_layer"):
            reasons.append("different base layer")
        if current.get("insulation_layer") and current.get("insulation_layer") != previous.get("insulation_layer"):
            reasons.append("added insulation layer" if not previous.get("insulation_layer") else "different insulation layer")
        if current.get("pants") != previous.get("pants"):
            reasons.append("different pants")
        if current.get("outer_layer") and current.get("outer_layer") != previous.get("outer_layer"):
            reasons.append("added outer layer" if not previous.get("outer_layer") else "different outer layer")
        if current.get("accessories") and current.get("accessories") != previous.get("accessories"):
            reasons.append("different accessories")
        if not reasons:
            reasons.append("different combination")
        return ", ".join(reasons)

    def _candidate_by_section(self, items: List[Dict[str, Any]]) -> Dict[str, str]:
        return {
            item.get("section"): item.get("id")
            for item in items
            if item.get("section") and item.get("id")
        }

    def _cyclic_pick(self, options: List[Any], index: int) -> Any:
        if not options:
            return None
        return options[index % len(options)]

    def _forced_or_options(
        self,
        section: str,
        grouped_items: Dict[str, List[Dict[str, Any]]],
        must_by_section: Dict[str, Dict[str, Any]],
    ) -> List[Optional[Dict[str, Any]]]:
        if section in must_by_section:
            return [self._find_group_item(grouped_items, section, must_by_section[section]["id"])]
        return grouped_items.get(section, [])[:6]

    def _forced_or_optional_options(
        self,
        section: str,
        grouped_items: Dict[str, List[Dict[str, Any]]],
        must_by_section: Dict[str, Dict[str, Any]],
    ) -> List[Optional[Dict[str, Any]]]:
        if section in must_by_section:
            return [self._find_group_item(grouped_items, section, must_by_section[section]["id"])]
        return [None] + grouped_items.get(section, [])[:5]

    def _find_group_item(
        self,
        grouped_items: Dict[str, List[Dict[str, Any]]],
        section: str,
        item_id: str,
    ) -> Optional[Dict[str, Any]]:
        for item in grouped_items.get(section, []):
            if str(item.get("id")) == str(item_id):
                return item
        return None

    def _score_candidate(
        self,
        items: List[Dict[str, Any]],
        parsed_intent: Dict[str, Any],
        must_by_section: Dict[str, Dict[str, Any]],
        weather: Dict[str, Any],
    ) -> Tuple[float, Dict[str, Any]]:
        score_breakdown = {
            "request_match": self._request_match_score(items, parsed_intent, must_by_section),
            "style_consistency": self._style_consistency_score(items),
            "formality": self._formality_score(items, parsed_intent),
            "color_harmony": self._color_harmony_score(items),
            "occasion_fit": self._occasion_fit_score(items, parsed_intent),
            "weather": self._weather_score(items, weather),
            "completeness": self._completeness_score(items, weather),
            "usage_rotation": self._usage_rotation_score(items),
            "section_correctness": self._section_correctness_score(items),
        }
        total = round(sum(score_breakdown.values()), 3)
        score_breakdown["total"] = total

        return total, {
            "request_match": score_breakdown["request_match"] >= 22,
            "style_match": (
                score_breakdown["style_consistency"] >= 9
                and score_breakdown["formality"] >= 9
            ),
            "weather_match": score_breakdown["weather"] >= 8,
            "complete_outfit": score_breakdown["completeness"] >= 12,
            "section_correctness": score_breakdown["section_correctness"],
            "color_coherence": score_breakdown["color_harmony"],
            "usage_rotation": score_breakdown["usage_rotation"],
            "score_breakdown": score_breakdown,
            "score_explanation": self._score_explanation(score_breakdown),
        }

    def _request_match_score(
        self,
        items: List[Dict[str, Any]],
        parsed_intent: Dict[str, Any],
        must_by_section: Dict[str, Dict[str, Any]],
    ) -> float:
        score = 12.0
        item_ids = {str(item.get("id")) for item in items}
        if must_by_section:
            required_ids = {str(item.get("id")) for item in must_by_section.values()}
            score += 18.0 if required_ids.issubset(item_ids) else -30.0

        requested_colors = {
            self.normalize_color(color)
            for color in (parsed_intent.get("requested_colors") or [])
            if color
        }
        requested_types = {
            self.normalize_type(item_type)
            for item_type in (parsed_intent.get("requested_types") or [])
            if item_type
        }
        requested_style = self._requested_style(parsed_intent)
        requested_occasion = self._requested_occasion(parsed_intent)

        if requested_colors:
            colors = {self.normalize_color(item.get("source", {}).get("color")) for item in items}
            score += 5.0 if requested_colors & colors else -8.0
        if requested_types:
            sections = {item.get("section") for item in items}
            score += 5.0 if requested_types & sections else -8.0
        if requested_style:
            style_hits = sum(
                1 for item in items
                if self._item_style_matches(item.get("source", {}), requested_style)
            )
            score += min(style_hits * 4.0, 8.0)
        if requested_occasion:
            occasion_hits = sum(
                1 for item in items
                if requested_occasion in self._item_text(item.get("source", {}))
            )
            score += min(occasion_hits * 3.0, 6.0)

        return self._clamp(score, 0.0, 30.0)

    def _style_consistency_score(self, items: List[Dict[str, Any]]) -> float:
        styles = {self._item_style_label(item.get("source", {})) for item in items}
        score = 15.0
        incompatible_pairs = [
            ("formal", "sporty"),
            ("formal", "streetwear"),
            ("classic", "sporty"),
            ("elegant", "streetwear"),
        ]
        for left, right in incompatible_pairs:
            if left in styles and right in styles:
                score -= 5.0
        if "smart casual" in styles and ({"formal", "casual"} & styles):
            score += 2.0
        return self._clamp(score, 0.0, 15.0)

    def _formality_score(
        self,
        items: List[Dict[str, Any]],
        parsed_intent: Dict[str, Any],
    ) -> float:
        values = [self._item_formality(item.get("source", {})) for item in items]
        if not values:
            return 0.0
        average = sum(values) / len(values)
        formality_range = max(values) - min(values)
        score = 15.0 - (formality_range * 2.0)
        requested_style = self._requested_style(parsed_intent)
        if requested_style in {"formal", "elegant", "classic"}:
            score += 4.0 if average >= 4.0 else -6.0
        elif requested_style == "casual":
            score += 4.0 if 2.0 <= average <= 3.2 else -4.0
        elif requested_style in {"streetwear", "sporty"}:
            score += 4.0 if 1.0 <= average <= 2.3 else -5.0
        return self._clamp(score, 0.0, 15.0)

    def _color_harmony_score(self, items: List[Dict[str, Any]]) -> float:
        colors = [
            self.normalize_color(item.get("source", {}).get("color"))
            for item in items
            if item.get("source", {}).get("color")
        ]
        if not colors:
            return 7.0
        neutral_count = sum(1 for color in colors if color in NEUTRAL_COLORS)
        strong_colors = [color for color in colors if color in STRONG_COLORS]
        unique_strong = set(strong_colors)
        score = 6.0 + min(neutral_count * 1.2, 4.0)
        if len(unique_strong) <= 1:
            score += 2.0
        else:
            score -= (len(unique_strong) - 1) * 3.0
        section_by_color = {
            item.get("section"): self.normalize_color(item.get("source", {}).get("color"))
            for item in items
        }
        if section_by_color.get("shoes") in unique_strong and section_by_color.get("accessories") == section_by_color.get("shoes"):
            score += 1.0
        return self._clamp(score, 0.0, 12.0)

    def _occasion_fit_score(
        self,
        items: List[Dict[str, Any]],
        parsed_intent: Dict[str, Any],
    ) -> float:
        requested = self._requested_occasion(parsed_intent)
        if not requested:
            return 7.0
        accepted_styles = OCCASION_STYLE_FIT.get(requested, {requested})
        hits = 0
        for item in items:
            source = item.get("source", {})
            style = self._item_style_label(source)
            text = self._item_text(source)
            if style in accepted_styles or requested in text:
                hits += 1
        return self._clamp(4.0 + hits * 2.0, 0.0, 10.0)

    def _weather_score(self, items: List[Dict[str, Any]], weather: Dict[str, Any]) -> float:
        temp = weather.get("temp", weather.get("temperature"))
        condition = self._normalize_text(weather.get("condition"))
        has_sections = {item.get("section") for item in items}
        score = 8.0
        if temp is not None:
            try:
                temp_value = float(temp)
                compatible = sum(
                    1 for item in items
                    if self._item_temperature_match(item.get("source", {}), temp_value)
                )
                score = 5.0 + (compatible / max(len(items), 1)) * 5.0
                if temp_value <= 15:
                    if "insulation_layer" in has_sections:
                        score += 1.5
                    if "outer_layer" in has_sections:
                        score += 1.5
                elif temp_value >= 24:
                    if "outer_layer" in has_sections:
                        score -= 2.0
                    if "insulation_layer" in has_sections:
                        score -= 1.5
            except (TypeError, ValueError):
                pass
        if any(token in condition for token in ["rain", "chuva", "cloudy", "nublado"]):
            weatherproof = sum(
                1 for item in items
                if item.get("section") in {"outer_layer", "shoes"}
                and any(token in self._item_text(item.get("source", {})) for token in ["waterproof", "impermeavel", "rain", "chuva", "boot", "bota"])
            )
            score += min(weatherproof, 2) * 1.0
        return self._clamp(score, 0.0, 12.0)

    def _completeness_score(self, items: List[Dict[str, Any]], weather: Dict[str, Any]) -> float:
        section_counts: Dict[str, int] = {}
        for item in items:
            section = item.get("section")
            section_counts[section] = section_counts.get(section, 0) + 1
        score = 0.0
        for section in REQUIRED_SECTIONS:
            score += 4.0 if section_counts.get(section) else -8.0
        if section_counts.get("accessories"):
            score += 1.0
        temp = weather.get("temp", weather.get("temperature"))
        try:
            temp_value = float(temp) if temp is not None else None
        except (TypeError, ValueError):
            temp_value = None
        if temp_value is not None and temp_value <= 15:
            if section_counts.get("insulation_layer"):
                score += 1.0
            if section_counts.get("outer_layer"):
                score += 1.0
        if temp_value is not None and temp_value >= 24 and section_counts.get("outer_layer"):
            score -= 2.0
        duplicate_sections = sum(
            max(count - 1, 0)
            for section, count in section_counts.items()
            if section != "accessories"
        )
        score -= duplicate_sections * 3.0
        return self._clamp(score, 0.0, 14.0)

    def _usage_rotation_score(self, items: List[Dict[str, Any]]) -> float:
        if not items:
            return 0.0
        usages = [self._usage_frequency(item.get("source", {})) for item in items]
        average_usage = sum(usages) / len(usages)
        score = 6.0 - min(average_usage, 10.0) * 0.45
        unused_bonus = sum(1 for usage in usages if usage <= 1) * 0.2
        return self._clamp(score + unused_bonus, 0.0, 6.0)

    def _section_correctness_score(self, items: List[Dict[str, Any]]) -> float:
        if not items:
            return 0.0
        correct = sum(
            1 for item in items
            if item.get("section") == self.get_section(item.get("source", {}))
        )
        return self._clamp((correct / len(items)) * 10.0, 0.0, 10.0)

    def _score_explanation(self, score_breakdown: Dict[str, float]) -> str:
        strengths = []
        if score_breakdown.get("request_match", 0) >= 24:
            strengths.append("strong request match")
        if score_breakdown.get("style_consistency", 0) >= 12:
            strengths.append("consistent style")
        if score_breakdown.get("color_harmony", 0) >= 9:
            strengths.append("balanced colors")
        if score_breakdown.get("weather", 0) >= 9:
            strengths.append("good weather fit")
        if score_breakdown.get("formality", 0) >= 12:
            strengths.append("aligned formality")
        if not strengths:
            strengths.append("valid complete outfit")
        return ", ".join(strengths[:3])

    def _requested_style(self, parsed_intent: Dict[str, Any]) -> str:
        value = (
            parsed_intent.get("requested_style")
            or self._first_value(parsed_intent.get("style"))
            or self._first_value(parsed_intent.get("requested_styles"))
        )
        return self._canonical_style(value)

    def _requested_occasion(self, parsed_intent: Dict[str, Any]) -> str:
        value = (
            parsed_intent.get("requested_occasion")
            or self._first_value(parsed_intent.get("occasion"))
            or self._first_value(parsed_intent.get("requested_occasions"))
        )
        text = self._normalize_text(value)
        if not text:
            text = self._normalize_text(parsed_intent.get("raw_text") or parsed_intent.get("user_request"))
        if any(token in text for token in ["trabalho", "work", "office", "escritorio"]):
            return "work"
        if any(token in text for token in ["jantar", "dinner"]):
            return "dinner"
        if any(token in text for token in ["dia a dia", "daily", "everyday"]):
            return "daily"
        if any(token in text for token in ["desporto", "sport", "gym", "treino"]):
            return "sport"
        if any(token in text for token in ["sair", "noite", "night"]):
            return "night"
        return text

    def _item_style_label(self, item: Dict[str, Any]) -> str:
        text = self._item_text(item)
        if any(token in text for token in ["formal", "work", "office", "camisa", "shirt", "blazer", "elegant", "elegante"]):
            return "formal"
        if any(token in text for token in ["classic", "classico", "classica", "classicas", "trousers", "calcas classicas"]):
            return "classic"
        if "smart casual" in text or "smart_casual" in text:
            return "smart casual"
        if any(token in text for token in ["sport", "sporty", "desportivo", "running", "run", "jersey", "gym"]):
            return "sporty"
        if any(token in text for token in ["streetwear", "oversized", "stussy", "jordan"]):
            return "streetwear"
        if any(token in text for token in ["casual", "daily", "dia a dia", "hoodie", "tee", "t-shirt"]):
            return "casual"
        return "casual"

    def _item_formality(self, item: Dict[str, Any]) -> int:
        label = self._item_style_label(item)
        if label in {"sporty", "streetwear"}:
            return 1
        if label == "casual":
            return 2
        if label == "smart casual":
            return 3
        if label == "classic":
            return 4
        if label in {"formal", "elegant"}:
            return 5
        return 2

    def _canonical_style(self, value: Any) -> str:
        text = self._normalize_text(value)
        if not text:
            return ""
        if text in {"desportivo", "sport", "sporty"}:
            return "sporty"
        if text in {"elegante", "elegant"}:
            return "elegant"
        if text in {"classico", "classica", "classic"}:
            return "classic"
        if text in {"confortavel", "comfortable"}:
            return "casual"
        if "smart" in text:
            return "smart casual"
        return text

    def _item_text(self, item: Dict[str, Any]) -> str:
        return self._normalize_text(
            f"{item.get('name', '')} {item.get('type', '')} "
            f"{item.get('style', '')} {item.get('occasion', '')} "
            f"{item.get('brand', '')} {item.get('color', '')}"
        )

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return round(max(minimum, min(maximum, value)), 3)

    def _sort_items(
        self,
        items: List[Dict[str, Any]],
        parsed_intent: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return sorted(
            items,
            key=lambda item: self._item_score(item, parsed_intent),
            reverse=True,
        )

    def _item_score(self, item: Dict[str, Any], parsed_intent: Dict[str, Any]) -> float:
        score = 0.0
        requested_style = (
            parsed_intent.get("requested_style")
            or self._first_value(parsed_intent.get("style"))
        )
        if item.get("favorite"):
            score += 2
        if self.get_section(item) in REQUIRED_SECTIONS:
            score += 2
        if requested_style and self._item_style_matches(item, requested_style):
            score += 15
        if requested_style == "formal":
            text = self._normalize_text(
                f"{item.get('name', '')} {item.get('type', '')} {item.get('style', '')} {item.get('occasion', '')}"
            )
            if any(token in text for token in ["formal", "work", "camisa", "shirt", "blazer", "classico", "classica", "classicas", "calca", "calcas", "sapato"]):
                score += 8
            if any(token in text for token in ["jersey", "sport", "desportivo", "jordan", "running"]):
                score -= 8
        return score

    def _item_style_matches(self, item: Dict[str, Any], requested_style: Any) -> bool:
        requested = self._normalize_text(requested_style)
        text = self._normalize_text(
            f"{item.get('style', '')} {item.get('occasion', '')} {item.get('name', '')} {item.get('type', '')}"
        )
        if requested == "formal":
            return any(token in text for token in ["formal", "work", "elegant", "classico", "classica", "camisa", "blazer"])
        return requested in text

    def _section_style_score(
        self,
        section: str,
        item: Dict[str, Any],
        requested_style: Any,
    ) -> float:
        requested = self._normalize_text(requested_style)
        text = self._normalize_text(
            f"{item.get('name', '')} {item.get('type', '')} {item.get('style', '')} {item.get('occasion', '')}"
        )
        if requested != "formal":
            return 3.0 if requested and requested in text else 0.0

        score = 0.0
        if section == "base_layer":
            if any(token in text for token in ["camisa", "shirt", "formal", "work"]):
                score += 10
            if any(token in text for token in ["jersey", "sport", "hoodie"]):
                score -= 8
        elif section == "pants":
            if any(token in text for token in ["calcas", "calca", "trousers", "classica", "classicas", "formal", "work"]):
                score += 12
            if any(token in text for token in ["calcoes", "shorts", "sport"]):
                score -= 10
        elif section == "outer_layer":
            if any(token in text for token in ["casaco", "blazer", "classico", "classico", "formal", "work"]):
                score += 10
            if any(token in text for token in ["run", "running", "sport"]):
                score -= 6
        elif section == "shoes":
            if any(token in text for token in ["sapato", "formal", "loafer", "oxford"]):
                score += 8
            if any(token in text for token in ["jordan", "running", "sport"]):
                score -= 8
        return score

    def _usage_frequency(self, item: Dict[str, Any]) -> float:
        metrics = item.get("usage_metrics") or item.get("metadata", {}).get("usage_metrics") or {}
        for key in ("usage_frequency_last_7_days", "last_7_days", "usage_count", "times_used"):
            try:
                return float(metrics.get(key, 0) or 0)
            except (TypeError, ValueError):
                continue
        return 0.0

    def _candidate_item(self, item: Dict[str, Any], section: str) -> Dict[str, Any]:
        return {
            "section": section,
            "id": str(item.get("id")),
            "name": item.get("name"),
            "type": item.get("type"),
            "color": item.get("color"),
            "style": item.get("style"),
            "occasion": item.get("occasion"),
        }

    def _request_section(self, request: Dict[str, Any]) -> Optional[str]:
        requested_type = request.get("type")
        if not requested_type:
            return None
        return self.normalize_type(requested_type)

    def _request_label(self, request: Dict[str, Any]) -> str:
        color = request.get("color")
        item_type = request.get("type")
        name = request.get("name")
        if name:
            return str(name)
        if color and item_type:
            return f"{color} {item_type}"
        if color:
            return f"any {color} item"
        if item_type:
            return f"any {item_type}"
        return "matching items"

    def _group_by_section(
        self,
        items: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        grouped = {section: [] for section in SECTION_ORDER}
        for item in items:
            section = self.get_section(item)
            if section in grouped:
                grouped[section].append(item)
        return grouped

    def _force_must_include_into_groups(
        self,
        grouped: Dict[str, List[Dict[str, Any]]],
        clean_items: List[Dict[str, Any]],
        must_include_items: List[Dict[str, Any]],
    ) -> None:
        clean_by_id = {str(item.get("id")): item for item in clean_items}
        for required in must_include_items:
            section = required.get("section")
            item_id = str(required.get("id"))
            source = clean_by_id.get(item_id)
            if not section or not source:
                continue
            grouped.setdefault(section, [])
            if item_id not in {str(item.get("id")) for item in grouped[section]}:
                grouped[section].insert(0, source)
                print(
                    "[CandidateOutfit] forced_must_include_into_group "
                    f"section={section} id={item_id} name={source.get('name')}"
                )

    def _has_required_sections(self, grouped: Dict[str, List[Dict[str, Any]]]) -> bool:
        return all(grouped.get(section) for section in REQUIRED_SECTIONS)

    def _item_temperature_match(self, item: Dict[str, Any], temp: float) -> bool:
        try:
            temp_min = float(item.get("temp_min", item.get("temperature_range", {}).get("min", -10)))
            temp_max = float(item.get("temp_max", item.get("temperature_range", {}).get("max", 30)))
        except (TypeError, ValueError):
            return True
        return temp_min <= temp <= temp_max

    def _debug_grouped(self, grouped: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        return {
            section: [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "color": item.get("color"),
                    "style": item.get("style"),
                    "occasion": item.get("occasion"),
                    "status": item.get("status"),
                }
                for item in items
            ]
            for section, items in grouped.items()
        }

    def _log_wardrobe(self, user_id: str, wardrobe_items: List[Dict[str, Any]]) -> None:
        print(f"[CandidateOutfit] wardrobe_loaded count={len(wardrobe_items)} user_id={user_id}")
        for item in wardrobe_items:
            print(
                "[CandidateOutfit] wardrobe_item "
                f"id={item.get('id')} user_id={item.get('user_id')} "
                f"name={item.get('name')} type={item.get('type')} "
                f"color={item.get('color')} style={item.get('style')} "
                f"occasion={item.get('occasion')} status={item.get('status')} "
                f"layer={item.get('layer')} temp_min={item.get('temp_min')} "
                f"temp_max={item.get('temp_max')}"
            )

    def _normalize_text(self, value: Any) -> str:
        decomposed = unicodedata.normalize("NFD", str(value or ""))
        without_accents = "".join(
            char for char in decomposed if unicodedata.category(char) != "Mn"
        )
        return without_accents.lower().strip()

    def _first_value(self, value: Any) -> Any:
        if isinstance(value, list):
            return value[0] if value else None
        return value
