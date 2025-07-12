"""Knowledge base for Hotel Passarim - Ana's core information."""

from datetime import date
from typing import Dict, List, Optional

# Hotel basic information
HOTEL_INFO = {
    "name": "Hotel Passarim",
    "location": "Capão Bonito, SP",
    "address": "Rua Example, 123, Capão Bonito - SP",
    "check_in_time": "14:00",
    "check_out_time": "12:00",
    "wifi_password": "passarim2025",
    "phone": "+55 15 3542-0000",
    "whatsapp": "+55 11 95772-1122",
    "website": "https://www.hotelpassarim.com.br",
    "restaurant_hours": {
        "breakfast": "07:00 às 11:00",
        "lunch": "12:00 às 15:00 (terça a domingo)",
        "dinner": "19:30 às 22:00 (terça a sábado)",
        "friday_saturday_pasta": "19:00 às 22:00"
    },
    "amenities": [
        "Piscina de água natural",
        "Sauna seca",
        "Sala de jogos",
        "Lago com caiaques e stand-up paddle",
        "Pesca esportiva",
        "Ofurô externo",
        "Wi-Fi gratuito",
        "Estacionamento gratuito"
    ]
}

# Pricing tables for normal days (not holidays)
PRICING_TABLE_NORMAL = {
    "terreo": {
        # Adults: {meal_plan: price}
        1: {
            "cafe_da_manha": 199,
            "meia_pensao": 279,
            "pensao_completa": 359
        },
        2: {
            "cafe_da_manha": 290,
            "meia_pensao": 460,
            "pensao_completa": 610
        },
        3: {
            "cafe_da_manha": 350,
            "meia_pensao": 590,
            "pensao_completa": 830
        },
        4: {
            "cafe_da_manha": 420,
            "meia_pensao": 740,
            "pensao_completa": 1060
        }
    },
    "superior": {
        1: {
            "cafe_da_manha": 239,
            "meia_pensao": 319,
            "pensao_completa": 399
        },
        2: {
            "cafe_da_manha": 350,
            "meia_pensao": 520,
            "pensao_completa": 670
        },
        3: {
            "cafe_da_manha": 420,
            "meia_pensao": 660,
            "pensao_completa": 900
        },
        4: {
            "cafe_da_manha": 490,
            "meia_pensao": 840,
            "pensao_completa": 1130
        }
    }
}

# Children pricing supplements
CHILDREN_PRICING = {
    # Age range: {meal_plan: price}
    "3_to_5": {
        "cafe_da_manha": 40,
        "meia_pensao": 130,
        "pensao_completa": 200
    },
    "6_to_10": {
        "cafe_da_manha": 50,
        "meia_pensao": 130,
        "pensao_completa": 210
    }
}

# Easter package pricing
EASTER_PACKAGE = {
    "name": "Pacote de Páscoa",
    "start_date": date(2025, 4, 17),
    "end_date": date(2025, 4, 21),
    "min_nights": 3,
    "discount_until": date(2025, 4, 5),
    "discount_percentage": 10,
    "includes": [
        "Hospedagem com pensão completa",
        "Jantar especial de quinta-feira (17/04)",
        "Bacalhoada da Sexta-feira Santa (18/04)",
        "Rodízio de massas no sábado (19/04)",
        "Bacalhoada de Páscoa no domingo (20/04)",
        "Check-out estendido até 15h na segunda-feira",
        "Todas as atividades de lazer inclusas"
    ],
    "pricing": {
        "terreo": {
            4: {  # 4 nights
                1: 2156.00,
                2: 3284.00,
                3: 4368.00,
                4: 5496.00,
                "child_3_5": 968.00,
                "child_6_10": 1032.00
            },
            3: {  # 3 nights
                1: 1778.70,
                2: 2709.30,
                3: 3603.60,
                4: 4534.20,
                "child_3_5": 798.60,
                "child_6_10": 851.40
            },
            2: {  # 2 nights
                1: 1239.70,
                2: 1888.30,
                3: 2511.60,
                4: 3160.20,
                "child_3_5": 556.60,
                "child_6_10": 593.40
            },
            1: {  # 1 night
                1: 646.80,
                2: 985.20,
                3: 1310.40,
                4: 1648.80,
                "child_3_5": 290.40,
                "child_6_10": 309.60
            }
        },
        "superior": {
            4: {  # 4 nights
                1: 2371.60,
                2: 3612.40,
                3: 4804.80,
                4: 6045.60,
                "child_3_5": 1064.80,
                "child_6_10": 1135.20
            },
            3: {  # 3 nights
                1: 1956.57,
                2: 2980.23,
                3: 3963.96,
                4: 4987.62,
                "child_3_5": 878.46,
                "child_6_10": 936.54
            },
            2: {  # 2 nights
                1: 1363.67,
                2: 2077.13,
                3: 2762.76,
                4: 3476.22,
                "child_3_5": 612.26,
                "child_6_10": 652.74
            },
            1: {  # 1 night
                1: 711.48,
                2: 1083.72,
                3: 1441.44,
                4: 1813.68,
                "child_3_5": 319.44,
                "child_6_10": 340.56
            }
        }
    }
}

