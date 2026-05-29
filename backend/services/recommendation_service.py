"""
Recommendation Service

Orchestrates the complete outfit recommendation pipeline.
Coordinates between:
- Data preparation service (prepares AI-ready context)
- Wardrobe service (fallback for direct item fetching)
- Weather service (fallback for weather data)
- Usage service (fallback for usage metrics)
- Prompt service (builds VLM prompts from context)
- VLM service (generates recommendations)
- Response parser (normalizes output)
- User request parser (parses user constraints)
- Constraint matching service (matches constraints with wardrobe)

Also provides fallback to rule-based recommendations if VLM fails.

PHASE 2 UPDATE:
Now uses DataPreparationService to build AI-ready context before VLM processing.
Flow: route → recommend_* → prepare_*_context → wardrobe/weather/usage services

PHASE 3 UPDATE:
Added validation layer to check VLM responses against wardrobe and layer rules.
- Validates item existence and status
- Checks layer compatibility
- Validates weather compatibility
- Includes retry logic with stricter prompts
- Provides detailed logging and error tracking

PHASE 4 UPDATE:
Added user request parsing and mandatory item enforcement.
- Parses user text to extract constraints
- Matches constraints with wardrobe items
- Forces mandatory items into the prompt
- Validates AI response includes mandatory items
- Adds variation to prevent same outfit
"""

import logging
import json
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from services.data_preparation_service import DataPreparationService
from services.prompt_service import PromptService
from services.response_parser import ResponseParser
from services.usage_service import UsageService
from services.vlm_service import VLMServiceInterface
from services.wardrobe_service import WardrobeService
from services.weather_service import WeatherService
from services.user_request_parser import UserRequestParser
from services.constraint_matching_service import ConstraintMatchingService
from services.item_scoring_service import ItemScoringService
from services.outfit_variation_service import OutfitVariationService
from services.candidate_outfit_service import CandidateOutfitService

