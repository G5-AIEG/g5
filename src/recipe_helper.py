"""
src/recipe_helper.py
====================
Core recipe matching and suggestion logic for the Recipe Suggestion Helper CLI.

This module provides:
- Ingredient parsing and normalization
- Recipe matching with ingredient overlap counting
- Dietary preference filtering
- Recipe display formatting
- Ingredient substitution suggestions
- Recipe lookup by index or title

The recipe database is loaded from recipes.json on module import.
"""
import json
import os
from typing import List, Dict, Any, Tuple

# Load recipe database from JSON file in project root
BASE = os.path.dirname(os.path.dirname(__file__))
RECIPES_PATH = os.path.join(BASE, "recipes.json")

with open(RECIPES_PATH, "r", encoding="utf-8") as f:
    RECIPES = json.load(f)


def normalize(text: str) -> str:
    """Normalize text for case-insensitive matching.
    
    Args:
        text: Input string
        
    Returns:
        Lowercased and whitespace-stripped string
    """
    return text.lower().strip()


def parse_ingredients(text: str) -> List[str]:
    """Parse comma or semicolon-separated ingredient input into normalized list.
    
    Handles:
    - "chicken, rice, broccoli"
    - "tofu; bell pepper; soy sauce"
    - Mixed separators and extra spaces
    
    Args:
        text: Raw user input string
        
    Returns:
        List of normalized ingredients
    """
    import re

    # Split on commas or semicolons first (preferred explicit separators)
    parts = [p.strip() for p in re.split(r"[;,]", text) if p.strip()]

    # If user didn't use commas/semicolons and provided a space-separated list
    # (e.g. `chicken rice broccoli`), split on whitespace as a fallback.
    if len(parts) == 1 and " " in text and "," not in text and ";" not in text:
        parts = [p.strip() for p in text.split() if p.strip()]

    normalized = [normalize(p) for p in parts]
    return normalized


def match_recipes(ingredients: List[str], min_match: int = 2, diet: str = None) -> List[Tuple[Dict[str, Any], int]]:
    """Find recipes matching user ingredients with optional dietary filtering.
    
    Algorithm:
    1. Filter recipes by diet (if specified)
    2. Count matching ingredients per recipe (intersection of ingredient sets)
    3. Keep only recipes with >= min_match matching ingredients
    4. Sort by match count (descending) then title (ascending)
    
    Args:
        ingredients: List of user ingredients
        min_match: Minimum required ingredient matches (default: 2)
        diet: Optional dietary filter string (e.g., "vegan", "halal")
        
    Returns:
        List of (recipe_dict, match_count) tuples, sorted by best matches
    """
    # Normalize user-provided ingredients
    ing_set = set([normalize(i) for i in ingredients])
    matches = []
    
    for r in RECIPES:
        # Apply dietary filter if specified
        if diet:
            diets = [normalize(d) for d in r.get("diets", [])]
            if normalize(diet) not in diets:
                continue  # Skip recipes that don't match user's diet
        
        # Count ingredient overlap
        recipe_ings_list = [normalize(i) for i in r.get("ingredients", [])]

        # Allow substring and exact matches: e.g., user 'soba' matches 'soba noodles'
        matched = set()
        for u in ing_set:
            for ri in recipe_ings_list:
                if u == ri or u in ri or ri in u:
                    matched.add(ri)

        count = len(matched)
        
        # Keep recipe if it meets minimum threshold
        if count >= min_match:
            matches.append((r, count))
    
    # Sort: most matches first, then alphabetical
    matches.sort(key=lambda x: (-x[1], x[0]["title"]))
    return matches


def explain_recipe(recipe: Dict[str, Any]) -> str:
    """Format recipe for display to user.
    
    Includes:
    - Recipe title and time
    - Dietary tags
    - Numbered step-by-step instructions
    
    Args:
        recipe: Recipe dictionary with title, time, diets, steps
        
    Returns:
        Formatted multi-line string ready to print
    """
    lines = []
    lines.append(f"{recipe.get('title')} ({recipe.get('time', 'N/A')})")
    
    if recipe.get("diets"):
        lines.append(f"Dietary tags: {', '.join(recipe.get('diets'))}")
    
    lines.append("")  # Blank line for readability
    
    steps = recipe.get("steps", [])
    for i, s in enumerate(steps, 1):
        lines.append(f"- Step {i}: {s}")
    
    return "\n".join(lines)


# Ingredient substitution map for handling "I don't have X" questions
# Each entry: missing_ingredient -> suggested_alternative
# Includes culturally-appropriate swaps (e.g., tofu/lentils for meat)
SUBSTITUTIONS = {
    "butter": "oil",
    "milk": "plant milk or water",
    "egg": "mashed banana or applesauce (for baking)",
    "sour cream": "yogurt",
    "cream": "milk",
    "broth": "water + seasoning",
    "chicken": "tofu or chickpeas",
    "beef": "lentils or mushrooms",
    "fish": "tofu or beans",
}


def suggest_substitute(ingredient: str) -> str:
    """Suggest an alternative ingredient.
    
    Args:
        ingredient: Missing ingredient name
        
    Returns:
        Suggestion string or "I don't have a suggestion for that ingredient"
    """
    k = normalize(ingredient)
    return SUBSTITUTIONS.get(k, "I don't have a suggestion for that ingredient")


def find_recipe_by_title_or_index(query: str) -> Dict[str, Any]:
    """Look up a recipe by numeric index (1-based) or partial title match.
    
    Matching:
    - "1" matches RECIPES[0] (1-based for user convenience)
    - "stir" matches "Tofu Stir-Fry" (case-insensitive substring)
    
    Args:
        query: Either a number string or recipe title (partial)
        
    Returns:
        Recipe dict if found, empty dict otherwise
    """
    q = normalize(query)
    
    # Try numeric index (1-based for user-friendly UX)
    if q.isdigit():
        idx = int(q) - 1
        if 0 <= idx < len(RECIPES):
            return RECIPES[idx]
    
    # Try partial title match
    for r in RECIPES:
        if q in normalize(r.get("title", "")):
            return r
    
    return {}


def get_available_diets() -> List[str]:
    """Get all dietary categories available in recipe database.
    
    Returns:
        Sorted list of unique diet tags (e.g., ["halal", "kosher", "vegan", ...])
    """
    diets = set()
    for r in RECIPES:
        diets.update(r.get("diets", []))
    return sorted(list(diets))