# Other holiday packages
HOLIDAY_PACKAGES = {
    "pascoa": EASTER_PACKAGE,
    "natal": {
        "name": "Pacote de Natal",
        "start_date": date(2025, 12, 23),
        "end_date": date(2025, 12, 26),
        "min_nights": 3
    },
    "ano_novo": {
        "name": "Pacote de Ano Novo", 
        "start_date": date(2025, 12, 29),
        "end_date": date(2026, 1, 2),
        "min_nights": 3
    }
}

# Room descriptions
ROOM_DESCRIPTIONS = {
    "terreo": {
        "name": "Apartamento Térreo",
        "description": "Piso cerâmico, ideal para quem precisa de acessibilidade",
        "amenities": [
            "Ar-condicionado quente e frio",
            "Wi-Fi",
            "TV a cabo",
            "Frigobar",
            "Mesa com duas cadeiras",
            "Cadeira de balanço",
            "Cama box",
            "Ducha com aquecimento central",
            "Secador de cabelo",
            "Terraço"
        ]
    },
    "superior": {
        "name": "Apartamento Superior",
        "description": "Mais reservado, piso de madeira, menos sujeito a ruídos externos",
        "amenities": [
            "Ar-condicionado quente e frio",
            "Wi-Fi",
            "TV a cabo",
            "Frigobar", 
            "Mesa com duas cadeiras",
            "Cadeira de balanço",
            "Cama box",
            "Ducha com aquecimento central",
            "Secador de cabelo",
            "Terraço"
        ]
    }
}

# Meal plan descriptions
MEAL_PLAN_DESCRIPTIONS = {
    "cafe_da_manha": "Apenas café da manhã incluso",
    "meia_pensao": "Café da manhã + 1 refeição (almoço ou jantar)",
    "pensao_completa": "Café da manhã + almoço + jantar (bebidas não inclusas)"
}

# Pasta rotation menu
PASTA_ROTATION = {
    "friday_saturday": {
        "name": "Rodízio de Massas",
        "hours": "19:00 às 22:00",
        "days": ["sexta-feira", "sábado"],
        "price_adult": 74.90,
        "price_child": 35.90,  # 5-12 years
        "includes": [
            "Antepastos italianos",
            "4 tipos de ravioli",
            "2 tipos de rondelli",
            "Massas secas (penne e espaguete)",
            "Molhos artesanais da casa"
        ],
        "reservation_required": True,
        "prepayment": 15.00  # Per person via PIX
    }
}

# Promotional codes
PROMO_CODES = {
    "SOC10": {
        "description": "Desconto para moradores de Sorocaba",
        "discount": 10,
        "type": "percentage",
        "valid_for": ["sorocaba"],
        "excluded_dates": ["holidays"],
        "requires_validation": True
    }
}


def is_holiday_period(check_in: date, check_out: date) -> Optional[Dict]:
    """Check if dates fall within a holiday period."""
    for holiday_key, holiday in HOLIDAY_PACKAGES.items():
        if check_in >= holiday["start_date"] and check_out <= holiday["end_date"]:
            return holiday
    return None


def get_children_age_category(age: int) -> Optional[str]:
    """Get pricing category for child based on age."""
    if age < 3:
        return None  # Free
    elif 3 <= age <= 5:
        return "3_to_5"
    elif 6 <= age <= 10:
        return "6_to_10"
    else:
        return None  # Counts as adult