# Setup logging
logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Main orchestrator for the outfit recommendation pipeline.

    Coordinates all services to provide outfit recommendations using the VLM,
    with fallback to rule-based recommendations if needed.

    Phase 2 Enhancement:
    - Now uses DataPreparationService to build AI-ready context
    - Context is prepared before VLM processing
    - Ensures all data is properly enriched and filtered
    """

    def __init__(
        self,
        vlm_service: VLMServiceInterface,
        wardrobe_service: Optional[WardrobeService] = None,
        weather_service: Optional[WeatherService] = None,
        usage_service: Optional[UsageService] = None,
        prompt_service: Optional[PromptService] = None,
        response_parser: Optional[ResponseParser] = None,
        user_request_parser: Optional[UserRequestParser] = None,
        constraint_matching_service: Optional[ConstraintMatchingService] = None,
        item_scoring_service: Optional[ItemScoringService] = None,
        outfit_variation_service: Optional[OutfitVariationService] = None,
        candidate_outfit_service: Optional[CandidateOutfitService] = None,
    ):
        """
        Initialize the recommendation service.

        Args:
            vlm_service: VLM service implementation (required)
            wardrobe_service: Wardrobe service (created if not provided)
            weather_service: Weather service (created if not provided)
            usage_service: Usage service (created if not provided)
            prompt_service: Prompt service (created if not provided)
            response_parser: Response parser (created if not provided)
            user_request_parser: User request parser (created if not provided)
            constraint_matching_service: Constraint matching service (created if not provided)
            item_scoring_service: Item scoring service (created if not provided)
            outfit_variation_service: Outfit variation service (created if not provided)
        """
        self.vlm_service = vlm_service
        self.wardrobe_service = wardrobe_service or WardrobeService()
        self.weather_service = weather_service or WeatherService()
        self.usage_service = usage_service or UsageService()
        self.prompt_service = prompt_service or PromptService()
        self.response_parser = response_parser or ResponseParser()
        self.user_request_parser = user_request_parser or UserRequestParser()
        self.constraint_matching_service = constraint_matching_service or ConstraintMatchingService()
        self.item_scoring_service = item_scoring_service or ItemScoringService()
        self.outfit_variation_service = outfit_variation_service or OutfitVariationService()
        self.candidate_outfit_service = candidate_outfit_service or CandidateOutfitService()

        # Phase 2: Data preparation service
        self.data_preparation_service = DataPreparationService(
            usage_service=self.usage_service,
            weather_service=self.weather_service,
            item_scoring_service=self.item_scoring_service,
        )

    async def recommend_daily_outfit(
        self,
        user_id: str,
        temperature: float,
        weather_condition: str,
        humidity: Optional[float] = None,
        wind_speed: Optional[float] = None,
        occasion: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
        exclude_items: Optional[List[str]] = None,
        current_outfit_items: Optional[List[str]] = None,
        user_request: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a daily outfit recommendation.

        Phase 4 Flow:
        1. Parse user request to extract constraints (if provided)
        2. Match constraints with wardrobe items
        3. Prepare AI-ready context using DataPreparationService
        4. Build prompt with mandatory items
        5. Pass context to VLM or fallback logic
        6. Validate response includes mandatory items
        7. Return structured recommendation

        Args:
            user_id: User's ID
            temperature: Current temperature in Celsius
            weather_condition: Weather condition (sunny, rainy, snowy, etc)
            humidity: Optional humidity percentage
            wind_speed: Optional wind speed in km/h
            occasion: Optional occasion (work, casual, sports, etc)
            preferences: Optional user style preferences
            exclude_items: Optional list of item IDs to exclude
            user_request: Optional user text request (e.g., "outfit with yellow sneakers")

        Returns:
            Dictionary with recommended outfit and metadata
        """
        try:
            # Phase 4: Parse user request and extract constraints
            must_include_items = []
            must_include_ids = []
            parsed_constraints = {}
            user_request_text = None
            effective_preferences = dict(preferences or {})
            effective_exclude_items = list(exclude_items or [])
            current_outfit_items = current_outfit_items or []
            
            if user_request:
                user_request_text = user_request
                logger.info(f"Parsing user request: {user_request}")
                parsed_constraints = self.user_request_parser.parse_request(user_request)
                logger.info(f"Parsed constraints: {parsed_constraints}")
                self._print_intent_debug(parsed_constraints)

                parsed_styles = parsed_constraints.get("style", [])
                if parsed_styles and not effective_preferences.get("style"):
                    effective_preferences["style"] = parsed_styles[0]

                parsed_occasions = parsed_constraints.get("occasion", [])
                if parsed_occasions and occasion is None:
                    occasion = parsed_occasions[0]
            else:
                parsed_constraints = self.user_request_parser.parse_request("")

            candidate_weather = {
                "temp": temperature,
                "temperature": temperature,
                "condition": weather_condition,
                "humidity": humidity,
                "wind_speed": wind_speed,
            }
            wardrobe_for_candidates = await self.wardrobe_service.get_user_wardrobe(
                user_id=user_id,
                only_clean=False,
                exclude_item_ids=None,
            )
            replace_sections = self._normalize_candidate_sections(
                parsed_constraints.get("replace_sections") or []
            )
            strict_replace_mode = (
                parsed_constraints.get("mode") == "replace_piece"
                or bool(replace_sections)
            )
            if strict_replace_mode:
                if not current_outfit_items:
                    return self._create_error_response(
                        "I need the current outfit to replace only one piece."
                    )
                return self._build_strict_replace_response(
                    wardrobe_items=wardrobe_for_candidates,
                    current_outfit_item_ids=current_outfit_items,
                    replace_sections=replace_sections,
                    parsed_constraints=parsed_constraints,
                    weather=candidate_weather,
                    exclude_items=effective_exclude_items,
                    user_request_text=user_request_text or "",
                )

            candidate_result = self.candidate_outfit_service.generate_candidate_outfits(
                user_id=user_id,
                wardrobe_items=wardrobe_for_candidates,
                weather=candidate_weather,
                parsed_intent=parsed_constraints,
                current_outfit_items=current_outfit_items,
                exclude_items=effective_exclude_items,
                max_candidates=12,
            )

            if not candidate_result.get("success"):
                return self._create_error_response(
                    candidate_result.get("error", "Could not generate outfit candidates.")
                )

            candidates = candidate_result.get("candidates", [])
            llava_candidates = self._prepare_candidates_for_llava(
                candidates=candidates,
                parsed_intent=parsed_constraints,
                max_candidates=3,
            )
            if not llava_candidates:
                return self._create_error_response(
                    "Could not find candidates that satisfy the hard request constraints."
                )
            print(
                "[CandidateSelection] generated_candidate_ids="
                f"{[candidate.get('candidate_id') for candidate in candidates]}"
            )
            print(
                "[CandidateSelection] llava_candidate_ids="
                f"{[candidate.get('candidate_id') for candidate in llava_candidates]}"
            )
            selection = await self.select_best_candidate_with_llava(
                candidates=llava_candidates,
                wardrobe_items=wardrobe_for_candidates,
                user_request=user_request_text or "",
                weather_data=candidate_weather,
            )
            selected_candidate = selection["candidate"]
            selected_candidate_id = selected_candidate.get("candidate_id")
            final_item_ids = list(selected_candidate.get("item_ids") or [])
            selected_section_by_id = {
                item.get("id"): item.get("section")
                for item in selected_candidate.get("items", [])
                if item.get("id") and item.get("section")
            }
            wardrobe_by_id = {
                str(item.get("id")): item for item in wardrobe_for_candidates
                if item.get("id")
            }
            final_items = [
                {
                    **wardrobe_by_id[item_id],
                    "section": selected_section_by_id.get(item_id),
                }
                for item_id in final_item_ids
                if item_id in wardrobe_by_id
            ]
            reasoning = self._build_candidate_selection_reasoning(
                selected_candidate=selected_candidate,
                user_request=user_request_text,
                weather_data=candidate_weather,
            )
            print(f"[CandidateSelection] selected_candidate_id={selected_candidate_id}")
            print(f"[CandidateSelection] final_item_ids={final_item_ids}")

            return {
                "success": True,
                "outfit": {
                    "items": final_items,
                    "reasoning": reasoning,
                },
                "model_used": selection.get("model_used"),
                "context_used": "candidate_outfit_selection",
                "validation": {
                    "warnings": [],
                    "errors": [],
                },
                "debug": {
                    "generated_candidate_ids": [
                        candidate.get("candidate_id") for candidate in candidates
                    ],
                    "llava_candidate_ids": [
                        candidate.get("candidate_id") for candidate in llava_candidates
                    ],
                    "raw_llava_candidate_response": selection.get("raw_response"),
                    "selected_candidate_reasoning": selection.get("reasoning"),
                    "selected_candidate_id": selected_candidate_id,
                    "final_item_ids": final_item_ids,
                    "top_candidate_by_score": selection.get("top_candidate_by_score"),
                    "llava_selected": selection.get("llava_selected"),
                    "score_gap": selection.get("score_gap"),
                    "final_selected": selection.get("final_selected"),
                    "selection_reason": selection.get("selection_reason"),
                    "llava_confidence": selection.get("confidence"),
                    "candidates": candidates,
                    "llava_candidates": llava_candidates,
                },
                "timestamp": datetime.now().isoformat(),
            }

            mode = parsed_constraints.get("mode")
            is_followup_command = mode in {"replace_piece", "keep_piece", "avoid_piece"}
            must_include_constraints = parsed_constraints.get("must_include", {})
            has_must_include_constraints = any(
                bool(values) for values in must_include_constraints.values()
            ) and not is_followup_command
            avoid_constraints = parsed_constraints.get("avoid", {})
            needs_constraint_wardrobe = bool(
                has_must_include_constraints
                or avoid_constraints
                or current_outfit_items
                or parsed_constraints.get("replace_sections")
                or parsed_constraints.get("keep_sections")
                or user_request
            )
            clean_wardrobe = None
            clean_wardrobe_before_avoid = None
            followup_plan = None

            if needs_constraint_wardrobe:
                debug_wardrobe = await self.wardrobe_service.get_user_wardrobe(
                    user_id=user_id,
                    only_clean=False,
                    exclude_item_ids=None,
                )
                self._print_wardrobe_debug(debug_wardrobe)
                self._print_command_debug(
                    parsed_constraints=parsed_constraints,
                    wardrobe=debug_wardrobe,
                    user_id=user_id,
                    temperature=temperature,
                    excluded_ids=set(effective_exclude_items),
                )
                self._print_footwear_color_debug(
                    parsed_constraints=parsed_constraints,
                    wardrobe=debug_wardrobe,
                    user_id=user_id,
                    temperature=temperature,
                    excluded_ids=set(effective_exclude_items),
                )

                clean_wardrobe = await self.wardrobe_service.get_user_wardrobe(
                    user_id=user_id,
                    only_clean=True,
                    exclude_item_ids=effective_exclude_items,
                )
                clean_wardrobe_before_avoid = list(clean_wardrobe)

            if avoid_constraints and clean_wardrobe is not None:
                avoid_ids = self.constraint_matching_service.find_avoid_item_ids(
                    avoid_constraints,
                    clean_wardrobe,
                )
                if avoid_ids:
                    effective_exclude_items = list(
                        dict.fromkeys([*effective_exclude_items, *avoid_ids])
                    )
                    clean_wardrobe = [
                        item for item in clean_wardrobe
                        if item.get("id") not in set(avoid_ids)
                    ]

            if current_outfit_items and clean_wardrobe is not None:
                current_item_set = set(current_outfit_items)
                current_clean_items = [
                    item for item in debug_wardrobe
                    if item.get("id") in current_item_set
                ]
                followup_plan = self._build_followup_plan(
                    parsed_constraints,
                    current_clean_items,
                )
                if followup_plan:
                    keep_ids = followup_plan["keep_ids"]
                    replace_ids = followup_plan["replace_ids"]
                    if keep_ids:
                        must_include_ids = list(dict.fromkeys([*must_include_ids, *keep_ids]))
                    if replace_ids:
                        effective_exclude_items = list(
                            dict.fromkeys([*effective_exclude_items, *replace_ids])
                        )

            if has_must_include_constraints and clean_wardrobe is not None:
                resolved = self._resolve_mandatory_constraints(
                    parsed_constraints=parsed_constraints,
                    wardrobe=debug_wardrobe,
                    user_id=user_id,
                    temperature=temperature,
                    excluded_ids=set(effective_exclude_items),
                )
                if resolved.get("error"):
                    return self._create_error_response(resolved["error"])

                must_include_items = resolved["items"]
                must_include_ids = [
                    item.get("id") for item in must_include_items if item.get("id")
                ]
                if followup_plan and followup_plan.get("keep_ids"):
                    must_include_ids = list(
                        dict.fromkeys([*must_include_ids, *followup_plan["keep_ids"]])
                    )
                logger.info(
                    f"Found {len(must_include_items)} mandatory items: "
                    f"{[item.get('name') for item in must_include_items]}"
                )
            
            # Phase 2: Prepare AI-ready context
            ai_context = await self.data_preparation_service.prepare_daily_context(
                user_id=user_id,
                temperature=temperature,
                weather_condition=weather_condition,
                humidity=humidity,
                wind_speed=wind_speed,
                occasion=occasion,
                user_preferences=effective_preferences,
                exclude_items=effective_exclude_items,
                must_include_ids=must_include_ids,
                max_items_per_layer=20 if followup_plan else 5,
            )

            if followup_plan:
                followup_result = self._build_followup_response(
                    ai_context=ai_context,
                    current_items=followup_plan["current_items"],
                    keep_ids=followup_plan["keep_ids"],
                    replace_sections=followup_plan["replace_sections"],
                    parsed_constraints=parsed_constraints,
                    weather={
                        "temperature": temperature,
                        "condition": weather_condition,
                    },
                    preferences=effective_preferences,
                    must_include_items=must_include_items,
                )
                if followup_result:
                    return followup_result

            # Check if we have any items to work with
            if not ai_context.get_all_items():
                return self._create_error_response(
                    "No suitable wardrobe items available for recommendation"
                )

            if must_include_items:
                scores_by_id = {
                    item.id: item.score for item in ai_context.get_all_items()
                }
                for item in must_include_items:
                    item["score"] = scores_by_id.get(item.get("id"))

            # Phase 3: Call VLM with mandatory items in prompt
            prompt = self.prompt_service.build_daily_prompt_from_context(
                ai_context,
                must_include_items=must_include_items,
                user_request_text=user_request_text,
            )
            
            vlm_response = await self.vlm_service.recommend_outfit(
                wardrobe_items=[item.to_dict() for item in ai_context.get_all_items()],
                weather_context=ai_context.weather_current.to_dict()
                if ai_context.weather_current
                else {},
                user_context={
                    "preferences": ai_context.user_constraints.get("preferences", {}),
                    "occasion": occasion,
                    "mandatory_items": [item.get("id") for item in must_include_items],
                },
                prompt_template=prompt,
            )

            if not vlm_response.success:
                print(f"VLM request failed, falling back. Error: {vlm_response.error}")
                return await self._fallback_daily_recommendation_from_context(
                    ai_context
                )

            logger.info(
                f"VLM Response: outfit_items={vlm_response.outfit_items}, reasoning={vlm_response.reasoning}"
            )
            print("\n========== RAW VLM RESPONSE ==========")
            print(vlm_response)
            print("=====================================\n")
            raw_response = (
                (vlm_response.metadata or {}).get("raw_response")
                or vlm_response.reasoning
                or ""
            )
            logger.info(f"Raw VLM output: {raw_response}")
            print(f"[RecommendationService] raw_llava_response={raw_response}")

            parsed_result = self.response_parser.parse_daily_outfit(
                {
                    "response": raw_response,
                    "reasoning": vlm_response.reasoning or raw_response,
                },
                [item.to_dict() for item in ai_context.get_all_items()],
                ai_context.weather_current.to_dict() if ai_context.weather_current else {},
            )
            logger.info(
                f"Parsed items: {parsed_result.get('item_ids', [])}; "
                f"parser warnings={parsed_result.get('warnings', [])}; "
                f"parser validation_errors={parsed_result.get('validation_errors', [])}"
            )
            print("\n========== PARSED OUTPUT ==========")
            print(parsed_result)
            print("===================================\n")
            print(
                "[RecommendationService] parsed_json_ids="
                f"{parsed_result.get('item_ids', [])}"
            )

            if not parsed_result.get("success"):
                logger.warning("Parser found no valid structured outfit. Using fallback.")
                result = await self._fallback_daily_recommendation_from_context(ai_context)
                result["debug"] = {
                    "raw_vlm_response": raw_response,
                    "parsed_items": parsed_result.get("item_ids", []),
                    "validation_errors": parsed_result.get("validation_errors", []),
                }
                return result

            # Phase 4: Validate that mandatory items are present
            parsed_item_ids = set(parsed_result.get('item_ids', []))
            mandatory_item_ids = set(item.get("id") for item in must_include_items)
            
            if mandatory_item_ids and not mandatory_item_ids.issubset(parsed_item_ids):
                missing_mandatory = mandatory_item_ids - parsed_item_ids
                logger.warning(f"Mandatory items missing from VLM response: {missing_mandatory}")

                retry_response = await self._retry_with_stricter_prompt(
                    ai_context,
                    temperature,
                    weather_condition,
                    occasion,
                    [f"Missing mandatory item(s): {', '.join(missing_mandatory)}"],
                    must_include_items=must_include_items,
                    user_request_text=user_request_text,
                )

                if retry_response and retry_response.success:
                    retry_raw_response = (
                        (retry_response.metadata or {}).get("raw_response")
                        or retry_response.reasoning
                        or ""
                    )
                    retry_parsed_result = self.response_parser.parse_daily_outfit(
                        {
                            "response": retry_raw_response,
                            "reasoning": retry_response.reasoning or retry_raw_response,
                        },
                        [item.to_dict() for item in ai_context.get_all_items()],
                        ai_context.weather_current.to_dict()
                        if ai_context.weather_current
                        else {},
                    )
                    retry_item_ids = set(retry_parsed_result.get("item_ids", []))
                    vlm_response = retry_response
                    raw_response = retry_raw_response
                    print(f"[RecommendationService] raw_llava_response={raw_response}")
                    print(
                        "[RecommendationService] parsed_json_ids="
                        f"{retry_parsed_result.get('item_ids', [])}"
                    )

                    if mandatory_item_ids.issubset(retry_item_ids):
                        parsed_result = retry_parsed_result
                        missing_mandatory = set()
                        logger.info("Retry included all mandatory items.")
                    else:
                        missing_mandatory = mandatory_item_ids - retry_item_ids
                        parsed_result = retry_parsed_result
                        logger.warning(
                            f"Retry still missing mandatory items: {missing_mandatory}"
                        )

                if missing_mandatory:
                    logger.info("Force injecting missing mandatory items.")
                    injected_items = list(parsed_result.get('item_ids', []))
                    layer_assignments = parsed_result.setdefault(
                        "layer_assignments",
                        {1: [], 2: [], 3: [], "shoes": [], "accessories": []},
                    )
                    items_by_id_for_injection = {
                        item.id: item for item in ai_context.get_all_items()
                    }
                    for item in must_include_items:
                        mandatory_id = item.get("id")
                        if not mandatory_id:
                            continue
                        mandatory_ai_item = items_by_id_for_injection.get(mandatory_id)
                        mandatory_section = (
                            self._json_section_for_item(mandatory_ai_item)
                            if mandatory_ai_item
                            else None
                        )
                        if mandatory_section is not None:
                            competing_ids = set(layer_assignments.get(mandatory_section, []))
                            injected_items = [
                                item_id for item_id in injected_items
                                if item_id == mandatory_id or item_id not in competing_ids
                            ]
                            layer_assignments[mandatory_section] = [mandatory_id]
                        if mandatory_id not in injected_items:
                            injected_items.append(mandatory_id)
                    parsed_result['item_ids'] = injected_items
                    parsed_result['injected_items'] = list(missing_mandatory)
                    logger.info(f"Injected items: {list(missing_mandatory)}")

            if must_include_items:
                self._enforce_parsed_mandatory_slots(parsed_result, ai_context, must_include_items)

            # Build wardrobe by ID map for validation
            wardrobe_by_id = {item.id: item for item in ai_context.get_all_items()}

            validation_result = await self._validate_vlm_response(
                vlm_response,
                parsed_result,
                ai_context,
                wardrobe_by_id,
                temperature,
                weather_condition,
            )

            if not validation_result["valid"]:
                validation_errors = validation_result["errors"]
                print("\n========== VALIDATION ERRORS ==========")
                print(validation_errors)
                print("=======================================\n")
                logger.warning(
                    f"VLM response validation failed. Errors: {validation_result['errors']}. "
                    f"Warnings: {validation_result['warnings']}"
                )

                if validation_result["retry_count"] < 1:
                    logger.info("Retrying with stricter prompt...")
                    vlm_response = await self._retry_with_stricter_prompt(
                        ai_context,
                        temperature,
                        weather_condition,
                        occasion,
                        validation_result["errors"],
                        must_include_items=must_include_items,
                        user_request_text=user_request_text,
                    )

                    if vlm_response and vlm_response.success:
                        retry_raw_response = (
                            (vlm_response.metadata or {}).get("raw_response")
                            or vlm_response.reasoning
                            or ""
                        )
                        parsed_result = self.response_parser.parse_daily_outfit(
                            {
                                "response": retry_raw_response,
                                "reasoning": vlm_response.reasoning or retry_raw_response,
                            },
                            [item.to_dict() for item in ai_context.get_all_items()],
                            ai_context.weather_current.to_dict()
                            if ai_context.weather_current
                            else {},
                        )
                        validation_result = await self._validate_vlm_response(
                            vlm_response,
                            parsed_result,
                            ai_context,
                            wardrobe_by_id,
                            temperature,
                            weather_condition,
                        )
                        validation_result["retry_count"] = 1
                        print(
                            "[RecommendationService] parsed_json_ids="
                            f"{parsed_result.get('item_ids', [])}"
                        )

                if not validation_result["valid"]:
                    validation_errors = validation_result["errors"]
                    print("\n========== VALIDATION ERRORS ==========")
                    print(validation_errors)
                    print("=======================================\n")
                    logger.warning("VLM validation failed after retry. Using fallback.")
                    result = await self._fallback_daily_recommendation_from_context(
                        ai_context
                    )
                    result["debug"] = {
                        "raw_vlm_response": raw_response,
                        "parsed_items": parsed_result.get("item_ids", []),
                        "validation_errors": validation_errors,
                    }
                    return result
                else:
                    logger.info("VLM validation succeeded after retry.")
            else:
                validation_errors = validation_result.get("errors", [])
                print("\n========== VALIDATION ERRORS ==========")
                print(validation_errors)
                print("=======================================\n")

            model_used = "llava"

            # Use validated items from validation result
            validated_outfit_items = validation_result.get("items", [])
            print(
                "[FinalConsistency] validated_final_ids_before_enforcement="
                f"{[getattr(item, 'id', None) for item in validated_outfit_items]} "
                f"must_include_ids={[item.get('id') for item in must_include_items or []]}"
            )
            validated_outfit_items = self._enforce_final_outfit_constraints(
                selected_items=validated_outfit_items,
                ai_context=ai_context,
                must_include_items=must_include_items,
            )
            print(
                "[RecommendationService] validated_final_ids="
                f"{[getattr(item, 'id', None) for item in validated_outfit_items]}"
            )

            clean_reasoning = self.build_clean_reasoning(
                validated_items=validated_outfit_items,
                weather=ai_context.weather_current.to_dict() if ai_context.weather_current else {},
                preferences=effective_preferences,
                must_include_items=must_include_items,
                user_request_text=user_request_text,
                original_reasoning=validation_result.get("reasoning")
                or parsed_result.get("reasoning"),
            )
            clean_reasoning = self._ensure_reasoning_matches_items(
                clean_reasoning,
                validated_outfit_items,
                weather=ai_context.weather_current.to_dict() if ai_context.weather_current else {},
                preferences=effective_preferences,
                must_include_items=must_include_items,
                user_request_text=user_request_text,
            )
            self._log_final_outfit_debug(
                final_items=validated_outfit_items,
                reasoning=clean_reasoning,
                must_include_items=must_include_items,
            )

            return {
                "success": True,
                "outfit": {
                    "items": [item.to_dict() for item in validated_outfit_items],
                    "reasoning": clean_reasoning,
                },
                "model_used": model_used,
                "context_used": "ai_ready_context",
                "validation": {
                    "warnings": validation_result.get("warnings", []),
                    "errors": validation_result.get("errors", []),
                    "parser_warnings": parsed_result.get("warnings", []),
                    "parser_errors": parsed_result.get("validation_errors", []),
                },
                "debug": {
                    "raw_vlm_response": raw_response,
                    "raw_llava_response": raw_response,
                    "parsed_items": parsed_result.get("item_ids", []),
                    "parsed_json_ids": parsed_result.get("item_ids", []),
                    "validation_errors": validation_result.get("errors", []),
                    "validated_final_ids": [
                        getattr(item, "id", None) for item in validated_outfit_items
                    ],
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in daily recommendation: {e}", exc_info=True)
            print(f"Error in daily recommendation: {e}")
            return self._create_error_response(f"Daily recommendation failed: {str(e)}")

    async def select_best_candidate_with_llava(
        self,
        candidates: List[Dict[str, Any]],
        wardrobe_items: List[Dict[str, Any]],
        user_request: str,
        weather_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ask LLaVA to choose one candidate ID. LLaVA may not create, remove, or
        replace items. If the response is invalid, choose the highest-scored
        candidate deterministically.
        """
        candidate_by_id = {
            str(candidate.get("candidate_id")): candidate
            for candidate in candidates
            if candidate.get("candidate_id")
        }
        fallback_candidate = sorted(
            candidates,
            key=lambda candidate: candidate.get("score", 0),
            reverse=True,
        )[0]
        top_candidate_id = str(fallback_candidate.get("candidate_id"))
        prompt = self._build_candidate_selection_prompt(
            candidates=candidates,
            user_request=user_request,
            weather_data=weather_data,
        )
        candidate_item_ids = {
            item.get("id")
            for candidate in candidates
            for item in candidate.get("items", [])
            if item.get("id")
        }
        candidate_wardrobe_items = [
            item for item in wardrobe_items
            if item.get("id") in candidate_item_ids
        ]

        try:
            vlm_response = await self.vlm_service.recommend_outfit(
                wardrobe_items=candidate_wardrobe_items,
                weather_context=weather_data,
                user_context={
                    "user_request": user_request,
                    "mode": "candidate_selection",
                },
                prompt_template=prompt,
            )
        except Exception as exc:
            print(f"[CandidateSelection] LLaVA exception={exc}")
            return {
                "candidate": fallback_candidate,
                "selected_candidate_id": fallback_candidate.get("candidate_id"),
                "reasoning": "LLaVA failed, selected the highest-scored candidate.",
                "raw_response": str(exc),
                "model_used": "llava_candidate_fallback",
                "top_candidate_by_score": top_candidate_id,
                "llava_selected": None,
                "score_gap": 0,
                "final_selected": top_candidate_id,
                "selection_reason": "llava_exception",
                "confidence": 0.0,
            }

        raw_response = (
            (vlm_response.metadata or {}).get("raw_response")
            or vlm_response.reasoning
            or ""
        )
        print(f"[CandidateSelection] raw_llava_candidate_response={raw_response}")

        if not vlm_response.success:
            return {
                "candidate": fallback_candidate,
                "selected_candidate_id": fallback_candidate.get("candidate_id"),
                "reasoning": "LLaVA failed, selected the highest-scored candidate.",
                "raw_response": raw_response or vlm_response.error,
                "model_used": "llava_candidate_fallback",
                "top_candidate_by_score": top_candidate_id,
                "llava_selected": None,
                "score_gap": 0,
                "final_selected": top_candidate_id,
                "selection_reason": "llava_failed",
                "confidence": 0.0,
            }

        parsed = self._parse_candidate_selection_json(raw_response)
        selected_candidate_id = str(parsed.get("selected_candidate") or "").strip()
        confidence = self._parse_llava_confidence(parsed.get("confidence"))
        if selected_candidate_id not in candidate_by_id:
            print(
                "[CandidateSelection] invalid_selected_candidate "
                f"selected={selected_candidate_id} valid={list(candidate_by_id.keys())}"
            )
            return {
                "candidate": fallback_candidate,
                "selected_candidate_id": fallback_candidate.get("candidate_id"),
                "reasoning": "LLaVA returned an invalid candidate, selected the highest-scored candidate.",
                "raw_response": raw_response,
                "model_used": "llava_candidate_fallback",
                "top_candidate_by_score": top_candidate_id,
                "llava_selected": selected_candidate_id or None,
                "score_gap": 0,
                "final_selected": top_candidate_id,
                "selection_reason": "invalid_candidate",
                "confidence": confidence,
            }

        selected_candidate = candidate_by_id[selected_candidate_id]
        score_gap = round(
            float(fallback_candidate.get("score", 0) or 0)
            - float(selected_candidate.get("score", 0) or 0),
            3,
        )
        if confidence < 0.65:
            print(
                "[CandidateSelection] low_confidence_fallback "
                f"selected={selected_candidate_id} confidence={confidence} "
                f"fallback={top_candidate_id}"
            )
            return {
                "candidate": fallback_candidate,
                "selected_candidate_id": fallback_candidate.get("candidate_id"),
                "reasoning": str(parsed.get("reasoning") or "").strip(),
                "raw_response": raw_response,
                "model_used": "candidate_score_fallback",
                "top_candidate_by_score": top_candidate_id,
                "llava_selected": selected_candidate_id,
                "score_gap": score_gap,
                "final_selected": top_candidate_id,
                "selection_reason": "low_confidence",
                "confidence": confidence,
            }
        if score_gap > 15:
            print(
                "[CandidateSelection] score_override "
                f"top={top_candidate_id} selected={selected_candidate_id} "
                f"score_gap={score_gap}"
            )
            return {
                "candidate": fallback_candidate,
                "selected_candidate_id": fallback_candidate.get("candidate_id"),
                "reasoning": str(parsed.get("reasoning") or "").strip(),
                "raw_response": raw_response,
                "model_used": "candidate_score_override",
                "top_candidate_by_score": top_candidate_id,
                "llava_selected": selected_candidate_id,
                "score_gap": score_gap,
                "final_selected": top_candidate_id,
                "selection_reason": "score_override",
                "confidence": confidence,
            }

        return {
            "candidate": selected_candidate,
            "selected_candidate_id": selected_candidate_id,
            "reasoning": str(parsed.get("reasoning") or "").strip(),
            "raw_response": raw_response,
            "model_used": "llava_candidate_selection",
            "top_candidate_by_score": top_candidate_id,
            "llava_selected": selected_candidate_id,
            "score_gap": score_gap,
            "final_selected": selected_candidate_id,
            "selection_reason": "llava_selected",
            "confidence": confidence,
        }

    def _build_candidate_selection_prompt(
        self,
        candidates: List[Dict[str, Any]],
        user_request: str,
        weather_data: Dict[str, Any],
    ) -> str:
        candidate_lines = []
        for candidate in candidates:
            metadata = candidate.get("metadata", {}) or {}
            candidate_lines.append(f"Candidate {candidate.get('candidate_id')}:")
            candidate_lines.append(f"Total score: {candidate.get('score')}")
            candidate_lines.append(
                f"Score explanation: {metadata.get('score_explanation', '')}"
            )
            candidate_lines.append(
                f"Strengths: {', '.join(metadata.get('strengths') or []) or 'valid candidate'}"
            )
            candidate_lines.append(
                f"Weaknesses: {', '.join(metadata.get('weaknesses') or []) or 'none'}"
            )
            candidate_lines.append(
                f"Diversity reason: {metadata.get('diversity_reason', '')}"
            )
            for item in candidate.get("items", []):
                candidate_lines.append(
                    "- "
                    f"Section: {item.get('section')} | "
                    f"ID: {item.get('id')} | "
                    f"Name: {item.get('name')} | "
                    f"Type: {item.get('type')} | "
                    f"Color: {item.get('color')} | "
                    f"Style: {item.get('style')} | "
                    f"Occasion: {item.get('occasion')}"
                )
            candidate_lines.append("")

        return f"""You are a stylist choosing the best outfit candidate.

You are not choosing freely from the wardrobe. You are choosing the best candidate from already validated outfits.
You must choose ONLY one candidate ID from the provided list.
Do not invent items.
Do not change items.
Do not remove items.
Do not select individual item IDs.
Choose the best candidate visually and stylistically, but do not ignore hard request matches. Prefer candidates with higher score unless there is a clear visual/style reason.
Do not prioritize visual variety over request accuracy.
Return JSON only. No markdown. No extra text.

User request:
{user_request or "No specific request"}

Weather:
{json.dumps(weather_data, ensure_ascii=False)}

Candidate list:
{chr(10).join(candidate_lines)}

Required response:
{{
  "selected_candidate": "A",
  "reasoning": "short explanation",
  "confidence": 0.0
}}
"""

    def _parse_candidate_selection_json(self, response_text: str) -> Dict[str, Any]:
        if not response_text:
            return {}
        stripped = response_text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
            stripped = re.sub(r"\s*```$", "", stripped)
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            parsed = json.loads(stripped[start:end + 1])
        except json.JSONDecodeError as exc:
            print(f"[CandidateSelection] JSON parse failed: {exc}")
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _parse_llava_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.75
        return max(0.0, min(1.0, confidence))

    def _prepare_candidates_for_llava(
        self,
        candidates: List[Dict[str, Any]],
        parsed_intent: Dict[str, Any],
        max_candidates: int = 3,
    ) -> List[Dict[str, Any]]:
        sorted_candidates = sorted(
            candidates,
            key=lambda candidate: float(candidate.get("score", 0) or 0),
            reverse=True,
        )
        hard_filtered = [
            candidate for candidate in sorted_candidates
            if self._candidate_respects_hard_request(candidate, parsed_intent)
        ]
        if not hard_filtered:
            if self._has_hard_candidate_request(parsed_intent):
                return []
            hard_filtered = sorted_candidates

        selected: List[Dict[str, Any]] = []
        top_score = float(hard_filtered[0].get("score", 0) or 0) if hard_filtered else 0.0
        close_score_window = 8.0

        for candidate in hard_filtered:
            if len(selected) >= max_candidates:
                break
            candidate_score = float(candidate.get("score", 0) or 0)
            if len(selected) < 2 or top_score - candidate_score <= close_score_window:
                selected.append(candidate)

        for candidate in hard_filtered:
            if len(selected) >= max_candidates:
                break
            if candidate not in selected:
                selected.append(candidate)

        prepared = []
        for index, candidate in enumerate(selected[:max_candidates]):
            cloned = {
                **candidate,
                "candidate_id": chr(ord("A") + index),
                "metadata": dict(candidate.get("metadata") or {}),
            }
            strengths, weaknesses = self._candidate_quality_labels(cloned, parsed_intent)
            cloned["metadata"]["strengths"] = strengths
            cloned["metadata"]["weaknesses"] = weaknesses
            prepared.append(cloned)
        return prepared

    def _has_hard_candidate_request(self, parsed_intent: Dict[str, Any]) -> bool:
        requested_style = self._normalized_requested_style(parsed_intent)
        requested_occasion = self._normalized_requested_occasion(parsed_intent)
        return bool(
            parsed_intent.get("must_include_items")
            or requested_style in {"formal", "classic", "elegant", "streetwear"}
            or requested_occasion in {"work", "trabalho", "dinner", "jantar"}
        )

    def _candidate_respects_hard_request(
        self,
        candidate: Dict[str, Any],
        parsed_intent: Dict[str, Any],
    ) -> bool:
        metadata = candidate.get("metadata") or {}
        if metadata.get("request_match") is False:
            return False

        requested_style = self._normalized_requested_style(parsed_intent)
        requested_occasion = self._normalized_requested_occasion(parsed_intent)
        if requested_style in {"formal", "classic", "elegant"}:
            return self._candidate_average_formality(candidate) >= 3.6
        if requested_style == "streetwear":
            return self._candidate_has_style(candidate, {"streetwear", "casual", "sporty"})
        if requested_occasion in {"work", "trabalho", "dinner", "jantar"}:
            return self._candidate_average_formality(candidate) >= 3.2
        return True

    def _candidate_quality_labels(
        self,
        candidate: Dict[str, Any],
        parsed_intent: Dict[str, Any],
    ) -> Tuple[List[str], List[str]]:
        breakdown = (candidate.get("metadata") or {}).get("score_breakdown") or {}
        strengths = []
        weaknesses = []

        if breakdown.get("request_match", 0) >= 24:
            strengths.append("strong request match")
        else:
            weaknesses.append("weaker request match")
        if breakdown.get("formality", 0) >= 12:
            strengths.append("aligned formality")
        elif self._normalized_requested_style(parsed_intent) in {"formal", "classic", "elegant"}:
            weaknesses.append("casual pieces reduce formality")
        if breakdown.get("style_consistency", 0) >= 12:
            strengths.append("consistent style")
        elif breakdown.get("style_consistency", 0) < 9:
            weaknesses.append("mixed style signals")
        if breakdown.get("color_harmony", 0) >= 9:
            strengths.append("good color harmony")
        elif breakdown.get("color_harmony", 0) < 6:
            weaknesses.append("less cohesive colors")
        if breakdown.get("weather", 0) >= 9:
            strengths.append("good weather fit")
        elif breakdown.get("weather", 0) < 7:
            weaknesses.append("weaker weather fit")
        if breakdown.get("completeness", 0) >= 12:
            strengths.append("complete outfit")
        if breakdown.get("section_correctness", 0) >= 10:
            strengths.append("correct sections")
        return strengths[:4], weaknesses[:3]

    def _normalized_requested_style(self, parsed_intent: Dict[str, Any]) -> str:
        style = (
            parsed_intent.get("requested_style")
            or self._first_list_value(parsed_intent.get("style"))
            or self._first_list_value(parsed_intent.get("requested_styles"))
        )
        text = self.candidate_outfit_service._normalize_text(style)
        if text in {"elegante", "elegant"}:
            return "elegant"
        if text in {"classico", "classica", "classic"}:
            return "classic"
        if text in {"desportivo", "sport", "sporty"}:
            return "sporty"
        return text

    def _normalized_requested_occasion(self, parsed_intent: Dict[str, Any]) -> str:
        occasion = (
            parsed_intent.get("requested_occasion")
            or self._first_list_value(parsed_intent.get("occasion"))
            or self._first_list_value(parsed_intent.get("requested_occasions"))
        )
        return self.candidate_outfit_service._normalize_text(occasion)

    def _first_list_value(self, value: Any) -> Any:
        if isinstance(value, list):
            return value[0] if value else None
        return value

    def _candidate_average_formality(self, candidate: Dict[str, Any]) -> float:
        values = [
            self._candidate_item_formality(item)
            for item in candidate.get("items", [])
        ]
        return sum(values) / len(values) if values else 0.0

    def _candidate_has_style(self, candidate: Dict[str, Any], accepted: set) -> bool:
        return any(
            self._candidate_item_style_label(item) in accepted
            for item in candidate.get("items", [])
        )

    def _candidate_item_formality(self, item: Dict[str, Any]) -> int:
        label = self._candidate_item_style_label(item)
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

    def _candidate_item_style_label(self, item: Dict[str, Any]) -> str:
        text = self.candidate_outfit_service._normalize_text(
            f"{item.get('style', '')} {item.get('occasion', '')} "
            f"{item.get('name', '')} {item.get('type', '')}"
        )
        if any(token in text for token in ["formal", "work", "elegant", "elegante", "camisa", "shirt", "blazer"]):
            return "formal"
        if any(token in text for token in ["classic", "classico", "classica", "classicas"]):
            return "classic"
        if "smart casual" in text:
            return "smart casual"
        if any(token in text for token in ["streetwear", "oversized", "stussy", "jordan"]):
            return "streetwear"
        if any(token in text for token in ["sport", "desportivo", "running", "jersey"]):
            return "sporty"
        return "casual"

    def _build_candidate_selection_reasoning(
        self,
        selected_candidate: Dict[str, Any],
        user_request: Optional[str],
        weather_data: Dict[str, Any],
    ) -> str:
        items = selected_candidate.get("items", [])
        temp = weather_data.get("temp", weather_data.get("temperature"))
        condition = weather_data.get("condition", "current")
        weather_phrase = (
            f"{condition} {temp}°C"
            if temp is not None
            else str(condition)
        )

        requested_mentions = self._requested_items_in_candidate(user_request, items)
        requested_names = set(requested_mentions)
        paired_names = self._unique_names([
            item.get("name")
            for item in items
            if item.get("name") and item.get("name") not in requested_names
        ])
        item_phrase = self._join_names(paired_names[:5])
        if requested_mentions:
            opening = f"Criei este look com {self._join_names(requested_mentions)} como pediste"
        elif user_request:
            opening = "Criei este look para responder ao teu pedido"
        else:
            opening = "Criei este look"

        result_style = self._candidate_result_style(user_request, items)
        if item_phrase:
            return (
                f"{opening} e combinei com {item_phrase} para um resultado "
                f"{result_style} adequado a {weather_phrase}."
            )
        return (
            f"{opening} para um resultado {result_style} adequado a {weather_phrase}."
        )

    def _candidate_result_style(
        self,
        user_request: Optional[str],
        items: List[Dict[str, Any]],
    ) -> str:
        if user_request:
            parsed = self.user_request_parser.parse_request(user_request)
            requested_style = parsed.get("requested_style")
            if requested_style:
                return str(requested_style)
        labels = []
        for item in items:
            text = self.candidate_outfit_service._normalize_text(
                f"{item.get('style', '')} {item.get('occasion', '')} "
                f"{item.get('name', '')} {item.get('type', '')}"
            )
            if any(token in text for token in ["formal", "work", "elegant", "elegante", "classico", "classica"]):
                labels.append("formal")
            elif any(token in text for token in ["streetwear", "jordan", "oversized"]):
                labels.append("streetwear")
            elif any(token in text for token in ["sport", "desportivo", "running", "jersey"]):
                labels.append("sporty")
            else:
                labels.append("casual")
        if labels.count("formal") >= max(1, len(labels) // 2):
            return "formal"
        if labels.count("streetwear") >= 2:
            return "streetwear"
        if labels.count("sporty") >= 2:
            return "sporty"
        return "casual"

    def _requested_items_in_candidate(
        self,
        user_request: Optional[str],
        items: List[Dict[str, Any]],
    ) -> List[str]:
        if not user_request:
            return []
        parsed = self.user_request_parser.parse_request(user_request)
        requested_items = parsed.get("must_include_items") or []
        matches = []
        for request in requested_items:
            req_color = self.candidate_outfit_service.normalize_color(request.get("color"))
            req_section = self.candidate_outfit_service.normalize_type(request.get("type"))
            req_name = self.candidate_outfit_service._normalize_text(request.get("name"))
            for item in items:
                item_color = self.candidate_outfit_service.normalize_color(item.get("color"))
                item_section = item.get("section")
                item_name = self.candidate_outfit_service._normalize_text(item.get("name"))
                if req_section and item_section != req_section:
                    continue
                if req_color and item_color != req_color:
                    continue
                if req_name and req_name not in item_name:
                    continue
                if item.get("name") and item.get("name") not in matches:
                    matches.append(item.get("name"))
        return matches

    def _unique_names(self, names: List[str]) -> List[str]:
        unique = []
        seen = set()
        for name in names:
            if not name or name in seen:
                continue
            unique.append(name)
            seen.add(name)
        return unique

    def build_clean_reasoning(
        self,
        validated_items: List[Any],
        weather: Dict[str, Any],
        preferences: Optional[Dict[str, Any]] = None,
        must_include_items: Optional[List[Dict[str, Any]]] = None,
        user_request_text: Optional[str] = None,
        original_reasoning: Optional[str] = None,
    ) -> str:
        """
        Build a short, clean user-facing reasoning string from validated metadata.
        If original reasoning is messy or conflicts with metadata, ignore it.
        """
        preferences = preferences or {}
        temperature = weather.get("temperature", weather.get("temp"))
        condition = weather.get("condition", "current")
        style = preferences.get("style")
        item_names = [item.name for item in validated_items if getattr(item, "name", None)]
        named_items = self._join_names(item_names[:4])
        weather_phrase = (
            f"{condition} {temperature}°C weather"
            if temperature is not None
            else f"{condition} weather"
        )

        if not item_names:
            return "I picked clean pieces that work for today's weather."

        must_include_names = [
            item.get("name")
            for item in (must_include_items or [])
            if item.get("name")
        ]
        if must_include_names:
            requested = self._join_names(must_include_names)
            rest_names = [
                name for name in item_names if name not in set(must_include_names)
            ]
            rest_phrase = (
                f"with {self._join_names(rest_names[:3])}"
                if rest_names
                else "as the focus"
            )
            reason = (
                f"This outfit includes your {requested} as requested, "
                f"{rest_phrase} for {weather_phrase}."
            )
            out_of_range = []
            if temperature is not None:
                must_include_ids = {
                    item.get("id") for item in (must_include_items or []) if item.get("id")
                }
                for item in validated_items:
                    if getattr(item, "id", None) in must_include_ids:
                        try:
                            if not (float(item.temp_min) <= float(temperature) <= float(item.temp_max)):
                                out_of_range.append(item.name)
                        except (TypeError, ValueError):
                            pass
            if out_of_range:
                reason += f" Note: {self._join_names(out_of_range)} is outside its saved temperature range."
            return reason

        if style:
            return f"I kept this outfit {style} with {named_items}, suitable for {weather_phrase}."

        if user_request_text:
            return f"This outfit follows your request with {named_items}, suitable for {weather_phrase}."

        return f"This outfit combines {named_items} for {weather_phrase}."

    def _print_intent_debug(self, parsed_constraints: Dict[str, Any]) -> None:
        must_include = parsed_constraints.get("must_include", {})
        print(
            "[IntentDebug] parsed_intent "
            f"requested_type={must_include.get('type')} "
            f"requested_color={must_include.get('color')} "
            f"requested_style={parsed_constraints.get('style')}"
        )

    def _print_wardrobe_debug(self, wardrobe: List[Dict[str, Any]]) -> None:
        print(f"[IntentDebug] wardrobe_loaded count={len(wardrobe)}")
        for item in wardrobe:
            temperature_range = item.get("temperature_range") or {}
            temp_min = item.get("temp_min", item.get("tempMin", temperature_range.get("min")))
            temp_max = item.get("temp_max", item.get("tempMax", temperature_range.get("max")))
            print(
                "[IntentDebug] wardrobe_item "
                f"id={item.get('id')} "
                f"name={item.get('name')} "
                f"type={item.get('type')} "
                f"color={item.get('color')} "
                f"style={item.get('style')} "
                f"occasion={item.get('occasion')} "
                f"status={item.get('status')} "
                f"layer={item.get('layer')} "
                f"temp_min={temp_min} "
                f"temp_max={temp_max} "
                f"user_id={item.get('user_id')} "
                f"is_public={item.get('is_public')}"
            )

    def _print_command_debug(
        self,
        parsed_constraints: Dict[str, Any],
        wardrobe: List[Dict[str, Any]],
        user_id: str,
        temperature: float,
        excluded_ids: set,
    ) -> None:
        print(f"[CommandResolver] parsed_intent={parsed_constraints.get('intent', parsed_constraints)}")
        required_type = (parsed_constraints.get("requested_types") or [None])[0]
        required_color = (parsed_constraints.get("requested_colors") or [None])[0]
        for item in wardrobe:
            reasons = self._item_rejection_reasons(
                item=item,
                required_type=required_type,
                required_color=required_color,
                user_id=user_id,
                temperature=temperature,
                excluded_ids=excluded_ids,
            )
            raw_type = item.get("type")
            raw_color = item.get("color")
            normalized_type = self.constraint_matching_service._canonical_type(raw_type)
            normalized_color = self.constraint_matching_service._normalize_color(raw_color or "")
            type_match = (
                True if not required_type
                else self.constraint_matching_service._type_matches(raw_type, required_type)
            )
            color_match = (
                True if not required_color
                else self.constraint_matching_service._item_color_matches(item, required_color)
            )
            status_match = item.get("status", "clean") == "clean"
            item_user_id = item.get("user_id")
            user_match = not item_user_id or str(item_user_id) == str(user_id)
            print(
                "[CommandResolver] wardrobe_item "
                f"name={item.get('name')} "
                f"id={item.get('id')} "
                f"raw_type={raw_type} "
                f"normalized_type={normalized_type} "
                f"raw_color={raw_color} "
                f"normalized_color={normalized_color} "
                f"style={item.get('style')} "
                f"occasion={item.get('occasion')} "
                f"status={item.get('status')} "
                f"layer={item.get('layer')} "
                f"user_id={item.get('user_id')} "
                f"type_match={type_match} "
                f"color_match={color_match} "
                f"status_match={status_match} "
                f"user_match={user_match} "
                f"final_match={not reasons} "
                f"reject_reason={'matched' if not reasons else ','.join(reasons)}"
            )

    def _print_footwear_color_debug(
        self,
        parsed_constraints: Dict[str, Any],
        wardrobe: List[Dict[str, Any]],
        user_id: str,
        temperature: float,
        excluded_ids: set,
    ) -> None:
        requested_types = set(parsed_constraints.get("requested_types") or [])
        requested_colors = set(parsed_constraints.get("requested_colors") or [])
        is_yellow_footwear_request = (
            bool(requested_colors.intersection({"yellow"}))
            and bool(requested_types.intersection({"sneakers", "shoes", "boots", "sandals"}))
        )
        if not is_yellow_footwear_request:
            return

        for item in wardrobe:
            type_is_footwear = any(
                self.constraint_matching_service._type_matches(item.get("type", ""), footwear_type)
                for footwear_type in ("sneakers", "shoes", "boots", "sandals")
            )
            section_is_footwear = self._item_section(item) == "shoes"
            if not type_is_footwear and not section_is_footwear:
                continue

            raw_color = item.get("color")
            normalized_color = self.constraint_matching_service._normalize_color(raw_color or "")
            type_match = any(
                self.constraint_matching_service._type_matches(item.get("type", ""), requested_type)
                for requested_type in requested_types
            )
            color_match = self.constraint_matching_service._item_color_matches(item, "yellow")
            reasons = self._item_rejection_reasons(
                item=item,
                required_type="sneakers" if "sneakers" in requested_types else "shoes",
                required_color="yellow",
                user_id=user_id,
                temperature=temperature,
                excluded_ids=excluded_ids,
            )
            print(
                "[FootwearColorDebug] "
                f"id={item.get('id')} "
                f"name={item.get('name')} "
                f"type={item.get('type')} "
                f"raw_color={raw_color!r} "
                f"normalized_color={normalized_color!r} "
                f"status={item.get('status')} "
                f"type_match={type_match} "
                f"color_match={color_match} "
                f"rejection_reason={'matched' if not reasons else ','.join(reasons)}"
            )

    def _resolve_mandatory_constraints(
        self,
        parsed_constraints: Dict[str, Any],
        wardrobe: List[Dict[str, Any]],
        user_id: str,
        temperature: float,
        excluded_ids: set,
    ) -> Dict[str, Any]:
        """Resolve mandatory user constraints before LLaVA is allowed to run."""
        resolved_items: List[Dict[str, Any]] = []
        requested_items = parsed_constraints.get("must_include_items") or []

        for requested in requested_items:
            required_type = requested.get("type")
            required_color = requested.get("color")
            required_name = requested.get("name")

            matches = []
            diagnostics = []
            for item in wardrobe:
                if required_name and not self._name_matches(item, required_name):
                    reasons = ["name_mismatch"]
                else:
                    reasons = self._item_rejection_reasons(
                        item=item,
                        required_type=required_type,
                        required_color=required_color,
                        user_id=user_id,
                        temperature=temperature,
                        excluded_ids=excluded_ids,
                        enforce_temperature=False,
                    )
                diagnostics.append((item, reasons))
                if not reasons:
                    matches.append(item)

            if not matches:
                return {
                    "error": self._mandatory_failure_message(
                        requested=requested,
                        diagnostics=diagnostics,
                    )
                }

            selected = self._select_best_resolved_item(matches)
            resolved_items.append({
                "id": selected.get("id"),
                "name": selected.get("name"),
                "type": selected.get("type"),
                "color": selected.get("color"),
                "constraint_match": self._constraint_label(required_type, required_color, required_name),
                "original_item": selected,
            })

        return {"items": resolved_items}

    async def debug_deterministic_matcher(
        self,
        user_id: str,
        temperature: float = 20,
    ) -> Dict[str, Any]:
        """Backend-only matcher probe for real wardrobe rows, without LLaVA."""
        wardrobe = await self.wardrobe_service.get_user_wardrobe(
            user_id=user_id,
            only_clean=False,
            exclude_item_ids=None,
        )

        requests = [
            {
                "request": "quero um outfit com sapatilhas amarelas",
                "expected": "Mexico 66 yellow",
            },
            {
                "request": "da me um look com um casaco verde",
                "expected": "casaco com botoes",
            },
            {
                "request": "da me um look com um casaco azul",
                "expected": "Casaco Classico azul",
            },
            {
                "request": "da me um look mais formal",
                "expected_candidates": [
                    "casaco com botoes",
                    "Casaco Classico azul",
                    "Calças classicas",
                ],
            },
        ]

        results = []
        for test in requests:
            parsed = self.user_request_parser.parse_request(test["request"])
            requested_type = (parsed.get("requested_types") or [None])[0]
            requested_color = (parsed.get("requested_colors") or [None])[0]
            item_logs = []

            for item in wardrobe:
                reasons = self._item_rejection_reasons(
                    item=item,
                    required_type=requested_type,
                    required_color=requested_color,
                    user_id=user_id,
                    temperature=temperature,
                    excluded_ids=set(),
                    enforce_temperature=False,
                )
                raw_type = item.get("type")
                raw_color = item.get("color")
                normalized_type = self.constraint_matching_service._canonical_type(raw_type)
                normalized_color = self.constraint_matching_service._normalize_color(raw_color or "")
                type_match = (
                    True if not requested_type
                    else self.constraint_matching_service._type_matches(raw_type, requested_type)
                )
                color_match = (
                    True if not requested_color
                    else self.constraint_matching_service._item_color_matches(item, requested_color)
                )
                status_match = item.get("status", "clean") == "clean"
                item_user_id = item.get("user_id")
                user_match = not item_user_id or str(item_user_id) == str(user_id)
                final_match = not reasons
                log = {
                    "name": item.get("name"),
                    "id": item.get("id"),
                    "raw_type": raw_type,
                    "normalized_type": normalized_type,
                    "raw_color": raw_color,
                    "normalized_color": normalized_color,
                    "type_match": type_match,
                    "color_match": color_match,
                    "status_match": status_match,
                    "user_match": user_match,
                    "final_match": final_match,
                    "reject_reason": "matched" if final_match else ",".join(reasons),
                }
                item_logs.append(log)
                print(
                    "[MatcherDebugTest] "
                    f"request={test['request']!r} "
                    f"name={log['name']} "
                    f"raw_type={raw_type} normalized_type={normalized_type} "
                    f"raw_color={raw_color} normalized_color={normalized_color} "
                    f"type_match={type_match} color_match={color_match} "
                    f"status_match={status_match} user_match={user_match} "
                    f"final_match={final_match} reject_reason={log['reject_reason']}"
                )

            if parsed.get("requested_style") == "formal":
                formal_candidates = [
                    item for item in wardrobe
                    if item.get("status", "clean") == "clean"
                    and str(item.get("user_id")) == str(user_id)
                    and self._looks_formal_dict(item)
                ]
                penalized = [
                    item for item in wardrobe
                    if self._looks_sporty_or_casual_dict(item)
                ]
                result = {
                    "request": test["request"],
                    "parsed_intent": parsed.get("intent", parsed),
                    "matches": [item.get("name") for item in formal_candidates],
                    "penalized": [item.get("name") for item in penalized],
                    "item_logs": item_logs,
                    "expected_candidates": test.get("expected_candidates", []),
                }
            else:
                matches = [
                    item_log["name"] for item_log in item_logs
                    if item_log["final_match"]
                ]
                result = {
                    "request": test["request"],
                    "parsed_intent": parsed.get("intent", parsed),
                    "matches": matches,
                    "expected": test.get("expected"),
                    "item_logs": item_logs,
                }
            results.append(result)

        return {
            "user_id": user_id,
            "wardrobe_count": len(wardrobe),
            "wardrobe_items": [
                {
                    "id": item.get("id"),
                    "user_id": item.get("user_id"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "normalized_type": self.constraint_matching_service._canonical_type(item.get("type")),
                    "color": item.get("color"),
                    "normalized_color": self.constraint_matching_service._normalize_color(item.get("color") or ""),
                    "style": item.get("style"),
                    "occasion": item.get("occasion"),
                    "status": item.get("status"),
                    "layer": item.get("layer"),
                }
                for item in wardrobe
            ],
            "tests": results,
        }

    def _item_rejection_reasons(
        self,
        item: Dict[str, Any],
        required_type: Optional[str],
        required_color: Optional[str],
        user_id: str,
        temperature: float,
        excluded_ids: set,
        enforce_temperature: bool = False,
    ) -> List[str]:
        reasons = []
        item_user_id = item.get("user_id")
        if item_user_id and str(item_user_id) != str(user_id):
            reasons.append("wrong_user")
        if item.get("id") in excluded_ids:
            reasons.append("excluded")
        if required_type and not self.constraint_matching_service._type_matches(
            item.get("type", ""), required_type
        ):
            reasons.append("type_mismatch")
        if required_color and not self.constraint_matching_service._item_color_matches(
            item, required_color
        ):
            reasons.append("color_mismatch")
        if item.get("status", "clean") != "clean":
            reasons.append("dirty")
        if enforce_temperature and not self.constraint_matching_service._temp_allowed(
            item,
            debug_context={"temperature": temperature},
        ):
            reasons.append("temp_mismatch")
        return reasons

    def _mandatory_failure_message(
        self,
        requested: Dict[str, Any],
        diagnostics: List[Any],
    ) -> str:
        required_type = requested.get("type")
        required_color = requested.get("color")
        required_name = requested.get("name")
        label = self._constraint_label(required_type, required_color, required_name)

        type_candidates = [
            item for item, reasons in diagnostics
            if not required_type or "type_mismatch" not in reasons
        ]
        color_candidates = [
            item for item, reasons in diagnostics
            if not required_color or "color_mismatch" not in reasons
        ]
        type_color_candidates = [
            (item, reasons) for item, reasons in diagnostics
            if (
                (not required_type or "type_mismatch" not in reasons)
                and (not required_color or "color_mismatch" not in reasons)
                and (not required_name or "name_mismatch" not in reasons)
            )
        ]

        if required_type and not type_candidates:
            return f"I could not find any {self._type_label(required_type)} in your wardrobe."
        if required_color and required_type and not type_color_candidates:
            if type_candidates and not any(item in color_candidates for item in type_candidates):
                return f"I found {self._type_label(required_type)} in your wardrobe, but none are {required_color}."
            return f"I could not find {self._article_for(required_type)}{label} in your wardrobe."
        if type_color_candidates:
            if any("wrong_user" in reasons for _, reasons in type_color_candidates):
                return f"I found {label}, but it belongs to another user."
            if any("dirty" in reasons for _, reasons in type_color_candidates):
                return f"I found {label}, but it is not clean."
            if any("temp_mismatch" in reasons for _, reasons in type_color_candidates):
                return f"I found {label}, but it is outside the current temperature range."
            if any("excluded" in reasons for _, reasons in type_color_candidates):
                return f"I found {label}, but it is currently excluded."
        if required_color:
            return f"I could not find any {required_color} pieces in your wardrobe."
        if required_name:
            return f"I could not find {required_name} in your wardrobe."
        return "I could not find matching items in your wardrobe."

    def _select_best_resolved_item(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        return sorted(
            items,
            key=lambda item: (
                bool(item.get("favorite")),
                -((item.get("usage_metrics") or {}).get("usage_frequency_last_7_days", 0) or 0),
                item.get("name") or "",
            ),
            reverse=True,
        )[0]

    def _name_matches(self, item: Dict[str, Any], requested_name: str) -> bool:
        requested = self.constraint_matching_service._normalize_text(requested_name)
        item_name = self.constraint_matching_service._normalize_text(item.get("name", ""))
        return item_name == requested or requested in item_name or item_name in requested

    def _constraint_label(
        self,
        required_type: Optional[str],
        required_color: Optional[str],
        required_name: Optional[str] = None,
    ) -> str:
        if required_name:
            return required_name
        if required_color and required_type:
            return f"{required_color} {self._type_label(required_type)}"
        if required_type:
            return self._type_label(required_type)
        if required_color:
            return f"{required_color} piece"
        return "matching item"

    def _type_label(self, item_type: str) -> str:
        labels = {
            "jacket": "jacket",
            "sneakers": "sneakers",
            "shoes": "shoes",
            "pants": "pants",
            "tshirt": "t-shirt",
            "t-shirt": "t-shirt",
            "sweater": "sweater",
            "shirt": "shirt",
            "shorts": "shorts",
            "accessories": "accessories",
        }
        return labels.get(item_type, item_type)

    def _article_for(self, item_type: Optional[str]) -> str:
        if item_type in {"sneakers", "shoes", "pants", "shorts", "accessories"}:
            return ""
        return "a "

    def _missing_constraint_message(self, constraints: Dict[str, Any]) -> str:
        must_include = constraints.get("must_include", {})
        colors = must_include.get("color") or []
        types = must_include.get("type") or []
        color = colors[0] if colors else None
        item_type = types[0] if types else None

        if color and item_type:
            article = "" if item_type in {"sneakers", "shoes", "pants", "shorts", "accessories"} else "a "
            return f"I could not find {article}{color} {item_type} in your wardrobe."
        if color:
            return f"I could not find any {color} pieces in your wardrobe."
        if item_type:
            return f"I could not find any clean {item_type} in your wardrobe."
        return "I could not find matching items in your wardrobe."

    async def recommend_travel_outfits(
        self,
        user_id: str,
        destination: str,
        start_date: datetime,
        end_date: datetime,
        weather_forecast: Optional[List[Dict[str, Any]]] = None,
        luggage_limit: int = 10,
        preferences: Optional[Dict[str, Any]] = None,
        exclude_items: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate travel outfit recommendations.

        Phase 2 Flow:
        1. Prepare AI-ready context for travel using DataPreparationService
        2. Context includes weather forecast, luggage constraints, versatile items
        3. Pass context to VLM or fallback logic
        4. Return packing list and daily outfit suggestions

        Args:
            user_id: User's ID
            destination: Travel destination
            start_date: Start date of trip
            end_date: End date of trip
            weather_forecast: Optional weather forecast (will be fetched if not provided)
            luggage_limit: Maximum items to pack
            preferences: Optional user preferences
            exclude_items: Optional item IDs to exclude

        Returns:
            Dictionary with recommended outfits and packing list
        """
        try:
            # Phase 2: Prepare AI-ready context for travel
            ai_context = await self.data_preparation_service.prepare_travel_context(
                user_id=user_id,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                luggage_limit=luggage_limit,
                user_preferences=preferences,
                exclude_items=exclude_items,
            )

            # Check if we have items
            if not ai_context.get_all_items():
                return self._create_error_response(
                    "No suitable wardrobe items available for travel planning"
                )

            # Call VLM
            vlm_responses = await self.vlm_service.recommend_travel_outfits(
                wardrobe_items=[item.to_dict() for item in ai_context.get_all_items()],
                weather_forecast=[w.to_dict() for w in ai_context.weather_forecast],
                num_days=(end_date - start_date).days + 1,
                user_context={
                    "preferences": ai_context.user_constraints.get("preferences", {}),
                    "destination": destination,
                },
            )

            # Phase 4: Validate VLM responses
            logger.info(
                f"Validating travel VLM responses with {len(vlm_responses)} days"
            )

            # Build wardrobe by ID map for validation
            wardrobe_by_id = {item.id: item for item in ai_context.get_all_items()}

            validation_result = await self._validate_travel_vlm_response(
                vlm_responses, ai_context, wardrobe_by_id
            )

            if not validation_result["valid"]:
                logger.warning(
                    f"Travel validation failed. Errors: {validation_result['errors']}. "
                    f"Warnings: {validation_result['warnings']}"
                )

                # For travel, if validation fails, use fallback
                logger.warning("Travel validation failed. Using fallback.")
                result = await self._fallback_travel_recommendation_from_context(
                    ai_context
                )
                return result
            else:
                logger.info("Travel validation succeeded.")

            # Build outfits from validated responses
            daily_outfits = []
            packing_items = {}

            for valid_resp in validation_result["valid_responses"]:
                day_outfit = [item.to_dict() for item in valid_resp["items"]]
                daily_outfits.append(
                    {
                        "day": valid_resp["day"],
                        "items": day_outfit,
                        "reasoning": valid_resp["response"].reasoning,
                    }
                )
                for item in valid_resp["items"]:
                    packing_items[item.id] = item.to_dict()

            if not daily_outfits:
                logger.warning("No valid daily outfits after validation, falling back.")
                return await self._fallback_travel_recommendation_from_context(
                    ai_context
                )

            return {
                "success": True,
                "travel_plan": {
                    "daily_outfits": daily_outfits,
                    "packing_list": list(packing_items.values()),
                    "packing_notes": "AI optimized capsule wardrobe.",
                },
                "model_used": "llava",
                "context_used": "ai_ready_context",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Error in travel recommendation: {e}")
            return self._create_error_response(
                f"Travel recommendation failed: {str(e)}"
            )

    async def recommend_alternatives(
        self,
        user_id: str,
        current_outfit_item_ids: List[str],
        temperature: float,
        weather_condition: str,
        humidity: Optional[float] = None,
        wind_speed: Optional[float] = None,
        num_alternatives: int = 3,
        preferences: Optional[Dict[str, Any]] = None,
        exclude_items: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate alternative outfit suggestions.

        Phase 2 Flow:
        1. Prepare AI-ready context with alternatives focus
        2. Deprioritize items from current outfit
        3. Pass context to VLM or fallback logic
        4. Return alternative outfit suggestions

        Args:
            user_id: User's ID
            current_outfit_item_ids: Item IDs in current outfit
            temperature: Current temperature
            weather_condition: Weather condition
            humidity: Optional humidity
            wind_speed: Optional wind speed
            num_alternatives: Number of alternatives to suggest
            preferences: Optional user preferences
            exclude_items: Optional item IDs to exclude

        Returns:
            Dictionary with alternative outfit suggestions
        """
        try:
            variation_exclude_items = list(
                {
                    *(exclude_items or []),
                    *(current_outfit_item_ids or []),
                }
            )

            # Phase 2: Prepare AI-ready context for alternatives
            ai_context = (
                await self.data_preparation_service.prepare_alternative_context(
                    user_id=user_id,
                    current_outfit_items=current_outfit_item_ids,
                    temperature=temperature,
                    weather_condition=weather_condition,
                    num_alternatives=num_alternatives,
                    user_preferences=preferences,
                    exclude_items=variation_exclude_items,
                )
            )

            # Check if we have alternatives
            if not ai_context.get_all_items():
                return self._create_error_response(
                    "No alternative wardrobe items available"
                )

            # Call VLM
            all_items = ai_context.get_all_items()
            items_by_id = {item.id: item for item in all_items}
            vlm_responses = await self.vlm_service.recommend_alternatives(
                current_outfit_items=[
                    items_by_id[i].to_dict()
                    for i in current_outfit_item_ids
                    if i in items_by_id
                ],
                all_wardrobe_items=[
                    item.to_dict() for item in ai_context.get_all_items()
                ],
                weather_context=ai_context.weather_current.to_dict()
                if ai_context.weather_current
                else {},
                num_alternatives=num_alternatives,
                user_context={
                    "preferences": ai_context.user_constraints.get("preferences", {}),
                    "excluded_items": variation_exclude_items,
                },
            )

            # Phase 4: Validate VLM responses
            logger.info(f"Validating {len(vlm_responses)} alternative outfit responses")

            # Build wardrobe by ID map for validation
            wardrobe_by_id = {item.id: item for item in ai_context.get_all_items()}

            validation_result = await self._validate_alternatives_vlm_responses(
                vlm_responses, ai_context, wardrobe_by_id
            )

            if not validation_result["valid"]:
                logger.warning(
                    f"Alternatives validation failed. Errors: {validation_result['errors']}"
                )

                # For alternatives, use fallback if validation fails
                logger.warning("Alternatives validation failed. Using fallback.")
                result = await self._fallback_alternative_recommendation_from_context(
                    ai_context, num_alternatives
                )
                return result
            else:
                logger.info("Alternatives validation succeeded.")

            # Build alternatives from validated responses
            alternatives = []
            for valid_alt in validation_result.get("valid_alternatives", []):
                alt_items = [item.to_dict() for item in valid_alt["items"]]
                alternatives.append(
                    {"items": alt_items, "reasoning": valid_alt["response"].reasoning}
                )

            if not alternatives:
                logger.warning("No valid alternatives after validation, falling back.")
                return await self._fallback_alternative_recommendation_from_context(
                    ai_context, num_alternatives
                )

            return {
                "success": True,
                "alternatives": alternatives,
                "model_used": "llava",
                "context_used": "ai_ready_context",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in alternative recommendation: {e}", exc_info=True)
            print(f"Error in alternative recommendation: {e}")
            return self._create_error_response(
                f"Alternative recommendation failed: {str(e)}"
            )

    # ========================================================================
    # VALIDATION METHODS (Ensure VLM responses are valid and safe)
    # ========================================================================

    async def _validate_vlm_response(
        self,
        vlm_response,
        parsed_result: Dict[str, Any],
        ai_context,
        wardrobe_items_by_id: Dict[str, Any],
        temperature: float,
        weather_condition: str,
    ) -> Dict[str, Any]:
        """
        Validate VLM response against wardrobe and layer rules.

        Checks:
        1. Items exist in wardrobe
        2. Items are not dirty/damaged
        3. Items are suitable for weather conditions
        4. Items are suitable for temperature range
        5. No duplicate items
        6. Minimum item count (at least 2-3 items)
        7. At least basic layer coverage

        Args:
            vlm_response: Response from VLM service
            ai_context: AIReadyContext with enriched wardrobe data
            wardrobe_items_by_id: Mapping of item IDs to item data
            temperature: Current temperature
            weather_condition: Current weather condition

        Returns:
            Dictionary with structure:
            {
                "valid": bool,
                "items": List of valid AIReadyItem objects,
                "errors": List of error strings,
                "warnings": List of warning strings,
                "retry_count": int,
            }
        """
        errors = []
        warnings = []
        valid_items = []
        seen_ids = set()
        parsed_item_ids = parsed_result.get("item_ids", [])
        mandatory_item_ids = set(
            ai_context.user_constraints.get("must_include_ids", [])
        )
        layer_assignments = parsed_result.get(
            "layer_assignments", {1: [], 2: [], 3: [], "shoes": [], "accessories": []}
        )
        mandatory_section_by_id = {}
        for item_id in mandatory_item_ids:
            mandatory_item = wardrobe_items_by_id.get(item_id)
            if mandatory_item:
                mandatory_section_by_id[item_id] = self._json_section_for_item(mandatory_item)

        logger.info(
            f"Validating VLM response with parsed items={len(parsed_item_ids)}"
        )
        logger.debug(f"Raw VLM outfit items: {vlm_response.outfit_items}")
        logger.debug(f"Parsed VLM item ids: {parsed_item_ids}")

        # Check 1: Item exists in wardrobe
        for item_id in parsed_item_ids:
            if item_id not in wardrobe_items_by_id:
                error_msg = f"Item {item_id} not found in wardrobe"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue

            item = wardrobe_items_by_id[item_id]

            # Check 2: Item is not dirty/damaged
            if item.status == "dirty":
                error_msg = f"Item '{item.name}' ({item_id}) is dirty"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue

            if item.status == "damaged":
                error_msg = f"Item '{item.name}' ({item_id}) is damaged"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue

            # Check 3: Weather compatibility (for outer layers)
            if not item.is_suitable_for_weather(weather_condition):
                error_msg = (
                    f"Item '{item.name}' ({item_id}) not suitable "
                    f"for {weather_condition} weather"
                )
                errors.append(error_msg)
                logger.warning(error_msg)
                continue

            # Check 4: Temperature compatibility
            if not item.is_suitable_for_temperature(temperature - 5, temperature + 5):
                message = (
                    f"Item '{item.name}' ({item_id}) temp range "
                    f"[{item.temp_min}°C - {item.temp_max}°C] "
                    f"does not match current temp {temperature}°C"
                )
                if item_id in mandatory_item_ids:
                    warning_msg = f"Mandatory item kept despite temperature mismatch: {message}"
                    warnings.append(warning_msg)
                    logger.warning(warning_msg)
                else:
                    errors.append(message)
                    logger.warning(message)
                    continue

            # Check 5: No duplicates
            if item_id in seen_ids:
                warning_msg = f"Duplicate item detected: {item.name} ({item_id})"
                warnings.append(warning_msg)
                logger.warning(warning_msg)
                continue

            assigned_section = self._assigned_section_for_item_id(item_id, layer_assignments)
            if assigned_section and not self._item_allowed_in_assigned_section(item, assigned_section):
                error_msg = (
                    f"Item '{item.name}' ({item_id}) is not valid for JSON section "
                    f"{assigned_section}"
                )
                errors.append(error_msg)
                logger.warning(error_msg)
                continue

            mandatory_section = mandatory_section_by_id.get(item_id)
            if mandatory_section and assigned_section and assigned_section != mandatory_section:
                error_msg = (
                    f"Mandatory item '{item.name}' ({item_id}) was assigned to "
                    f"{assigned_section}, expected {mandatory_section}"
                )
                errors.append(error_msg)
                logger.warning(error_msg)
                continue

            seen_ids.add(item_id)
            valid_items.append(item)
            logger.debug(f"Item {item.name} ({item_id}) validated successfully")

        # Check 6: No more than one item per main section
        for layer_key, ids in layer_assignments.items():
            if len(ids) > 1:
                errors.append(f"Too many items in section {layer_key}: {ids}")

        for mandatory_id, mandatory_section in mandatory_section_by_id.items():
            section_ids = set(layer_assignments.get(mandatory_section, []))
            if mandatory_id not in section_ids:
                errors.append(
                    f"Mandatory item {mandatory_id} must be selected in section "
                    f"{mandatory_section}"
                )
            competing_ids = [
                item_id for item_id in section_ids
                if item_id != mandatory_id
            ]
            if competing_ids:
                errors.append(
                    f"Mandatory section {mandatory_section} contains competing item(s) "
                    f"{competing_ids}; expected only {mandatory_id}"
                )

        # Check 7: Minimum item count
        if len(valid_items) < 1:
            error_msg = (
                f"Too few valid items returned ({len(valid_items)}). "
                f"Need at least 1 valid item for a recommendation."
            )
            errors.append(error_msg)
            logger.error(error_msg)

        requested_style = (
            ai_context.user_constraints.get("preferences", {}).get("style")
            if ai_context.user_constraints
            else None
        )
        if requested_style and not self._items_match_requested_style(
            valid_items, requested_style
        ):
            error_msg = f"Outfit does not match requested {requested_style} style"
            errors.append(error_msg)
            logger.warning(error_msg)

        # Check 8: Reasoning cleanup
        cleaned_reasoning = self.response_parser._clean_reasoning(
            parsed_result.get("reasoning", "")
        )
        if not cleaned_reasoning:
            warnings.append("Reasoning was empty after cleanup")

        is_valid = len(errors) == 0

        logger.info(
            f"Validation result: valid={is_valid}, "
            f"items={len(valid_items)}, errors={len(errors)}, warnings={len(warnings)}"
        )

        return {
            "valid": is_valid,
            "items": valid_items,
            "errors": errors,
            "warnings": warnings,
            "retry_count": 0,
            "reasoning": cleaned_reasoning,
        }

    def _assigned_section_for_item_id(
        self,
        item_id: str,
        layer_assignments: Dict[Any, List[str]],
    ) -> Optional[Any]:
        for section, ids in (layer_assignments or {}).items():
            if item_id in ids:
                return section
        return None

    def _json_section_for_item(self, item: Any) -> Any:
        section = self._item_section(item)
        if section == "shoes":
            return "shoes"
        if section in {"dress", "skirt", "jumpsuit", "bag"}:
            return section
        if section == "accessories":
            return "accessories"
        if section == "pants":
            return 2
        if section == "outer":
            return 3
        return 1

    def _item_allowed_in_assigned_section(self, item: Any, section: Any) -> bool:
        actual_section = self._item_section(item)
        if section == "shoes":
            return actual_section == "shoes"
        if section in {"dress", "skirt", "jumpsuit", "bag"}:
            return actual_section == section
        if section == "accessories":
            return actual_section == "accessories"
        if section == 3:
            return actual_section == "outer"
        if section == 2:
            return actual_section == "pants" or actual_section == "insulation"
        if section == 1:
            return actual_section == "base" or actual_section == "insulation"
        return True

    def _items_match_requested_style(
        self, items: List[Any], requested_style: Any
    ) -> bool:
        """Check lightweight style intent without exposing it to the user."""
        if isinstance(requested_style, list):
            requested_style = " ".join(str(style) for style in requested_style)
        requested_style = str(requested_style or "").lower()

        if not requested_style:
            return True

        style_keywords = {
            "formal": {
                "positive": [
                    "formal",
                    "camisa",
                    "blazer",
                    "suit",
                    "shirt",
                    "dress",
                    "trouser",
                    "calcas",
                    "calças",
                    "chino",
                    "loafer",
                    "oxford",
                    "jacket",
                    "coat",
                    "work",
                    "office",
                    "business",
                    "boots",
                    "sapatos",
                    "botas",
                ],
                "negative": [
                    "t-shirt",
                    "tshirt",
                    "tee",
                    "jersey",
                    "sneaker",
                    "sneakers",
                    "sapatilhas",
                    "hoodie",
                    "sportswear",
                    "gym",
                    "sport",
                    "sporty",
                    "desportivo",
                    "athletic",
                    "air jordan",
                ],
            },
            "casual": {
                "positive": [
                    "casual",
                    "t-shirt",
                    "tshirt",
                    "tee",
                    "jeans",
                    "sneaker",
                    "sneakers",
                    "hoodie",
                    "denim",
                ],
                "negative": ["suit", "blazer", "formal", "business"],
            },
        }

        matched_styles = [
            style for style in style_keywords if style in requested_style
        ]
        if not matched_styles:
            return True

        for style in matched_styles:
            profile = style_keywords[style]
            positive_items = 0
            negative_items = 0

            for item in items:
                text = (
                    f"{getattr(item, 'name', '')} {getattr(item, 'type', '')} "
                    f"{getattr(item, 'style', '')} {getattr(item, 'occasion', '')}"
                ).lower()
                if any(keyword in text for keyword in profile["positive"]):
                    positive_items += 1
                if any(keyword in text for keyword in profile["negative"]):
                    negative_items += 1

            if style == "formal":
                has_formal_alternatives = any(
                    any(keyword in (
                        f"{getattr(item, 'name', '')} {getattr(item, 'type', '')} "
                        f"{getattr(item, 'style', '')} {getattr(item, 'occasion', '')}"
                    ).lower() for keyword in profile["positive"])
                    for item in items
                )
                if has_formal_alternatives:
                    return positive_items > 0 and negative_items == 0
                return positive_items > 0 and positive_items > negative_items

            return positive_items > 0

        return True

    def _normalize_candidate_section(self, section: Optional[str]) -> Optional[str]:
        if not section:
            return None
        normalized = str(section).strip().lower()
        return {
            "base": "base_layer",
            "top": "base_layer",
            "tops": "base_layer",
            "base_layer": "base_layer",
            "dress": "dress",
            "skirt": "skirt",
            "jumpsuit": "jumpsuit",
            "bag": "bag",
            "insulation": "insulation_layer",
            "mid_layer": "insulation_layer",
            "insulation_layer": "insulation_layer",
            "pants": "pants",
            "trousers": "pants",
            "jeans": "pants",
            "outer": "outer_layer",
            "outerwear": "outer_layer",
            "jacket": "outer_layer",
            "coat": "outer_layer",
            "outer_layer": "outer_layer",
            "shoes": "shoes",
            "footwear": "shoes",
            "sneakers": "shoes",
            "accessory": "accessories",
            "accessories": "accessories",
            "one_item": "one_item",
        }.get(normalized, normalized)

    def _normalize_candidate_sections(self, sections: List[str]) -> List[str]:
        normalized_sections: List[str] = []
        for section in sections or []:
            normalized = self._normalize_candidate_section(section)
            if normalized and normalized not in normalized_sections:
                normalized_sections.append(normalized)
        return normalized_sections

    def _candidate_section_for_item(self, item: Dict[str, Any]) -> str:
        explicit_section = self._normalize_candidate_section(item.get("section"))
        if explicit_section and explicit_section != "one_item":
            return explicit_section
        return self.candidate_outfit_service.get_section(item)

    def _status_is_clean(self, item: Dict[str, Any]) -> bool:
        return (
            self.candidate_outfit_service._normalize_text(item.get("status") or "clean")
            == "clean"
        )

    def _strict_replace_reasoning(
        self,
        replace_sections: List[str],
        user_request_text: str,
    ) -> str:
        normalized_request = self.user_request_parser._normalize_text(user_request_text or "")
        is_portuguese = any(
            token in normalized_request
            for token in [
                "troca",
                "muda",
                "calca",
                "calcas",
                "casaco",
                "sapatilha",
                "sapatilhas",
                "camisola",
            ]
        )
        if is_portuguese:
            labels = self._join_names([
                {
                    "pants": "as calças",
                    "outer_layer": "o casaco",
                    "shoes": "as sapatilhas",
                    "insulation_layer": "a camisola",
                    "base_layer": "a peça de cima",
                    "accessories": "os acessórios",
                }.get(section, section)
                for section in replace_sections
            ])
            return f"Troquei apenas {labels} e mantive o resto do outfit igual."
        labels = self._join_section_labels(replace_sections)
        return f"I replaced only the {labels} and kept the rest of the outfit unchanged."

    def _build_strict_replace_response(
        self,
        wardrobe_items: List[Dict[str, Any]],
        current_outfit_item_ids: List[str],
        replace_sections: List[str],
        parsed_constraints: Dict[str, Any],
        weather: Dict[str, Any],
        exclude_items: Optional[List[str]],
        user_request_text: str,
    ) -> Dict[str, Any]:
        """Replace only requested current-outfit sections and preserve every other item."""
        wardrobe_by_id = {
            str(item.get("id")): item
            for item in wardrobe_items or []
            if item.get("id")
        }
        requested_current_ids = [
            str(item_id) for item_id in current_outfit_item_ids or []
        ]
        current_ids = [
            str(item_id)
            for item_id in requested_current_ids
            if str(item_id) in wardrobe_by_id
        ]
        if not current_ids:
            return self._create_error_response(
                "I need the current outfit to replace only one piece."
            )
        missing_current_ids = [
            item_id for item_id in requested_current_ids
            if item_id not in wardrobe_by_id
        ]
        if missing_current_ids:
            print(
                "[StrictReplace] missing_current_items "
                f"missing_current_ids={missing_current_ids}"
            )
            return self._create_error_response(
                "I could not load every item in the current outfit, so I cannot replace only one piece safely."
            )

        current_sections_by_id = {
            item_id: self._candidate_section_for_item(wardrobe_by_id[item_id])
            for item_id in current_ids
        }
        current_by_section: Dict[str, List[str]] = {}
        for item_id, section in current_sections_by_id.items():
            current_by_section.setdefault(section, []).append(item_id)

        normalized_replace_sections = self._normalize_candidate_sections(replace_sections)
        if "one_item" in normalized_replace_sections:
            normalized_replace_sections = [
                section
                for section in ["shoes", "outer_layer", "insulation_layer", "base_layer", "pants"]
                if section in current_by_section
            ][:1]
        if not normalized_replace_sections:
            requested_types = parsed_constraints.get("requested_types") or []
            normalized_replace_sections = [
                self._normalize_candidate_section(
                    self.user_request_parser.TYPE_TO_SECTION.get(item_type)
                )
                for item_type in requested_types
            ]
            normalized_replace_sections = [
                section for section in normalized_replace_sections
                if section and section != "one_item"
            ]
        if not normalized_replace_sections:
            return self._create_error_response(
                "I need to know which piece to replace."
            )

        excluded_ids = {str(item_id) for item_id in exclude_items or []}
        locked_item_ids = [
            item_id for item_id in current_ids
            if current_sections_by_id.get(item_id) not in normalized_replace_sections
        ]
        removed_item_ids = [
            item_id for item_id in current_ids
            if current_sections_by_id.get(item_id) in normalized_replace_sections
        ]
        selected_replacements_by_section: Dict[str, Dict[str, Any]] = {}
        replacement_item_ids: List[str] = []

        for section in normalized_replace_sections:
            section_current_ids = set(current_by_section.get(section, []))
            section_candidates = [
                item for item in wardrobe_items or []
                if str(item.get("id")) not in section_current_ids
                and str(item.get("id")) not in excluded_ids
                and str(item.get("id")) not in set(locked_item_ids)
                and self._status_is_clean(item)
                and self._candidate_section_for_item(item) == section
            ]
            weather_compatible, checked_temperature = (
                self.candidate_outfit_service.filter_temperature_compatible(
                    section_candidates,
                    weather,
                )
            )
            if checked_temperature and weather_compatible:
                section_candidates = weather_compatible

            print(
                "[StrictReplace] section_candidates "
                f"section={section} "
                f"candidate_ids={[item.get('id') for item in section_candidates]} "
                f"excluded_current_ids={list(section_current_ids)} "
                f"excluded_ids={list(excluded_ids)}"
            )
            if not section_candidates:
                debug_payload = {
                    "mode": "strict_replace_piece",
                    "replace_sections": normalized_replace_sections,
                    "locked_item_ids": locked_item_ids,
                    "removed_item_ids": removed_item_ids,
                    "replacement_item_ids": replacement_item_ids,
                    "final_item_ids": current_ids,
                }
                print(f"[StrictReplace] {json.dumps(debug_payload, ensure_ascii=False)}")
                return self._create_error_response(
                    self._replacement_failure_message(section)
                )

            sorted_candidates = self.candidate_outfit_service._sort_items(
                section_candidates,
                parsed_constraints,
            )
            selected = sorted_candidates[0]
            selected_id = str(selected.get("id"))
            selected_replacements_by_section[section] = selected
            replacement_item_ids.append(selected_id)

        final_items: List[Dict[str, Any]] = []
        inserted_sections = set()
        for item_id in current_ids:
            section = current_sections_by_id.get(item_id)
            if section in normalized_replace_sections:
                replacement = selected_replacements_by_section.get(section)
                if replacement and section not in inserted_sections:
                    final_items.append({**replacement, "section": section})
                    inserted_sections.add(section)
                continue
            final_items.append({**wardrobe_by_id[item_id], "section": section})

        for section, replacement in selected_replacements_by_section.items():
            if section not in inserted_sections:
                final_items.append({**replacement, "section": section})
                inserted_sections.add(section)

        final_item_ids = [str(item.get("id")) for item in final_items if item.get("id")]
        for item_id in locked_item_ids:
            if item_id not in final_item_ids:
                section = current_sections_by_id[item_id]
                final_items.append({**wardrobe_by_id[item_id], "section": section})
                final_item_ids.append(item_id)

        final_item_ids = [str(item.get("id")) for item in final_items if item.get("id")]
        debug_payload = {
            "mode": "strict_replace_piece",
            "replace_sections": normalized_replace_sections,
            "locked_item_ids": locked_item_ids,
            "removed_item_ids": removed_item_ids,
            "replacement_item_ids": replacement_item_ids,
            "final_item_ids": final_item_ids,
        }
        print(f"[StrictReplace] {json.dumps(debug_payload, ensure_ascii=False)}")

        reasoning = self._strict_replace_reasoning(
            normalized_replace_sections,
            user_request_text,
        )
        return {
            "success": True,
            "outfit": {
                "items": final_items,
                "reasoning": reasoning,
            },
            "model_used": "strict_replace_piece",
            "context_used": "strict_replace_piece",
            "validation": {
                "warnings": [],
                "errors": [],
            },
            "debug": debug_payload,
            "timestamp": datetime.now().isoformat(),
        }

    def _build_followup_plan(
        self,
        parsed_constraints: Dict[str, Any],
        current_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Translate a follow-up intent into exact current outfit keep/replace IDs."""
        if not current_items:
            return None

        mode = parsed_constraints.get("mode")
        replace_sections = list(parsed_constraints.get("replace_sections") or [])
        keep_sections = list(parsed_constraints.get("keep_sections") or [])
        avoid = parsed_constraints.get("avoid") or {}

        if (
            mode not in {"replace_piece", "keep_piece", "avoid_piece"}
            and not replace_sections
            and not keep_sections
            and not avoid
        ):
            return None

        current_by_section: Dict[str, List[Dict[str, Any]]] = {}
        for item in current_items:
            section = self._item_section(item)
            current_by_section.setdefault(section, []).append(item)

        normalized_replace = set()
        if "one_item" in replace_sections:
            candidates = [
                section for section in ("shoes", "outer", "insulation", "base", "pants", "accessories")
                if section in current_by_section and section not in set(keep_sections)
            ]
            if candidates:
                normalized_replace.add(candidates[0])
        normalized_replace.update(section for section in replace_sections if section != "one_item")

        if keep_sections and self._requests_change_rest(parsed_constraints.get("raw_text", "")):
            normalized_replace.update(
                section for section in current_by_section
                if section not in set(keep_sections)
            )

        if avoid:
            for section, items in current_by_section.items():
                if any(self._item_matches_avoid(item, avoid) for item in items):
                    normalized_replace.add(section)

        if not normalized_replace and keep_sections:
            normalized_replace.update(
                section for section in current_by_section
                if section not in set(keep_sections)
            )

        if not normalized_replace:
            return None

        keep_ids = [
            item.get("id")
            for section, items in current_by_section.items()
            for item in items
            if section not in normalized_replace and item.get("id")
        ]
        replace_ids = [
            item.get("id")
            for section, items in current_by_section.items()
            for item in items
            if section in normalized_replace and item.get("id")
        ]

        return {
            "current_items": current_items,
            "keep_ids": keep_ids,
            "replace_ids": replace_ids,
            "replace_sections": sorted(normalized_replace),
        }

    def _build_followup_response(
        self,
        ai_context,
        current_items: List[Dict[str, Any]],
        keep_ids: List[str],
        replace_sections: List[str],
        parsed_constraints: Dict[str, Any],
        weather: Dict[str, Any],
        preferences: Dict[str, Any],
        must_include_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Build a deterministic follow-up outfit that only changes requested sections."""
        all_candidates = ai_context.get_all_items()
        candidates_by_id = {item.id: item for item in all_candidates}
        selected = [
            candidates_by_id[item_id]
            for item_id in keep_ids
            if item_id in candidates_by_id
        ]
        selected_ids = {item.id for item in selected}
        current_ids = {item.get("id") for item in current_items if item.get("id")}

        for mandatory in must_include_items or []:
            mandatory_id = mandatory.get("id")
            if mandatory_id and mandatory_id in candidates_by_id and mandatory_id not in selected_ids:
                selected.append(candidates_by_id[mandatory_id])
                selected_ids.add(mandatory_id)

        replacement_items = []
        old_item_ids = []
        for section in replace_sections:
            old_item_ids.extend(
                item.get("id")
                for item in current_items
                if item.get("id") and self._item_section(item) == section
            )
            replacement = self._choose_replacement_for_section(
                section=section,
                candidates=all_candidates,
                selected_ids=selected_ids,
                current_ids=current_ids,
                parsed_constraints=parsed_constraints,
            )
            if not replacement:
                return self._create_error_response(
                    self._replacement_failure_message(section)
                )
            selected.append(replacement)
            selected_ids.add(replacement.id)
            replacement_items.append(replacement)

        reasoning = self._followup_reasoning(
            replace_sections=replace_sections,
            keep_ids=keep_ids,
            parsed_constraints=parsed_constraints,
            must_include_items=must_include_items or [],
            replacement_items=replacement_items,
        )
        reasoning = self._ensure_reasoning_matches_items(
            reasoning or self.build_clean_reasoning(
                validated_items=selected,
                weather=weather,
                preferences=preferences,
                must_include_items=must_include_items,
            ),
            validated_items=selected,
            weather=weather,
            preferences=preferences,
            must_include_items=must_include_items,
            user_request_text=parsed_constraints.get("raw_text"),
        )
        self._log_final_outfit_debug(
            final_items=selected,
            reasoning=reasoning,
            must_include_items=must_include_items,
            replaced_sections=replace_sections,
            old_item_ids=old_item_ids,
            replacement_item_ids=[item.id for item in replacement_items],
        )

        return {
            "success": True,
            "outfit": {
                "items": [item.to_dict() for item in selected],
                "reasoning": reasoning,
            },
            "model_used": "rule_based",
            "context_used": "followup_intent",
            "timestamp": datetime.now().isoformat(),
        }

    def _choose_replacement_for_section(
        self,
        section: str,
        candidates: List[Any],
        selected_ids: set,
        current_ids: set,
        parsed_constraints: Dict[str, Any],
    ) -> Optional[Any]:
        section_candidates = [
            item for item in candidates
            if item.id not in selected_ids
            and item.id not in current_ids
            and self._item_section(item) == section
        ]
        for item in candidates:
            reasons = []
            if item.id in selected_ids:
                reasons.append("already_selected")
            if item.id in current_ids:
                reasons.append("current_item_excluded")
            if self._item_section(item) != section:
                reasons.append("section_mismatch")
            print(
                "[CommandResolver] replacement_candidate "
                f"section={section} id={item.id} name={item.name} type={item.type} "
                f"color={item.color} status={item.status} "
                f"decision={'candidate' if not reasons else 'rejected'} "
                f"reason={'candidate' if not reasons else ','.join(reasons)}"
            )

        requested_types = parsed_constraints.get("requested_types") or []
        requested_colors = parsed_constraints.get("requested_colors") or []
        relevant_types = [
            item_type for item_type in requested_types
            if self._section_for_type(item_type) == section
        ]
        relevant_colors = requested_colors if relevant_types or not requested_types else []

        if relevant_types:
            section_candidates = [
                item for item in section_candidates
                if any(self.constraint_matching_service._type_matches(item.type, t) for t in relevant_types)
            ]
        if relevant_colors:
            section_candidates = [
                item for item in section_candidates
                if any(self.constraint_matching_service._item_color_matches(item.to_dict(), c) for c in relevant_colors)
            ]

        if not section_candidates:
            print(
                "[CommandResolver] replacement_result "
                f"section={section} decision=failed reason=no_alternative_clean_section_candidate"
            )
            return None

        selected = sorted(
            section_candidates,
            key=lambda item: (
                item.score if item.score is not None else 0,
                -(item.usage_metrics or {}).get("usage_frequency_last_7_days", 0),
                bool(item.favorite),
            ),
            reverse=True,
        )[0]
        print(
            "[CommandResolver] replacement_result "
            f"section={section} decision=matched id={selected.id} name={selected.name}"
        )
        return selected

    def _enforce_final_outfit_constraints(
        self,
        selected_items: List[Any],
        ai_context,
        must_include_items: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Any]:
        """Make the returned item list obey mandatory section ownership."""
        final_items = []
        seen_ids = set()
        for item in selected_items or []:
            item_id = getattr(item, "id", None)
            if item_id and item_id not in seen_ids:
                final_items.append(item)
                seen_ids.add(item_id)

        items_by_id = {item.id: item for item in ai_context.get_all_items()}
        for mandatory in must_include_items or []:
            mandatory_id = mandatory.get("id")
            mandatory_item = items_by_id.get(mandatory_id)
            if not mandatory_item:
                continue

            mandatory_section = self._item_section(mandatory_item)
            before_ids = [getattr(item, "id", None) for item in final_items]
            final_items = [
                item for item in final_items
                if (
                    getattr(item, "id", None) == mandatory_id
                    or self._item_section(item) != mandatory_section
                )
            ]
            if mandatory_id not in {getattr(item, "id", None) for item in final_items}:
                final_items.append(mandatory_item)
            after_ids = [getattr(item, "id", None) for item in final_items]
            if before_ids != after_ids:
                print(
                    "[FinalConsistency] enforced_must_include_section "
                    f"section={mandatory_section} mandatory_id={mandatory_id} "
                    f"before={before_ids} after={after_ids}"
                )

        return final_items

    def _enforce_parsed_mandatory_slots(
        self,
        parsed_result: Dict[str, Any],
        ai_context,
        must_include_items: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Make parsed JSON IDs obey mandatory slot ownership before validation."""
        if not must_include_items:
            return

        items_by_id = {item.id: item for item in ai_context.get_all_items()}
        layer_assignments = parsed_result.setdefault(
            "layer_assignments",
            {1: [], 2: [], 3: [], "shoes": [], "accessories": []},
        )
        parsed_ids = list(parsed_result.get("item_ids", []))
        before_ids = list(parsed_ids)

        for mandatory in must_include_items:
            mandatory_id = mandatory.get("id")
            mandatory_item = items_by_id.get(mandatory_id)
            if not mandatory_id or not mandatory_item:
                continue

            mandatory_section = self._json_section_for_item(mandatory_item)
            existing_section_ids = set(layer_assignments.get(mandatory_section, []))
            parsed_ids = [
                item_id for item_id in parsed_ids
                if item_id == mandatory_id or item_id not in existing_section_ids
            ]
            for section, ids in list(layer_assignments.items()):
                if section != mandatory_section:
                    layer_assignments[section] = [
                        item_id for item_id in ids if item_id != mandatory_id
                    ]
            layer_assignments[mandatory_section] = [mandatory_id]
            if mandatory_id not in parsed_ids:
                parsed_ids.append(mandatory_id)

        parsed_result["item_ids"] = list(dict.fromkeys(parsed_ids))
        print(
            "[RecommendationService] enforced_mandatory_json_slots "
            f"before={before_ids} after={parsed_result['item_ids']} "
            f"layer_assignments={layer_assignments}"
        )

    def _ensure_reasoning_matches_items(
        self,
        reasoning: str,
        validated_items: List[Any],
        weather: Dict[str, Any],
        preferences: Optional[Dict[str, Any]] = None,
        must_include_items: Optional[List[Dict[str, Any]]] = None,
        user_request_text: Optional[str] = None,
    ) -> str:
        final_names = {
            getattr(item, "name", None)
            for item in validated_items or []
            if getattr(item, "name", None)
        }
        final_ids = {
            getattr(item, "id", None)
            for item in validated_items or []
            if getattr(item, "id", None)
        }
        missing_mandatory = [
            item.get("name") or item.get("id")
            for item in must_include_items or []
            if item.get("id") and item.get("id") not in final_ids
        ]
        mentioned_missing = [
            name for name in final_names
            if name and name in (reasoning or "") and name not in final_names
        ]
        if missing_mandatory or mentioned_missing:
            print(
                "[FinalConsistency] rebuilding_reasoning "
                f"missing_mandatory={missing_mandatory} mentioned_missing={mentioned_missing}"
            )
            return self.build_clean_reasoning(
                validated_items=validated_items,
                weather=weather,
                preferences=preferences,
                must_include_items=must_include_items,
                user_request_text=user_request_text,
            )

        # The backend never trusts raw LLaVA text here; this keeps reasoning tied
        # to the exact final item list even when the supplied sentence is generic.
        return reasoning or self.build_clean_reasoning(
            validated_items=validated_items,
            weather=weather,
            preferences=preferences,
            must_include_items=must_include_items,
            user_request_text=user_request_text,
        )

    def _log_final_outfit_debug(
        self,
        final_items: List[Any],
        reasoning: str,
        must_include_items: Optional[List[Dict[str, Any]]] = None,
        replaced_sections: Optional[List[str]] = None,
        old_item_ids: Optional[List[str]] = None,
        replacement_item_ids: Optional[List[str]] = None,
    ) -> None:
        final_item_ids = [getattr(item, "id", None) for item in final_items]
        final_item_names = [getattr(item, "name", None) for item in final_items]
        print(
            "[FinalConsistency] "
            f"final_item_ids={final_item_ids} "
            f"final_item_names={final_item_names} "
            f"must_include_item_ids={[item.get('id') for item in must_include_items or []]} "
            f"replaced_section={replaced_sections or []} "
            f"old_item_ids={old_item_ids or []} "
            f"replacement_item_ids={replacement_item_ids or []} "
            f"final_reasoning={reasoning}"
        )

    def _item_matches_avoid(self, item: Dict[str, Any], avoid: Dict[str, Any]) -> bool:
        if avoid.get("name"):
            requested = str(avoid["name"]).lower()
            name = str(item.get("name", "")).lower()
            if requested in name or name in requested:
                return True
        if avoid.get("type") and self.constraint_matching_service._type_matches(
            item.get("type", ""), avoid["type"]
        ):
            return True
        if avoid.get("color") and self.constraint_matching_service._item_color_matches(
            item, avoid["color"]
        ):
            return True
        return False

    def _requests_change_rest(self, raw_text: str) -> bool:
        text = self.user_request_parser._normalize_text(raw_text or "")
        return re.search(r"\b(?:muda|troca|change|replace)\s+(?:o\s+)?(?:resto|rest)\b", text) is not None

    def _item_section(self, item: Any) -> str:
        if isinstance(item, dict):
            item_type = item.get("type", "")
            item_name = item.get("name", "")
            layer = item.get("layer")
        else:
            item_type = getattr(item, "type", "")
            item_name = getattr(item, "name", "")
            layer = getattr(item, "layer", None)

        text = f"{item_type} {item_name}".lower()
        if any(token in text for token in ["vestido", "dress"]):
            return "dress"
        if any(token in text for token in ["saia", "skirt"]):
            return "skirt"
        if any(token in text for token in ["macacao", "macacão", "jumpsuit"]):
            return "jumpsuit"
        if any(token in text for token in ["mala", "carteira", "bag", "handbag", "purse"]):
            return "bag"
        if any(token in text for token in ["sapatilha", "tenis", "ténis", "sneaker", "shoe", "boot", "calçado", "calcado", "sandalia", "sandália", "sandal"]):
            return "shoes"
        if any(token in text for token in ["calça", "calca", "pants", "trouser", "jeans", "short", "calções", "calcoes"]):
            return "pants"
        if any(token in text for token in ["casaco", "jacket", "coat", "blazer", "sobretudo"]):
            return "outer"
        if any(token in text for token in ["camisola", "sweater", "hoodie", "sweatshirt", "cardigan"]):
            return "insulation"
        if any(token in text for token in ["acessor", "accessor", "scarf", "belt", "tie", "hat", "cap"]):
            return "accessories"
        if layer == 2:
            return "insulation"
        if layer == 3:
            return "outer"
        return "base"

    def _dict_search_text(self, item: Dict[str, Any]) -> str:
        return self.constraint_matching_service._normalize_text(
            " ".join(
                str(value or "")
                for value in [
                    item.get("name"),
                    item.get("type"),
                    item.get("style"),
                    item.get("occasion"),
                    " ".join(str(material) for material in item.get("materials") or []),
                ]
            )
        )

    def _looks_formal_dict(self, item: Dict[str, Any]) -> bool:
        text = self._dict_search_text(item)
        positive = [
            "formal",
            "camisa",
            "shirt",
            "blazer",
            "casaco",
            "jacket",
            "coat",
            "trouser",
            "trousers",
            "calcas",
            "chino",
            "sapatos",
            "boots",
            "botas",
            "oxford",
            "loafer",
            "work",
            "office",
            "business",
            "elegant",
        ]
        return any(keyword in text for keyword in positive)

    def _looks_sporty_or_casual_dict(self, item: Dict[str, Any]) -> bool:
        text = self._dict_search_text(item)
        negative = [
            "jersey",
            "t-shirt",
            "tshirt",
            "tee",
            "sneaker",
            "sneakers",
            "sapatilhas",
            "tenis",
            "hoodie",
            "sportswear",
            "sport",
            "sporty",
            "desportivo",
            "athletic",
            "gym",
            "air jordan",
        ]
        return any(keyword in text for keyword in negative)

    def _section_for_type(self, item_type: str) -> str:
        return self.user_request_parser.TYPE_TO_SECTION.get(item_type, "base")

    def _section_label(self, section: str) -> str:
        return {
            "shoes": "shoes",
            "outer": "jacket",
            "outer_layer": "jacket",
            "insulation": "sweater",
            "insulation_layer": "sweater",
            "base": "top",
            "base_layer": "top",
            "dress": "dress",
            "skirt": "skirt",
            "jumpsuit": "jumpsuit",
            "pants": "pants",
            "bag": "bag",
            "accessories": "accessories",
        }.get(section, section)

    def _replacement_failure_message(self, section: str) -> str:
        if section == "pants":
            return "I could not find another clean pair of pants to replace the current one."
        if section == "shoes":
            return "I could not replace the shoes because no alternative clean shoes are available."
        if section == "outer_layer":
            return "I could not replace the jacket because no alternative clean jacket is available."
        if section in {"base_layer", "insulation_layer"}:
            return "I could not replace that top because no alternative clean top is available."
        label = self._section_label(section)
        return f"I could not replace the {label} because no alternative clean {label} item is available."

    def _followup_reasoning(
        self,
        replace_sections: List[str],
        keep_ids: List[str],
        parsed_constraints: Dict[str, Any],
        must_include_items: List[Dict[str, Any]],
        replacement_items: Optional[List[Any]] = None,
    ) -> str:
        replacement_names = [
            getattr(item, "name", None)
            for item in replacement_items or []
            if getattr(item, "name", None)
        ]
        if parsed_constraints.get("keep_sections") and self._requests_change_rest(
            parsed_constraints.get("raw_text", "")
        ):
            kept = self._join_section_labels(parsed_constraints.get("keep_sections", []))
            changed = (
                f" using {self._join_names(replacement_names)}"
                if replacement_names
                else ""
            )
            return f"I kept the {kept} and changed the other pieces{changed}."

        if len(replace_sections) == 1:
            replacement_phrase = (
                f" with {self._join_names(replacement_names)}"
                if replacement_names
                else ""
            )
            return f"I replaced only the {self._section_label(replace_sections[0])}{replacement_phrase} and kept the rest of the outfit."

        if must_include_items:
            names = [item.get("name") for item in must_include_items if item.get("name")]
            if names:
                return f"This outfit includes your {self._join_names(names)} as requested."

        changed = self._join_section_labels(replace_sections)
        return f"I changed the {changed} and kept the rest of the outfit."

    def _join_section_labels(self, sections: List[str]) -> str:
        return self._join_names([self._section_label(section) for section in sections])

    def _join_names(self, names: List[str]) -> str:
        """Join item names for short natural user-facing sentences."""
        clean_names = [name for name in names if name]
        if not clean_names:
            return "your selected pieces"
        if len(clean_names) == 1:
            return clean_names[0]
        if len(clean_names) == 2:
            return f"{clean_names[0]} and {clean_names[1]}"
        return f"{', '.join(clean_names[:-1])}, and {clean_names[-1]}"

    async def _retry_with_stricter_prompt(
        self,
        ai_context,
        temperature: float,
        weather_condition: str,
        occasion: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        humidity: Optional[float] = None,
        wind_speed: Optional[float] = None,
        must_include_items: Optional[List[Dict[str, Any]]] = None,
        user_request_text: Optional[str] = None,
    ):
        """
        Retry VLM call with stricter constraints based on validation errors.

        Args:
            ai_context: AIReadyContext with enriched wardrobe data
            temperature: Current temperature
            weather_condition: Current weather condition
            occasion: Optional occasion
            validation_errors: List of validation errors from previous attempt
            humidity: Optional humidity percentage
            wind_speed: Optional wind speed in km/h
            must_include_items: Items that must be included in the retry
            user_request_text: Original user request to restate in the retry prompt

        Returns:
            VLMResponse from retry attempt
        """
        logger.info("Retrying VLM call with stricter constraints")

        if validation_errors:
            logger.debug(f"Previous validation errors: {validation_errors}")

        # Apply stricter filters:
        # 1. Remove items that failed validation
        mandatory_item_ids = {
            item.get("id") for item in (must_include_items or []) if item.get("id")
        }

        filtered_items = [
            item
            for item in ai_context.get_all_items()
            if (
                item.status != "dirty"
                and item.status != "damaged"
                and item.is_suitable_for_weather(weather_condition)
                and (
                    item.id in mandatory_item_ids
                    or item.is_suitable_for_temperature(temperature - 2, temperature + 2)
                )
            )
        ]

        if not filtered_items:
            logger.warning("No items passed stricter filtering")
            return None

        logger.info(f"Retry with {len(filtered_items)} filtered items")

        retry_prompt = self.prompt_service.build_daily_prompt_from_context(
            ai_context,
            must_include_items=must_include_items,
            user_request_text=user_request_text,
        )
        if validation_errors:
            retry_prompt += (
                "\n\nRETRY VALIDATION FEEDBACK:\n"
                + "\n".join(f"- {error}" for error in validation_errors)
                + "\nFollow the required format exactly and correct the invalid assignments."
            )

        # Retry VLM with stricter context
        vlm_response = await self.vlm_service.recommend_outfit(
            wardrobe_items=[item.to_dict() for item in filtered_items],
            weather_context=ai_context.weather_current.to_dict()
            if ai_context.weather_current
            else {},
            user_context={
                "preferences": ai_context.user_constraints.get("preferences", {}),
                "occasion": occasion,
                "strict_validation": True,
                "previous_errors": validation_errors or [],
            },
            prompt_template=retry_prompt,
        )

        return vlm_response

    async def _validate_travel_vlm_response(
        self, vlm_responses: List, ai_context, wardrobe_items_by_id: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate travel outfit VLM responses.

        Args:
            vlm_responses: List of VLMResponse objects (one per day)
            ai_context: AIReadyContext with enriched wardrobe data
            wardrobe_items_by_id: Mapping of item IDs to item data

        Returns:
            Validation result dictionary with structure similar to daily validation
        """
        errors = []
        warnings = []
        valid_responses = []

        logger.info(f"Validating {len(vlm_responses)} daily travel outfits")

        for day_idx, vlm_resp in enumerate(vlm_responses):
            day_errors = []

            if not vlm_resp.success:
                day_errors.append(f"Day {day_idx + 1}: VLM call failed")
                logger.warning(f"Day {day_idx + 1} VLM call was not successful")
                continue

            valid_items = []
            seen_ids = set()

            for item_id in vlm_resp.outfit_items:
                if item_id not in wardrobe_items_by_id:
                    day_errors.append(
                        f"Day {day_idx + 1}: Item {item_id} not in wardrobe"
                    )
                    continue

                item = wardrobe_items_by_id[item_id]

                if item.status in ["dirty", "damaged"]:
                    day_errors.append(
                        f"Day {day_idx + 1}: Item '{item.name}' is {item.status}"
                    )
                    continue

                if item_id in seen_ids:
                    warnings.append(f"Day {day_idx + 1}: Duplicate item '{item.name}'")
                    continue

                seen_ids.add(item_id)
                valid_items.append(item)

            if len(valid_items) < 2:
                day_errors.append(
                    f"Day {day_idx + 1}: Too few valid items ({len(valid_items)})"
                )

            if day_errors:
                errors.extend(day_errors)
            else:
                valid_responses.append(
                    {"day": day_idx + 1, "items": valid_items, "response": vlm_resp}
                )

        is_valid = len(errors) == 0

        logger.info(
            f"Travel validation result: valid={is_valid}, "
            f"valid_days={len(valid_responses)}, errors={len(errors)}"
        )

        return {
            "valid": is_valid,
            "valid_responses": valid_responses,
            "errors": errors,
            "warnings": warnings,
        }

    async def _validate_alternatives_vlm_responses(
        self, vlm_responses: List, ai_context, wardrobe_items_by_id: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate alternative outfit VLM responses.

        Args:
            vlm_responses: List of VLMResponse objects (one per alternative)
            ai_context: AIReadyContext with enriched wardrobe data
            wardrobe_items_by_id: Mapping of item IDs to item data

        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []
        valid_alternatives = []

        logger.info(f"Validating {len(vlm_responses)} alternative outfits")

        for alt_idx, vlm_resp in enumerate(vlm_responses):
            alt_errors = []

            if not vlm_resp.success:
                alt_errors.append(f"Alternative {alt_idx + 1}: VLM call failed")
                continue

            valid_items = []
            seen_ids = set()

            for item_id in vlm_resp.outfit_items:
                if item_id not in wardrobe_items_by_id:
                    alt_errors.append(
                        f"Alternative {alt_idx + 1}: Item {item_id} not in wardrobe"
                    )
                    continue

                item = wardrobe_items_by_id[item_id]

                if item.status in ["dirty", "damaged"]:
                    alt_errors.append(
                        f"Alternative {alt_idx + 1}: Item '{item.name}' is {item.status}"
                    )
                    continue

                if item_id in seen_ids:
                    warnings.append(
                        f"Alternative {alt_idx + 1}: Duplicate item '{item.name}'"
                    )
                    continue

                seen_ids.add(item_id)
                valid_items.append(item)

            if len(valid_items) < 2:
                alt_errors.append(
                    f"Alternative {alt_idx + 1}: Too few valid items ({len(valid_items)})"
                )

            if alt_errors:
                errors.extend(alt_errors)
            else:
                valid_alternatives.append(
                    {
                        "alternative_num": alt_idx + 1,
                        "items": valid_items,
                        "response": vlm_resp,
                    }
                )

        is_valid = len(errors) == 0

        logger.info(
            f"Alternatives validation result: valid={is_valid}, "
            f"valid_alts={len(valid_alternatives)}, errors={len(errors)}"
        )

        return {
            "valid": is_valid,
            "valid_alternatives": valid_alternatives,
            "errors": errors,
            "warnings": warnings,
        }

    # ========================================================================
    # FALLBACK METHODS (Rule-based recommendations when VLM not available)
    # ========================================================================

    async def _fallback_daily_recommendation_from_context(self, ai_context):
        """
        Fallback recommendation using AI-ready context.

        Selects from the highest-scored candidates while preserving mandatory items.
        """
        try:
            outfit_items = []
            selected_ids = set()
            mandatory_ids = set(
                ai_context.user_constraints.get("must_include_ids", [])
                if ai_context.user_constraints
                else []
            )
            all_items = ai_context.get_all_items()

            for item in all_items:
                if item.id in mandatory_ids and item.id not in selected_ids:
                    outfit_items.append(item)
                    selected_ids.add(item.id)

            # Select one item from each available layer
            for layer in sorted(ai_context.wardrobe_by_layer.keys()):
                items = [
                    item for item in ai_context.wardrobe_by_layer[layer]
                    if item.id not in selected_ids
                ]
                if not items:
                    continue

                sorted_items = sorted(
                    items,
                    key=lambda x: (
                        x.score if x.score is not None else 0,
                        -x.usage_metrics.get("usage_frequency_last_7_days", 0),
                        bool(x.favorite),
                    ),
                    reverse=True,
                )
                best_score = sorted_items[0].score or 0
                top_pool = [
                    item for item in sorted_items[:5]
                    if (item.score or 0) >= best_score - 10
                ]
                selected = random.choice(top_pool or sorted_items[:1])
                outfit_items.append(selected)
                selected_ids.add(selected.id)

            must_include_items = [
                {"id": item.id, "name": item.name}
                for item in outfit_items
                if item.id in mandatory_ids
            ]
            outfit_items = self._enforce_final_outfit_constraints(
                selected_items=outfit_items,
                ai_context=ai_context,
                must_include_items=must_include_items,
            )
            preferences = (
                ai_context.user_constraints.get("preferences", {})
                if ai_context.user_constraints
                else {}
            )
            requested_style = preferences.get("style")
            if requested_style and not self._items_match_requested_style(
                outfit_items,
                requested_style,
            ):
                return self._create_error_response(
                    "I could not find matching items in your wardrobe"
                )
            reasoning = self.build_clean_reasoning(
                validated_items=outfit_items,
                weather=ai_context.weather_current.to_dict()
                if ai_context.weather_current
                else {},
                preferences=preferences,
                must_include_items=must_include_items,
            )
            self._log_final_outfit_debug(
                final_items=outfit_items,
                reasoning=reasoning,
                must_include_items=must_include_items,
            )

            return {
                "success": True,
                "outfit": {
                    "items": [item.to_dict() for item in outfit_items],
                    "reasoning": reasoning,
                },
                "model_used": "rule_based",
                "context_used": "ai_ready_context",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return self._create_error_response(f"Fallback recommendation failed: {e}")

    async def _fallback_travel_recommendation_from_context(self, ai_context):
        """
        Fallback travel recommendation using AI-ready context.

        Returns all available items as packing list.
        """
        try:
            all_items = ai_context.get_all_items()

            return {
                "success": True,
                "travel_plan": {
                    "packing_list": [item.to_dict() for item in all_items],
                    "packing_notes": "Rule-based packing: all suitable items selected",
                },
                "model_used": "rule_based",
                "context_used": "ai_ready_context",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return self._create_error_response(f"Travel fallback failed: {e}")

    async def _fallback_alternative_recommendation_from_context(
        self, ai_context, num_alternatives
    ):
        """
        Fallback alternative recommendations using AI-ready context.

        Selects diverse items from different layers.
        """
        try:
            alternatives = []
            all_items = ai_context.get_all_items()

            # Create simple alternatives by grouping items differently
            for i in range(min(num_alternatives, len(all_items))):
                outfit = [all_items[j] for j in range(i, min(i + 3, len(all_items)))]
                if outfit:
                    alternatives.append(
                        {
                            "items": [item.to_dict() for item in outfit],
                            "reasoning": f"Alternative {i + 1}: different item combination",
                        }
                    )

            return {
                "success": True,
                "alternatives": alternatives,
                "model_used": "rule_based",
                "context_used": "ai_ready_context",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return self._create_error_response(f"Alternative fallback failed: {e}")

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Create a standardized error response.

        Args:
            error_message: Error description

        Returns:
            Dictionary with error info
        """
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
        }


class RecommendationServiceError(Exception):
    """Exception raised by RecommendationService."""

    pass
