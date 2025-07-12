"""Unit tests for Ana's pricing calculator."""

from datetime import date

import pytest
from aria.agents.ana.calculator import PricingCalculator
from aria.agents.ana.models import MealPlan, ReservationRequest, RoomType


class TestPricingCalculator:
    """Test pricing calculations."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return PricingCalculator()

    @pytest.fixture
    def basic_request(self):
        """Create basic reservation request."""
        return ReservationRequest(
            check_in=date(2025, 2, 10),
            check_out=date(2025, 2, 12),
            adults=2,
            children=[]
        )

    def test_calculate_normal_pricing(self, calculator, basic_request):
        """Test normal (non-holiday) pricing calculation."""
        prices = calculator.calculate(basic_request)

        # Should return 6 options (2 room types × 3 meal plans)
        assert len(prices) == 6

        # Check all combinations exist
        room_types = {p.room_type for p in prices}
        meal_plans = {p.meal_plan for p in prices}

        assert room_types == {RoomType.TERREO, RoomType.SUPERIOR}
        assert meal_plans == {MealPlan.CAFE_DA_MANHA, MealPlan.MEIA_PENSAO, MealPlan.PENSAO_COMPLETA}

    def test_pricing_calculation_accuracy(self, calculator, basic_request):
        """Test specific pricing calculations."""
        prices = calculator.calculate(basic_request)

        # Find specific price
        terreo_cafe = next(
            p for p in prices
            if p.room_type == RoomType.TERREO and p.meal_plan == MealPlan.CAFE_DA_MANHA
        )

        # 2 adults, terreo, cafe da manha: R$ 290/night × 2 nights = R$ 580
        assert terreo_cafe.total == 580.0
        assert terreo_cafe.total_per_night == 290.0
        assert terreo_cafe.nights == 2

    def test_children_pricing(self, calculator):
        """Test pricing with children."""
        request = ReservationRequest(
            check_in=date(2025, 2, 10),
            check_out=date(2025, 2, 12),
            adults=2,
            children=[4, 7]  # One 3-5 years, one 6-10 years
        )

        prices = calculator.calculate(request)

        # Find terreo with breakfast
        terreo_cafe = next(
            p for p in prices
            if p.room_type == RoomType.TERREO and p.meal_plan == MealPlan.CAFE_DA_MANHA
        )

        # Adults: 290/night
        # Child 3-5: 40/night
        # Child 6-10: 50/night
        # Total per night: 290 + 40 + 50 = 380
        # Total for 2 nights: 760
        assert terreo_cafe.total_per_night == 380.0
        assert terreo_cafe.total == 760.0

    def test_easter_holiday_pricing(self, calculator):
        """Test Easter package pricing."""
        request = ReservationRequest(
            check_in=date(2025, 4, 18),
            check_out=date(2025, 4, 21),
            adults=2,
            children=[],
            is_holiday=True
        )

        prices = calculator.calculate(request)

        # Holiday packages only have pensao completa
        assert all(p.meal_plan == MealPlan.PENSAO_COMPLETA for p in prices)

        # Find terreo option
        terreo = next(p for p in prices if p.room_type == RoomType.TERREO)

        # 3 nights, 2 adults, terreo: R$ 2709.30
        assert terreo.total == 2709.30

    def test_promo_code_sorocaba(self, calculator):
        """Test Sorocaba promo code."""
        request = ReservationRequest(
            check_in=date(2025, 2, 10),
            check_out=date(2025, 2, 12),
            adults=2,
            children=[],
            promo_code="SOC10"
        )

        prices = calculator.calculate(request)

        # All prices should have 10% discount
        for price in prices:
            assert price.breakdown.discount_percentage == 10.0
            assert price.breakdown.discount_amount > 0

    def test_minimum_nights_validation(self, calculator):
        """Test that calculator handles single night stays."""
        request = ReservationRequest(
            check_in=date(2025, 2, 10),
            check_out=date(2025, 2, 11),  # 1 night
            adults=1,
            children=[]
        )

        prices = calculator.calculate(request)

        assert len(prices) > 0
        assert all(p.nights == 1 for p in prices)

    def test_format_pricing_message(self, calculator, basic_request):
        """Test message formatting."""
        prices = calculator.calculate(basic_request)
        message = calculator.format_pricing_message(prices)

        assert "Segue abaixo as opções de hospedagem:" in message
        assert "Apenas café da manhã" in message
        assert "Meia pensão" in message
        assert "Pensão completa" in message
        assert "Térreo:" in message
        assert "Superior:" in message
