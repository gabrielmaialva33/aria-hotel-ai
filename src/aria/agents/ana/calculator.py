"""Pricing calculator for Hotel Passarim reservations."""

from datetime import date
from typing import List, Optional, Tuple

from aria.agents.ana.knowledge_base import (
    CHILDREN_PRICING,
    EASTER_PACKAGE,
    HOLIDAY_PACKAGES,
    PRICING_TABLE_NORMAL,
    PROMO_CODES,
    get_children_age_category,
    is_holiday_period,
)
from aria.agents.ana.models import (
    MealPlan,
    Pricing,
    PricingBreakdown,
    ReservationRequest,
    RoomType,
)
from aria.core.logging import get_logger

logger = get_logger(__name__)


class PricingCalculator:
    """Calculate pricing for hotel reservations."""
    
    def calculate(self, request: ReservationRequest) -> List[Pricing]:
        """
        Calculate pricing for all available options.
        
        Returns list of pricing options for different room types and meal plans.
        """
        prices = []
        
        # Check if it's a holiday period
        holiday = is_holiday_period(request.check_in, request.check_out)
        
        if holiday:
            # Holiday packages have fixed pricing
            prices = self._calculate_holiday_pricing(request, holiday)
        else:
            # Normal pricing with different meal plans
            prices = self._calculate_normal_pricing(request)
        
        # Apply promotional codes if applicable
        if request.promo_code:
            prices = self._apply_promo_code(prices, request)
        
        return prices
    
    def _calculate_normal_pricing(self, request: ReservationRequest) -> List[Pricing]:
        """Calculate pricing for normal (non-holiday) periods."""
        prices = []
        
        # If specific room type requested, calculate only for that
        room_types = [request.room_type] if request.room_type else list(RoomType)
        meal_plans = [request.meal_plan] if request.meal_plan else list(MealPlan)
        
        for room_type in room_types:
            for meal_plan in meal_plans:
                try:
                    pricing = self._calculate_single_option(
                        request, room_type, meal_plan
                    )
                    prices.append(pricing)
                except Exception as e:
                    logger.error(
                        "Error calculating price",
                        room_type=room_type,
                        meal_plan=meal_plan,
                        error=str(e)
                    )
        
        return prices
    
    def _calculate_single_option(
        self,
        request: ReservationRequest,
        room_type: RoomType,
        meal_plan: MealPlan
    ) -> Pricing:
        """Calculate pricing for a single room type and meal plan option."""
        # Get base rate for adults
        adults = min(request.adults, 4)  # Max 4 per room
        base_rate = PRICING_TABLE_NORMAL[room_type.value][adults][meal_plan.value]
        
        # Calculate children rates
        children_rate = 0.0
        for child_age in request.children:
            category = get_children_age_category(child_age)
            if category:
                children_rate += CHILDREN_PRICING[category][meal_plan.value]
        
        # Calculate totals
        total_per_night = base_rate + children_rate
        total = total_per_night * request.nights
        
        # Create breakdown
        breakdown = PricingBreakdown(
            base_rate=base_rate * request.nights,
            children_rate=children_rate * request.nights,
            meal_supplement=0.0,  # Already included in base rate
            discount_amount=0.0,
            discount_percentage=0.0
        )
        
        return Pricing(
            room_type=room_type,
            meal_plan=meal_plan,
            adults=request.adults,
            children=request.children,
            nights=request.nights,
            total=total,
            total_per_night=total_per_night,
            breakdown=breakdown
        )
    
    def _calculate_holiday_pricing(
        self, 
        request: ReservationRequest,
        holiday: dict
    ) -> List[Pricing]:
        """Calculate pricing for holiday packages."""
        prices = []
        room_types = [request.room_type] if request.room_type else list(RoomType)
        
        # Holiday packages always include full board
        meal_plan = MealPlan.PENSAO_COMPLETA
        
        for room_type in room_types:
            try:
                # Get pricing table for the holiday
                holiday_pricing = holiday["pricing"][room_type.value]
                nights_pricing = holiday_pricing.get(request.nights, {})
                
                if not nights_pricing:
                    logger.warning(
                        "No pricing for nights",
                        nights=request.nights,
                        holiday=holiday["name"]
                    )
                    continue
                
                # Get base rate for adults
                adults = min(request.adults, 4)
                base_rate = nights_pricing.get(adults, 0)
                
                # Calculate children rates
                children_rate = 0.0
                for child_age in request.children:
                    if 3 <= child_age <= 5:
                        children_rate += nights_pricing.get("child_3_5", 0)
                    elif 6 <= child_age <= 10:
                        children_rate += nights_pricing.get("child_6_10", 0)
                
                # Total price
                total = base_rate + children_rate
                
                # Apply early booking discount if applicable
                discount_amount = 0.0
                discount_percentage = 0.0
                
                if (holiday.get("discount_until") and 
                    date.today() <= holiday["discount_until"]):
                    discount_percentage = holiday.get("discount_percentage", 0)
                    discount_amount = total * (discount_percentage / 100)
                    total -= discount_amount
                
                # Create breakdown
                breakdown = PricingBreakdown(
                    base_rate=base_rate,
                    children_rate=children_rate,
                    meal_supplement=0.0,  # Included in package
                    discount_amount=discount_amount,
                    discount_percentage=discount_percentage
                )
                
                pricing = Pricing(
                    room_type=room_type,
                    meal_plan=meal_plan,
                    adults=request.adults,
                    children=request.children,
                    nights=request.nights,
                    total=total,
                    total_per_night=total / request.nights if request.nights > 0 else 0,
                    breakdown=breakdown
                )
                
                prices.append(pricing)
                
            except Exception as e:
                logger.error(
                    "Error calculating holiday price",
                    room_type=room_type,
                    holiday=holiday["name"],
                    error=str(e)
                )
        
        return prices
    
    def _apply_promo_code(
        self,
        prices: List[Pricing],
        request: ReservationRequest
    ) -> List[Pricing]:
        """Apply promotional code to prices."""
        promo = PROMO_CODES.get(request.promo_code.upper())
        
        if not promo:
            return prices
        
        # Check if promo is valid for holidays
        if request.is_holiday and "holidays" in promo.get("excluded_dates", []):
            return prices
        
        # Apply discount
        for price in prices:
            if promo["type"] == "percentage":
                discount = price.total * (promo["discount"] / 100)
                price.total -= discount
                price.total_per_night = price.total / price.nights
                price.breakdown.discount_amount += discount
                price.breakdown.discount_percentage = promo["discount"]
        
        return prices
    
    def format_pricing_message(self, prices: List[Pricing]) -> str:
        """Format pricing options into a message for Ana to send."""
        if not prices:
            return "Desculpe, não encontrei opções disponíveis para essas datas."
        
        # Group by meal plan
        by_meal_plan = {}
        for price in prices:
            if price.meal_plan not in by_meal_plan:
                by_meal_plan[price.meal_plan] = []
            by_meal_plan[price.meal_plan].append(price)
        
        message = "Segue abaixo as opções de hospedagem:\n\n"
        
        # Format each meal plan option
        meal_plan_names = {
            MealPlan.CAFE_DA_MANHA: "☕ Apenas café da manhã",
            MealPlan.MEIA_PENSAO: "🍽️ Meia pensão",
            MealPlan.PENSAO_COMPLETA: "🍴 Pensão completa"
        }
        
        for meal_plan, prices_list in by_meal_plan.items():
            message += f"✔ *{meal_plan_names[meal_plan]}*\n"
            
            for price in prices_list:
                room_name = "Térreo" if price.room_type == RoomType.TERREO else "Superior"
                message += f"   {room_name}: {price.format_price()}"
                
                if price.breakdown.discount_percentage > 0:
                    message += f" (com {price.breakdown.discount_percentage}% de desconto!)"
                
                message += "\n"
            
            message += "\n"
        
        return message.strip()
