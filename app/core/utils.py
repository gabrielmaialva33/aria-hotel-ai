"""Core utilities for the application."""

from typing import Optional
from app.agents.ana.models import MealPlan


def parse_meal_plan(meal_plan_str: str) -> Optional[MealPlan]:
    """
    Parse a user-friendly meal plan string into a MealPlan enum.

    Args:
        meal_plan_str: The user-friendly meal plan string.

    Returns:
        The corresponding MealPlan enum member, or None if no match is found.
    """
    if not meal_plan_str:
        return None

    normalized_str = meal_plan_str.lower().strip()
    if "apenas café" in normalized_str or "café da manhã" in normalized_str:
        return MealPlan.CAFE_DA_MANHA
    elif "meia pensão" in normalized_str or "meia" in normalized_str:
        return MealPlan.MEIA_PENSAO
    elif "pensão completa" in normalized_str or "completa" in normalized_str:
        return MealPlan.PENSAO_COMPLETA
    return None
