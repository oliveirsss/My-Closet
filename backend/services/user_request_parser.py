"""
User Request Parser Service

Parses user text requests to extract structured constraints for outfit recommendations.

Examples:
"outfit com sapatilhas amarelas" → 
  must_include: {"type": "sneakers", "color": "yellow"}

"outfit mais formal" → 
  style: "formal"

"quero usar a Work Jacket" → 
  must_include: {"name": "Work Jacket"}

"traje para apresentação" →
  occasion: "presentation"
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional


class UserRequestParser:
    """
    Parses user text to extract clothing constraints and preferences.
    """

    # Color mappings (English and Portuguese - singular and plural)
    COLOR_MAPPINGS = {
        # Portuguese - Masculine singular & plural
        "amarelo": "yellow",
        "amarelos": "yellow",
        # Portuguese - Feminine singular & plural
        "amarela": "yellow",
        "amarelas": "yellow",
        
        "azul": "blue",
        "azuis": "blue",
        
        "vermelho": "red",
        "vermelhos": "red",
        "vermelha": "red",
        "vermelhas": "red",
        
        "verde": "green",
        "verdes": "green",
        
        "preto": "black",
        "pretos": "black",
        "preta": "black",
        "pretas": "black",
        
        "branco": "white",
        "brancos": "white",
        "branca": "white",
        "brancas": "white",
        
        "cinza": "gray",
        "cinzas": "gray",
        "cinzento": "gray",
        "cinzentos": "gray",
        "cinzenta": "gray",
        "cinzentas": "gray",
        
        "rosa": "pink",
        "rosas": "pink",
        
        "roxo": "purple",
        "roxos": "purple",
        "roxa": "purple",
        "roxas": "purple",
        
        "laranja": "orange",
        "laranjas": "orange",
        
        "marrom": "brown",
        "marrons": "brown",
        "castanho": "brown",
        "castanhos": "brown",
        "castanha": "brown",
        "castanhas": "brown",
        
        "bege": "beige",
        "beges": "beige",
        
        "creme": "cream",
        "cremes": "cream",
        
        "ouro": "gold",
        "ouros": "gold",
        
        "prata": "silver",
        "pratas": "silver",
        
        # English
        "yellow": "yellow",
        "blue": "blue",
        "red": "red",
        "green": "green",
        "black": "black",
        "white": "white",
        "gray": "gray",
        "grey": "gray",
        "pink": "pink",
        "purple": "purple",
        "orange": "orange",
        "brown": "brown",
        "beige": "beige",
        "cream": "cream",
        "gold": "gold",
        "silver": "silver",
    }

    # Type/Category mappings
    TYPE_MAPPINGS = {
        # Portuguese
        "sapatilha": "sneakers",
        "sapatilhas": "sneakers",
        "tenis": "sneakers",
        "ténis": "sneakers",
        "sapato": "shoes",
        "botas": "boots",
        "bota": "boots",
        "chinelos": "sandals",
        "calçado": "shoes",
        "calcado": "shoes",
        "jaqueta": "jacket",
        "casaco": "jacket",
        "casacos": "jacket",
        "camisola": "sweater",
        "camisolas": "sweater",
        "camiseta": "t-shirt",
        "camisa": "shirt",
        "blusa": "blouse",
        "top": "top",
        "calça": "pants",
        "calca": "pants",
        "calças": "pants",
        "calcas": "pants",
        "saia": "skirt",
        "saias": "skirt",
        "vestido": "dress",
        "vestidos": "dress",
        "macacão": "jumpsuit",
        "macacao": "jumpsuit",
        "macacões": "jumpsuit",
        "macacoes": "jumpsuit",
        "mala": "bag",
        "malas": "bag",
        "carteira": "bag",
        "carteiras": "bag",
        "calções": "shorts",
        "calcoes": "shorts",
        "shorts": "shorts",
        "suéter": "sweater",
        "sueter": "sweater",
        "moletom": "hoodie",
        "cardigã": "cardigan",
        "cardiga": "cardigan",
        "cardigan": "cardigan",
        "acessório": "accessory",
        "acessorio": "accessory",
        "acessórios": "accessories",
        "acessorios": "accessories",
        "gravata": "tie",
        "lenço": "scarf",
        "lenco": "scarf",
        "meia": "socks",
        "meias": "socks",
        "cinto": "belt",
        # English
        "sneakers": "sneakers",
        "shoes": "shoes",
        "boots": "boots",
        "sandals": "sandals",
        "jacket": "jacket",
        "coat": "jacket",
        "t-shirt": "tshirt",
        "tshirt": "tshirt",
        "jersey": "tshirt",
        "shirt": "shirt",
        "top": "top",
        "blouse": "blouse",
        "pants": "pants",
        "trousers": "pants",
        "skirt": "skirt",
        "dress": "dress",
        "jumpsuit": "jumpsuit",
        "bag": "bag",
        "bags": "bag",
        "handbag": "bag",
        "purse": "bag",
        "shorts": "shorts",
        "sweater": "sweater",
        "hoodie": "hoodie",
        "sweatshirt": "hoodie",
        "cardigan": "cardigan",
        "accessory": "accessories",
        "accessories": "accessories",
        "tie": "tie",
        "scarf": "scarf",
        "socks": "socks",
        "belt": "belt",
    }

    # Style/Occasion mappings
    STYLE_MAPPINGS = {
        # Portuguese
        "formal": "formal",
        "casual": "casual",
        "esporte": "sporty",
        "desportivo": "sporty",
        "desportiva": "sporty",
        "desportivas": "sporty",
        "streetwear": "streetwear",
        "elegante": "elegant",
        "confortavel": "comfortable",
        "confortável": "comfortable",
        "confortaveis": "comfortable",
        "confortáveis": "comfortable",
        "trabalho": "work",
        "escritório": "work",
        "escritorio": "work",
        "praia": "beach",
        "noite": "evening",
        "party": "party",
        "festinha": "party",
        "festa": "party",
        "reunião": "formal",
        "apresentação": "formal",
        "entrevista": "formal",
        "yoga": "fitness",
        "academia": "fitness",
        "treino": "fitness",
        # English
        "formal": "formal",
        "casual": "casual",
        "sporty": "sporty",
        "athletic": "sporty",
        "streetwear": "streetwear",
        "elegant": "elegant",
        "comfortable": "comfortable",
        "work": "work",
        "office": "work",
        "beach": "beach",
        "evening": "evening",
        "party": "party",
        "meeting": "formal",
        "presentation": "formal",
        "interview": "formal",
        "yoga": "fitness",
        "gym": "fitness",
        "training": "fitness",
        "workout": "fitness",
    }

    TYPE_TO_SECTION = {
        "sneakers": "shoes",
        "shoes": "shoes",
        "boots": "shoes",
        "sandals": "shoes",
        "jacket": "outer",
        "sweater": "insulation",
        "hoodie": "insulation",
        "cardigan": "insulation",
        "tshirt": "base",
        "t-shirt": "base",
        "shirt": "base",
        "blouse": "base",
        "top": "base",
        "pants": "pants",
        "shorts": "pants",
        "skirt": "skirt",
        "dress": "dress",
        "jumpsuit": "jumpsuit",
        "bag": "bag",
        "accessory": "accessories",
        "accessories": "accessories",
        "tie": "accessories",
        "scarf": "accessories",
        "socks": "accessories",
        "belt": "accessories",
    }

    def __init__(self):
        """Initialize the parser."""
        pass

    def parse_user_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Parse a user outfit request into a compact intent object.

        Output is the generic intent object consumed by recommendations.
        """
        empty_intent = {
            "requested_colors": [],
            "requested_types": [],
            "requested_style": None,
            "must_include_items": [],
            "avoid_items": [],
            "replace_sections": [],
            "keep_sections": [],
            "mode": "new_outfit",
        }
        if not user_input or not isinstance(user_input, str):
            return empty_intent

        normalized_text = self._normalize_text(user_input)
        avoid = self._extract_avoid(normalized_text, user_input)
        searchable_text = self._remove_avoid_segments(normalized_text)
        requested_colors = self._extract_all_mappings(searchable_text, self.COLOR_MAPPINGS)
        requested_types = self._extract_all_mappings(searchable_text, self.TYPE_MAPPINGS)
        replace_sections = self._extract_section_commands(searchable_text, action="replace")
        keep_sections = self._extract_section_commands(searchable_text, action="keep")
        if not replace_sections and not keep_sections and self._has_replace_language(searchable_text):
            replace_sections = self._sections_for_types(requested_types)
        if not keep_sections and self._has_keep_language(searchable_text):
            keep_sections = self._sections_for_types(requested_types)

        mode = "new_outfit"
        if avoid:
            mode = "avoid_piece"
        if replace_sections or self._has_replace_language(searchable_text):
            mode = "replace_piece"
        if keep_sections:
            mode = "keep_piece"

        must_include_items: List[Dict[str, str]] = []
        for combo in self._extract_color_type_combos(searchable_text):
            must_include_items.append({
                key: combo[key] for key in ("type", "color") if combo.get(key)
            })

        item_name = self._extract_include_name(user_input)
        if item_name and not must_include_items:
            must_include_items.append({"name": item_name})

        if not must_include_items and (requested_colors or requested_types):
            item: Dict[str, str] = {}
            if requested_types:
                item["type"] = requested_types[0]
            if requested_colors:
                item["color"] = requested_colors[0]
            must_include_items.append(item)

        return {
            "requested_colors": requested_colors,
            "requested_types": requested_types,
            "requested_style": self._extract_primary_style(searchable_text),
            "must_include_items": must_include_items,
            "avoid_items": [avoid] if avoid else [],
            "replace_sections": replace_sections,
            "keep_sections": keep_sections,
            "mode": mode,
        }

    def parse_request(self, user_text: str) -> Dict[str, Any]:
        """
        Parse user request text and extract structured constraints.

        Args:
            user_text: User's natural language request

        Returns:
            Dictionary with extracted constraints:
            {
                "must_include": {
                    "type": [...],
                    "color": [...],
                    "name": [...]
                },
                "style": [...],
                "occasion": [...],
                "raw_text": str,
                "parsed_items": list of parsed items
            }
        """
        if not user_text or not isinstance(user_text, str):
            return {
                "must_include": {"type": [], "color": [], "name": []},
                "style": [],
                "occasion": [],
                "raw_text": "",
                "parsed_items": [],
            }

        text_lower = self._normalize_text(user_text)
        intent = self.parse_user_intent(user_text)
        result = {
            "must_include": {"type": [], "color": [], "name": []},
            "style": [],
            "occasion": [],
            "raw_text": user_text,
            "parsed_items": [],
            "intent": intent,
            "requested_colors": intent["requested_colors"],
            "requested_types": intent["requested_types"],
            "requested_style": intent["requested_style"],
            "must_include_items": intent["must_include_items"],
            "avoid_items": intent["avoid_items"],
            "replace_sections": intent["replace_sections"],
            "keep_sections": intent["keep_sections"],
            "mode": intent["mode"],
        }

        must_include = intent.get("must_include_items", [])
        for item in must_include:
            if item.get("type") and item["type"] not in result["must_include"]["type"]:
                result["must_include"]["type"].append(item["type"])
            if item.get("color") and item["color"] not in result["must_include"]["color"]:
                result["must_include"]["color"].append(item["color"])
            if item.get("name") and item["name"] not in result["must_include"]["name"]:
                result["must_include"]["name"].append(item["name"])
        if must_include:
            result["parsed_items"].append({
                "kind": "must_include",
                "items": must_include,
            })

        # Extract item names (quoted or with specific patterns)
        name_matches = self._extract_item_names(user_text, text_lower)
        for match in name_matches:
            if match["name"] and match["name"] not in result["must_include"]["name"]:
                result["must_include"]["name"].append(match["name"])
            result["parsed_items"].append(match)

        # Extract style/occasion
        style_matches = self._extract_styles(text_lower)
        for match in style_matches:
            if match["type"] == "style":
                if match["value"] not in result["style"]:
                    result["style"].append(match["value"])
            elif match["type"] == "occasion":
                if match["value"] not in result["occasion"]:
                    result["occasion"].append(match["value"])
            result["parsed_items"].append(match)

        if intent.get("avoid_items"):
            first_avoid = intent["avoid_items"][0]
            result["avoid"] = first_avoid
            result["parsed_items"].append({
                "kind": "avoid",
                **first_avoid,
            })

        # Remove empty entries
        if not result["must_include"]["type"]:
            del result["must_include"]["type"]
        if not result["must_include"]["color"]:
            del result["must_include"]["color"]
        if not result["must_include"]["name"]:
            del result["must_include"]["name"]
        if not result["style"]:
            del result["style"]
        if not result["occasion"]:
            del result["occasion"]

        return result

    def _normalize_text(self, text: str) -> str:
        """Lowercase text and remove accents while keeping word boundaries."""
        decomposed = unicodedata.normalize("NFD", text or "")
        without_accents = "".join(
            char for char in decomposed if unicodedata.category(char) != "Mn"
        )
        return without_accents.lower().strip()

    def _mapping_pattern(self, mapping: Dict[str, str]) -> str:
        aliases = {
            self._normalize_text(alias)
            for alias in mapping
            if self._normalize_text(alias)
        }
        return r"(?:%s)" % "|".join(
            re.escape(alias) for alias in sorted(aliases, key=len, reverse=True)
        )

    def _find_first_mapping(self, text: str, mapping: Dict[str, str]) -> Optional[str]:
        for alias in sorted(mapping, key=len, reverse=True):
            normalized_alias = self._normalize_text(alias)
            if re.search(r"\b" + re.escape(normalized_alias) + r"\b", text):
                return mapping[alias]
        return None

    def _extract_all_mappings(self, text: str, mapping: Dict[str, str]) -> List[str]:
        found = []
        for alias in sorted(mapping, key=len, reverse=True):
            normalized_alias = self._normalize_text(alias)
            if re.search(r"\b" + re.escape(normalized_alias) + r"\b", text):
                value = mapping[alias]
                if value not in found:
                    found.append(value)
        return found

    def _extract_first_color_type(self, text: str) -> Dict[str, str]:
        color_pattern = self._mapping_pattern(self.COLOR_MAPPINGS)
        type_pattern = self._mapping_pattern(self.TYPE_MAPPINGS)

        patterns = [
            rf"\b(?P<type>{type_pattern})(?:\s+\w+){{0,2}}\s+(?P<color>{color_pattern})\b",
            rf"\b(?P<color>{color_pattern})(?:\s+\w+){{0,2}}\s+(?P<type>{type_pattern})\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                raw_type = match.group("type")
                raw_color = match.group("color")
                return {
                    "type": self.TYPE_MAPPINGS.get(raw_type, raw_type),
                    "color": self.COLOR_MAPPINGS.get(raw_color, raw_color),
                }

        return {}

    def _extract_primary_style(self, text: str) -> Optional[str]:
        style_priority = ["formal", "casual", "sporty", "streetwear", "elegant", "comfortable"]
        found_styles = []

        for alias, normalized in self.STYLE_MAPPINGS.items():
            normalized_alias = self._normalize_text(alias)
            if re.search(r"\b" + re.escape(normalized_alias) + r"\b", text):
                if normalized in style_priority and normalized not in found_styles:
                    found_styles.append(normalized)

        for style in style_priority:
            if style in found_styles:
                return style

        return None

    def _extract_avoid(self, normalized_text: str, original_text: str) -> Dict[str, str]:
        patterns = [
            r"\bnao\s+quero\s+(?:usar\s+)?(?:a\s+|o\s+|as\s+|os\s+|the\s+)?(?P<name>.+?)(?=\s+(?:com|para|for|porque|hoje)\b|[,\.\!\?]|$)",
            r"\bsem\s+(?:a\s+|o\s+|as\s+|os\s+|the\s+)?(?P<name>.+?)(?=\s+(?:com|para|for|porque|hoje)\b|[,\.\!\?]|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized_text)
            if match:
                raw_name = original_text[match.start("name"):match.end("name")]
                name = raw_name.strip(" .,!?")
                normalized_name = self._normalize_text(name)
                item_type = self._find_first_mapping(normalized_name, self.TYPE_MAPPINGS)
                color = self._find_first_mapping(normalized_name, self.COLOR_MAPPINGS)
                avoid: Dict[str, str] = {}
                if item_type:
                    avoid["type"] = item_type
                if color:
                    avoid["color"] = color
                if not avoid and name:
                    avoid["name"] = name
                if avoid:
                    return avoid

        return {}

    def _remove_avoid_segments(self, normalized_text: str) -> str:
        return re.sub(
            r"\b(?:nao\s+quero|sem)\s+.+?(?=\s+(?:com|para|for|porque|hoje)\b|[,\.\!\?]|$)",
            " ",
            normalized_text,
        )

    def _extract_include_name(self, original_text: str) -> Optional[str]:
        patterns = [
            r"(?:quero\s+)?(?:usar|use|wear)\s+(?:a\s+|o\s+|as\s+|os\s+|the\s+)?(?P<name>[A-Z][\w\s\-]+?)(?=\s*$|[,\.\!\?]|\s+(?:para|to|for|e))",
            r"\bcom\s+(?:a\s+|o\s+|as\s+|os\s+|the\s+)?(?P<name>[A-Z][\w\s\-]+?)(?=\s*$|[,\.\!\?]|\s+(?:para|to|for|e))",
        ]

        for pattern in patterns:
            match = re.search(pattern, original_text)
            if match:
                name = match.group("name").strip()
                if name:
                    return name

        return None

    def _extract_color_type_combos(self, text: str) -> List[Dict[str, Any]]:
        """Extract color + type combinations like 'amarelas sapatilhas' or 'yellow sneakers'."""
        matches = []
        
        # Pattern 1: color before type (e.g., "yellow sneakers")
        color_pattern = self._mapping_pattern(self.COLOR_MAPPINGS)
        type_pattern = self._mapping_pattern(self.TYPE_MAPPINGS)
        pattern1 = rf"(?P<color>{color_pattern})(?:\s+\w+){{0,2}}\s+(?P<type>{type_pattern})"
        
        # Pattern 2: type before color (e.g., "sapatilhas amarelas")
        pattern2 = rf"(?P<type>{type_pattern})(?:\s+\w+){{0,2}}\s+(?P<color>{color_pattern})"
        
        found_combos = set()
        
        # Try pattern 1 (color first)
        for match in re.finditer(pattern1, text, re.IGNORECASE):
            color_word = match.group("color")
            type_word = match.group("type")

            color = self.COLOR_MAPPINGS.get(self._normalize_text(color_word))
            item_type = self.TYPE_MAPPINGS.get(self._normalize_text(type_word))

            if color and item_type:
                combo_key = (color, item_type)
                if combo_key not in found_combos:
                    matches.append({
                        "kind": "color_type_combo",
                        "color": color,
                        "type": item_type,
                        "raw": match.group(0),
                    })
                    found_combos.add(combo_key)
        
        # Try pattern 2 (type first)
        for match in re.finditer(pattern2, text, re.IGNORECASE):
            type_word = match.group("type")
            color_word = match.group("color")

            color = self.COLOR_MAPPINGS.get(self._normalize_text(color_word))
            item_type = self.TYPE_MAPPINGS.get(self._normalize_text(type_word))

            if color and item_type:
                combo_key = (color, item_type)
                if combo_key not in found_combos:
                    matches.append({
                        "kind": "color_type_combo",
                        "color": color,
                        "type": item_type,
                        "raw": match.group(0),
                    })
                    found_combos.add(combo_key)

        return matches

    def _has_replace_language(self, text: str) -> bool:
        return re.search(r"\b(troca|trocar|muda|mudar|replace|change|swap)\b", text) is not None

    def _has_keep_language(self, text: str) -> bool:
        return re.search(r"\b(mantem|manter|keep|hold)\b", text) is not None

    def _sections_for_types(self, item_types: List[str]) -> List[str]:
        sections = []
        for item_type in item_types:
            section = self.TYPE_TO_SECTION.get(item_type)
            if section and section not in sections:
                sections.append(section)
        return sections

    def _extract_section_commands(self, text: str, action: str) -> List[str]:
        if action == "replace":
            verbs = r"(?:troca|trocar|muda|mudar|substitui|replace|change|swap)"
        else:
            verbs = r"(?:mantem|manter|mantém|keep|hold)"

        sections: List[str] = []
        type_pattern = self._mapping_pattern(self.TYPE_MAPPINGS)
        for match in re.finditer(rf"\b{verbs}\b(?:\s+\w+){{0,4}}\s+(?P<type>{type_pattern})\b", text):
            item_type = self.TYPE_MAPPINGS.get(self._normalize_text(match.group("type")))
            section = self.TYPE_TO_SECTION.get(item_type)
            if section and section not in sections:
                sections.append(section)

        if action == "replace" and re.search(r"\b(?:so|só|only)\s+(?:uma|one)\s+(?:peca|peça|piece)\b", text):
            if "one_item" not in sections:
                sections.append("one_item")

        return sections

    def _extract_types(
        self,
        text: str,
        already_matched_combos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract item types that haven't been matched in combos."""
        matches = []
        already_matched_types = {m.get("type") for m in already_matched_combos if m.get("type")}

        for type_word, normalized in self.TYPE_MAPPINGS.items():
            if re.search(r"\b" + re.escape(type_word) + r"\b", text):
                if normalized not in already_matched_types:
                    matches.append({
                        "kind": "item_type",
                        "type": normalized,
                        "value": normalized,
                        "raw": type_word,
                    })
                    already_matched_types.add(normalized)

        return matches

    def _extract_item_names(self, original_text: str, text_lower: str) -> List[Dict[str, Any]]:
        """Extract specific item names (quoted, after 'usar', 'with', etc)."""
        matches = []
        found_names = set()

        # Pattern 1: Quoted names "Work Jacket" or 'Work Jacket'
        quoted_pattern = r'["\']([^"\']+)["\']'
        for match in re.finditer(quoted_pattern, original_text):
            item_name = match.group(1).strip()
            if item_name and item_name not in found_names:
                matches.append({
                    "type": "quoted_name",
                    "name": item_name,
                    "raw": match.group(0),
                })
                found_names.add(item_name)

        # Pattern 2: Capitalized sequences after verbs
        # Matches: "usar a Work Jacket", "use the Work Jacket", "com a My Jacket"
        # The pattern must end at: word boundary, end of string, or punctuation
        verb_pattern = r"(?:quero\s+)?(?:usar|use|wear|with|com)\s+(?:a\s+|the\s+|my\s+|o\s+)([A-Z][a-zA-Z\s]+?)(?=\s*$|[,\.\!\?]|\s+(?:para|to|for|e))"
        for match in re.finditer(verb_pattern, original_text, re.IGNORECASE):
            item_name = match.group(1).strip()
            if item_name and len(item_name) > 2 and item_name not in found_names:
                matches.append({
                    "type": "specific_pattern",
                    "name": item_name,
                    "raw": match.group(0),
                })
                found_names.add(item_name)

        return matches

    def _extract_styles(self, text: str) -> List[Dict[str, Any]]:
        """Extract style and occasion keywords."""
        matches = []
        found_styles = set()
        found_occasions = set()

        for style_word, normalized in self.STYLE_MAPPINGS.items():
            normalized_style_word = self._normalize_text(style_word)
            if re.search(r"\b" + re.escape(normalized_style_word) + r"\b", text):
                # Determine if it's a style or occasion
                is_occasion = style_word in [
                    "trabalho", "escritório", "work", "office",
                    "reunião", "apresentação", "entrevista", "meeting", "presentation", "interview",
                    "festa", "party", "noite", "evening",
                    "praia", "beach",
                ]

                if is_occasion and normalized not in found_occasions:
                    matches.append({
                        "type": "occasion",
                        "value": normalized,
                        "raw": style_word,
                    })
                    found_occasions.add(normalized)
                elif not is_occasion and normalized not in found_styles:
                    matches.append({
                        "type": "style",
                        "value": normalized,
                        "raw": style_word,
                    })
                    found_styles.add(normalized)

        return matches


def parse_user_intent(user_input: str) -> Dict[str, Any]:
    """Parse a user outfit request into style, must_include, and avoid intent."""
    return UserRequestParser().parse_user_intent(user_input)
