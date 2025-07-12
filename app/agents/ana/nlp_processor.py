"""Advanced NLP processor for Ana agent with semantic understanding."""

import re
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.logging import get_logger

logger = get_logger(__name__)


class Intent(Enum):
    """Possible user intents."""
    GREETING = "greeting"
    RESERVATION_INQUIRY = "reservation_inquiry"
    PRICING_REQUEST = "pricing_request"
    AVAILABILITY_CHECK = "availability_check"
    AMENITIES_INFO = "amenities_info"
    RESTAURANT_INFO = "restaurant_info"
    WIFI_INFO = "wifi_info"
    LOCATION_INFO = "location_info"
    CHECKIN_CHECKOUT_INFO = "checkin_checkout_info"
    PASTA_ROTATION = "pasta_rotation"
    COMPLAINT = "complaint"
    THANKS = "thanks"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """Extracted entity from text."""
    type: str
    value: str
    confidence: float
    position: Tuple[int, int]


@dataclass
class NLPResult:
    """Result of NLP processing."""
    intent: Intent
    confidence: float
    entities: List[Entity]
    sentiment: str  # positive, neutral, negative
    language: str  # pt, en, es


class NLPProcessor:
    """Advanced NLP processor with semantic understanding."""
    
    def __init__(self):
        """Initialize NLP processor with models and patterns."""
        # Load sentence transformer for semantic similarity
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Intent examples for semantic matching
        self.intent_examples = {
            Intent.GREETING: [
                "olá", "oi", "bom dia", "boa tarde", "boa noite",
                "hello", "hi", "good morning", "hey there"
            ],
            Intent.RESERVATION_INQUIRY: [
                "quero fazer uma reserva", "gostaria de reservar",
                "tem disponibilidade", "preciso de um quarto",
                "quero me hospedar", "fazer booking"
            ],
            Intent.PRICING_REQUEST: [
                "quanto custa", "qual o valor", "preço da diária",
                "valores para", "quanto fica", "orçamento para"
            ],
            Intent.AVAILABILITY_CHECK: [
                "tem vaga", "está disponível", "tem quarto livre",
                "posso reservar", "tem lugar", "está lotado"
            ],
            Intent.AMENITIES_INFO: [
                "o que tem no hotel", "estrutura do hotel",
                "tem piscina", "área de lazer", "comodidades",
                "facilidades", "o que oferece"
            ],
            Intent.RESTAURANT_INFO: [
                "horário do restaurante", "café da manhã",
                "almoço", "jantar", "cardápio", "refeições"
            ],
            Intent.WIFI_INFO: [
                "senha do wifi", "tem internet", "wifi password",
                "como conectar", "rede sem fio"
            ],
            Intent.PASTA_ROTATION: [
                "rodízio de massas", "rodízio de pasta",
                "noite italiana", "festival de massas"
            ],
            Intent.COMPLAINT: [
                "estou insatisfeito", "péssimo atendimento",
                "quero reclamar", "problema com", "não gostei"
            ],
            Intent.THANKS: [
                "obrigado", "muito obrigada", "agradeço",
                "valeu", "thanks", "thank you"
            ]
        }
        
        # Precompute embeddings for intent examples
        self.intent_embeddings = {}
        for intent, examples in self.intent_examples.items():
            self.intent_embeddings[intent] = self.model.encode(examples)
        
        # Date patterns in Portuguese
        self.date_patterns = [
            # Relative dates
            (r'\b(hoje|today)\b', lambda: date.today()),
            (r'\b(amanhã|tomorrow)\b', lambda: date.today() + timedelta(days=1)),
            (r'\b(depois de amanhã|day after tomorrow)\b', lambda: date.today() + timedelta(days=2)),
            
            # Weekdays
            (r'\b(segunda|segunda-feira|monday)\b', self._next_weekday, 0),
            (r'\b(terça|terça-feira|tuesday)\b', self._next_weekday, 1),
            (r'\b(quarta|quarta-feira|wednesday)\b', self._next_weekday, 2),
            (r'\b(quinta|quinta-feira|thursday)\b', self._next_weekday, 3),
            (r'\b(sexta|sexta-feira|friday)\b', self._next_weekday, 4),
            (r'\b(sábado|saturday)\b', self._next_weekday, 5),
            (r'\b(domingo|sunday)\b', self._next_weekday, 6),
            
            # Relative periods
            (r'\b(este|essa|this)\s+(fim de semana|weekend)\b', self._this_weekend),
            (r'\b(próximo|next)\s+(fim de semana|weekend)\b', self._next_weekend),
            (r'\b(próxima|next)\s+semana\b', self._next_week),
            
            # Specific dates
            (r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', self._parse_date_numbers),
            (r'(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{2,4}))?', self._parse_date_text),
            
            # Holidays
            (r'\b(páscoa|easter)\b', self._easter_date),
            (r'\b(natal|christmas)\b', lambda: date(date.today().year, 12, 25)),
            (r'\b(ano novo|new year)\b', lambda: date(date.today().year + 1, 1, 1)),
        ]
        
        # Month names
        self.months = {
            'janeiro': 1, 'jan': 1, 'january': 1,
            'fevereiro': 2, 'fev': 2, 'february': 2,
            'março': 3, 'mar': 3, 'march': 3,
            'abril': 4, 'abr': 4, 'april': 4,
            'maio': 5, 'mai': 5, 'may': 5,
            'junho': 6, 'jun': 6, 'june': 6,
            'julho': 7, 'jul': 7, 'july': 7,
            'agosto': 8, 'ago': 8, 'august': 8,
            'setembro': 9, 'set': 9, 'september': 9,
            'outubro': 10, 'out': 10, 'october': 10,
            'novembro': 11, 'nov': 11, 'november': 11,
            'dezembro': 12, 'dez': 12, 'december': 12
        }
    
    async def process(self, text: str) -> NLPResult:
        """
        Process text and extract intent, entities, and sentiment.
        
        Args:
            text: Input text to process
            
        Returns:
            NLPResult with extracted information
        """
        # Normalize text
        text_lower = text.lower().strip()
        
        # Detect language
        language = self._detect_language(text_lower)
        
        # Extract intent
        intent, confidence = await self._extract_intent(text_lower)
        
        # Extract entities
        entities = await self._extract_entities(text, text_lower)
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(text_lower)
        
        return NLPResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            sentiment=sentiment,
            language=language
        )
    
    async def _extract_intent(self, text: str) -> Tuple[Intent, float]:
        """Extract intent using semantic similarity."""
        # Encode input text
        text_embedding = self.model.encode([text])[0]
        
        best_intent = Intent.UNKNOWN
        best_score = 0.0
        
        # Compare with each intent's examples
        for intent, embeddings in self.intent_embeddings.items():
            # Calculate cosine similarity
            similarities = np.dot(embeddings, text_embedding) / (
                np.linalg.norm(embeddings, axis=1) * np.linalg.norm(text_embedding)
            )
            max_similarity = float(np.max(similarities))
            
            if max_similarity > best_score:
                best_score = max_similarity
                best_intent = intent
        
        # Threshold for unknown intent
        if best_score < 0.5:
            best_intent = Intent.UNKNOWN
        
        return best_intent, best_score
    
    async def _extract_entities(self, original_text: str, normalized_text: str) -> List[Entity]:
        """Extract entities from text."""
        entities = []
        
        # Extract dates
        dates = self._extract_dates(normalized_text)
        for date_val, start, end in dates:
            entities.append(Entity(
                type="date",
                value=date_val.isoformat(),
                confidence=0.9,
                position=(start, end)
            ))
        
        # Extract numbers (for guests, nights, etc.)
        numbers = re.finditer(r'\b(\d+)\b', normalized_text)
        for match in numbers:
            num = int(match.group(1))
            start, end = match.span()
            
            # Check context to determine number type
            context = normalized_text[max(0, start-20):min(len(normalized_text), end+20)]
            
            if any(word in context for word in ['adulto', 'pessoa', 'pax', 'hóspede']):
                entity_type = "adults"
            elif any(word in context for word in ['criança', 'filho', 'kid']):
                entity_type = "children"
            elif any(word in context for word in ['noite', 'diária', 'night']):
                entity_type = "nights"
            else:
                entity_type = "number"
            
            entities.append(Entity(
                type=entity_type,
                value=str(num),
                confidence=0.8,
                position=(start, end)
            ))
        
        # Extract room types
        room_patterns = [
            (r'\b(térreo|terreo)\b', "TERREO"),
            (r'\b(superior)\b', "SUPERIOR"),
            (r'\b(suíte|suite)\b', "SUITE")
        ]
        
        for pattern, room_type in room_patterns:
            matches = re.finditer(pattern, normalized_text, re.IGNORECASE)
            for match in matches:
                entities.append(Entity(
                    type="room_type",
                    value=room_type,
                    confidence=0.9,
                    position=match.span()
                ))
        
        # Extract meal plans
        meal_patterns = [
            (r'\b(café da manhã|apenas café|only breakfast)\b', "CAFE_DA_MANHA"),
            (r'\b(meia pensão|half board)\b', "MEIA_PENSAO"),
            (r'\b(pensão completa|full board|all inclusive)\b', "PENSAO_COMPLETA")
        ]
        
        for pattern, meal_plan in meal_patterns:
            matches = re.finditer(pattern, normalized_text, re.IGNORECASE)
            for match in matches:
                entities.append(Entity(
                    type="meal_plan",
                    value=meal_plan,
                    confidence=0.9,
                    position=match.span()
                ))
        
        return entities
    
    def _extract_dates(self, text: str) -> List[Tuple[date, int, int]]:
        """Extract dates from text."""
        dates = []
        
        for pattern, handler, *args in self.date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if args:
                        date_val = handler(*args)
                    elif match.groups():
                        date_val = handler(match)
                    else:
                        date_val = handler()
                    
                    if date_val:
                        dates.append((date_val, match.start(), match.end()))
                except Exception as e:
                    logger.debug(f"Failed to parse date: {match.group()}", error=str(e))
        
        return dates
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of text."""
        positive_words = [
            'ótimo', 'excelente', 'maravilhoso', 'perfeito', 'adorei',
            'fantástico', 'incrível', 'bom', 'legal', 'obrigado'
        ]
        
        negative_words = [
            'péssimo', 'ruim', 'terrível', 'horrível', 'problema',
            'reclamar', 'insatisfeito', 'decepcionado', 'não gostei'
        ]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if negative_count > positive_count:
            return "negative"
        elif positive_count > negative_count:
            return "positive"
        else:
            return "neutral"
    
    def _detect_language(self, text: str) -> str:
        """Detect language of text."""
        # Simple language detection based on common words
        pt_words = ['de', 'para', 'com', 'em', 'por', 'que', 'não']
        en_words = ['the', 'is', 'at', 'for', 'with', 'and', 'not']
        es_words = ['el', 'la', 'para', 'con', 'por', 'que', 'no']
        
        words = text.split()
        pt_count = sum(1 for word in words if word in pt_words)
        en_count = sum(1 for word in words if word in en_words)
        es_count = sum(1 for word in words if word in es_words)
        
        if en_count > pt_count and en_count > es_count:
            return "en"
        elif es_count > pt_count:
            return "es"
        else:
            return "pt"  # Default to Portuguese
    
    # Date parsing helper methods
    def _next_weekday(self, weekday: int) -> date:
        """Get next occurrence of weekday (0=Monday, 6=Sunday)."""
        today = date.today()
        days_ahead = weekday - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _this_weekend(self) -> date:
        """Get this weekend's Saturday."""
        today = date.today()
        saturday = 5  # Saturday
        days_ahead = saturday - today.weekday()
        if days_ahead < 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _next_weekend(self) -> date:
        """Get next weekend's Saturday."""
        return self._this_weekend() + timedelta(days=7)
    
    def _next_week(self) -> date:
        """Get next Monday."""
        return self._next_weekday(0)
    
    def _parse_date_numbers(self, match) -> Optional[date]:
        """Parse date from DD/MM/YYYY format."""
        day, month, year = match.groups()
        if not year:
            year = date.today().year
        elif len(year) == 2:
            year = 2000 + int(year)
        else:
            year = int(year)
        
        try:
            return date(year, int(month), int(day))
        except ValueError:
            return None
    
    def _parse_date_text(self, match) -> Optional[date]:
        """Parse date from 'DD de MONTH de YYYY' format."""
        day, month_name, year = match.groups()
        
        month = self.months.get(month_name.lower())
        if not month:
            return None
        
        if not year:
            year = date.today().year
        else:
            year = int(year)
        
        try:
            return date(year, month, int(day))
        except ValueError:
            return None
    
    def _easter_date(self) -> date:
        """Calculate Easter date for current year."""
        year = date.today().year
        # Simplified - would need proper calculation
        # For 2025: April 20
        if year == 2025:
            return date(2025, 4, 20)
        # Add more years or use proper algorithm
        return date(year, 4, 15)  # Approximate
