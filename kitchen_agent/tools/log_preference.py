"""log_preference tool — stores user preferences and feedback in ChromaDB."""
from langchain_core.tools import tool
from kitchen_agent.memory import get_pref_store, get_recipe_store

_pref_store = get_pref_store()
_recipe_store = get_recipe_store()


@tool
def log_preference(
    entity: str,
    preference_type: str,
    value: str,
    notes: str = None,
    user_id: str = "default",
) -> str:
    """Log a user preference or feedback about a food, recipe, ingredient, or cuisine.

    Args:
        entity: What the preference is about (e.g., "salmon", "pasta", "Thai food").
        preference_type: Category of preference. Options:
            - "food" — general food preference (liked/disliked/avoid)
            - "cuisine" — cuisine type (Italian, Mexican, etc.)
            - "diet" — dietary restriction or goal (vegetarian, low-carb, etc.)
            - "cooking_style" — how you like food prepared (spicy, mild, etc.)
            - "allergen" — things to avoid
        value: Your preference value. Options:
            - For food: "liked", "loved", "disliked", "hated", "avoid"
            - For cuisine/diet: any string describing the preference
        notes: Optional free-text notes (e.g., "but only when fresh").
        user_id: User identifier. Defaults to "default".

    Returns:
        A confirmation string showing what was logged.
    """
    _pref_store.add_preference(
        user_id=user_id,
        preference_type=preference_type,
        entity=entity,
        value=value,
        notes=notes,
    )

    note_str = f" — {notes}" if notes else ""
    return (
        f"Logged: {preference_type} preference for '{entity}' → {value}{note_str}"
    )


@tool
def log_recipe_feedback(
    recipe_name: str,
    feedback: str = None,
    rating: int = None,
    ingredients_used: list = None,
    user_id: str = "default",
) -> str:
    """Log that you cooked a recipe and your feedback on it.

    Args:
        recipe_name: Name of the dish you made.
        feedback: Your thoughts — what you liked, what you'd change, etc.
        rating: Star rating 1-5.
        ingredients_used: List of ingredient names you used from inventory.
        user_id: User identifier. Defaults to "default".

    Returns:
        A confirmation string.
    """
    _recipe_store.add_recipe(
        user_id=user_id,
        recipe_name=recipe_name,
        ingredients=ingredients_used or [],
        feedback=feedback,
        rating=rating,
    )
    
    rating_str = f" ({rating}/5 stars)" if rating else ""
    return (
        f"Logged: you made '{recipe_name}'{rating_str}"
        + (f"\nFeedback: {feedback}" if feedback else "")
        + (f"\nUsed: {', '.join(ingredients_used)}" if ingredients_used else "")
    )
