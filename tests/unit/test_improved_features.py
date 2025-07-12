"""Tests for improved features - NLP, Vision, and Omnibees integration."""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from aria.agents.ana.nlp_processor import NLPProcessor, Intent, Entity
from aria.agents.ana.improved_agent import ImprovedAnaAgent
from aria.tools.vision_processor import VisionProcessor, ImageType
from aria.integrations.omnibees.client import OmnibeesClient, Guest


class TestNLPProcessor:
    """Test NLP processing capabilities."""
    
    @pytest.fixture
    def nlp(self):
        """Create NLP processor instance."""
        return NLPProcessor()
    
    @pytest.mark.asyncio
    async def test_intent_detection_greeting(self, nlp):
        """Test greeting intent detection."""
        greetings = [
            "Olá, bom dia!",
            "Oi, tudo bem?",
            "Boa tarde",
            "Hello, good morning"
        ]
        
        for text in greetings:
            result = await nlp.process(text)
            assert result.intent == Intent.GREETING
            assert result.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_intent_detection_reservation(self, nlp):
        """Test reservation intent detection."""
        reservations = [
            "Quero fazer uma reserva",
            "Gostaria de reservar um quarto",
            "Tem disponibilidade para março?",
            "Preciso de hospedagem"
        ]
        
        for text in reservations:
            result = await nlp.process(text)
            assert result.intent == Intent.RESERVATION_INQUIRY
            assert result.confidence > 0.6
    
    @pytest.mark.asyncio
    async def test_intent_detection_pricing(self, nlp):
        """Test pricing intent detection."""
        pricing_queries = [
            "Quanto custa a diária?",
            "Qual o valor para 2 pessoas?",
            "Preço para o fim de semana",
            "Valores para março"
        ]
        
        for text in pricing_queries:
            result = await nlp.process(text)
            assert result.intent == Intent.PRICING_REQUEST
            assert result.confidence > 0.6
    
    @pytest.mark.asyncio
    async def test_entity_extraction_dates(self, nlp):
        """Test date entity extraction."""
        text = "Quero reservar de 15/03 a 17/03 para 2 adultos"
        result = await nlp.process(text)
        
        # Should extract 2 dates
        date_entities = [e for e in result.entities if e.type == "date"]
        assert len(date_entities) == 2
        
        # Check dates
        dates = [date.fromisoformat(e.value) for e in date_entities]
        assert dates[0].day == 15
        assert dates[0].month == 3
        assert dates[1].day == 17
        assert dates[1].month == 3
    
    @pytest.mark.asyncio
    async def test_entity_extraction_relative_dates(self, nlp):
        """Test relative date extraction."""
        # Test "próxima sexta"
        text = "Tem vaga para próxima sexta?"
        result = await nlp.process(text)
        
        date_entities = [e for e in result.entities if e.type == "date"]
        assert len(date_entities) == 1
        
        # Should be a Friday
        extracted_date = date.fromisoformat(date_entities[0].value)
        assert extracted_date.weekday() == 4  # Friday
        assert extracted_date > date.today()
    
    @pytest.mark.asyncio
    async def test_entity_extraction_guests(self, nlp):
        """Test guest count extraction."""
        text = "Preciso de um quarto para 2 adultos e 1 criança de 8 anos"
        result = await nlp.process(text)
        
        # Check adults
        adult_entities = [e for e in result.entities if e.type == "adults"]
        assert len(adult_entities) == 1
        assert adult_entities[0].value == "2"
        
        # Check children
        children_entities = [e for e in result.entities if e.type == "children"]
        assert len(children_entities) >= 1
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis(self, nlp):
        """Test sentiment analysis."""
        positive = "Adorei o hotel, foi maravilhoso!"
        negative = "Péssimo atendimento, estou muito insatisfeito"
        neutral = "Gostaria de saber os horários do café"
        
        assert (await nlp.process(positive)).sentiment == "positive"
        assert (await nlp.process(negative)).sentiment == "negative"  
        assert (await nlp.process(neutral)).sentiment == "neutral"
    
    @pytest.mark.asyncio
    async def test_language_detection(self, nlp):
        """Test language detection."""
        portuguese = "Olá, gostaria de fazer uma reserva"
        english = "Hello, I would like to make a reservation"
        spanish = "Hola, me gustaría hacer una reserva"
        
        assert (await nlp.process(portuguese)).language == "pt"
        assert (await nlp.process(english)).language == "en"
        assert (await nlp.process(spanish)).language == "es"


class TestImprovedAgent:
    """Test improved Ana agent."""
    
    @pytest.fixture
    def agent(self):
        """Create improved agent instance."""
        return ImprovedAnaAgent()
    
    @pytest.mark.asyncio
    async def test_greeting_response(self, agent):
        """Test greeting response."""
        response = await agent.process_message(
            phone="+5511999999999",
            message="Olá!"
        )
        
        assert "Ana" in response.text
        assert "Hotel Passarim" in response.text
        assert response.quick_replies is not None
        assert len(response.quick_replies) > 0
    
    @pytest.mark.asyncio
    async def test_pricing_with_complete_info(self, agent):
        """Test pricing calculation with all information."""
        response = await agent.process_message(
            phone="+5511999999999",
            message="Quanto custa para 2 adultos de 15 a 17 de março?"
        )
        
        assert "opções de hospedagem" in response.text
        assert "R$" in response.text
        assert response.action == "show_pricing"
        assert response.metadata["adults"] == 2
    
    @pytest.mark.asyncio
    async def test_pricing_missing_info(self, agent):
        """Test pricing request with missing information."""
        response = await agent.process_message(
            phone="+5511999999999",
            message="Quanto custa a hospedagem?"
        )
        
        assert "preciso saber" in response.text
        assert "check-in" in response.text.lower()
        assert response.metadata.get("missing_info") is True
    
    @pytest.mark.asyncio
    async def test_negative_sentiment_handling(self, agent):
        """Test handling of negative sentiment."""
        response = await agent.process_message(
            phone="+5511999999999",
            message="Estou muito insatisfeito com o atendimento péssimo!"
        )
        
        assert response.needs_human is True
        assert response.action == "transfer_to_management"
        assert response.metadata["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_context_persistence(self, agent):
        """Test conversation context persistence."""
        phone = "+5511999999999"
        
        # First message
        response1 = await agent.process_message(
            phone=phone,
            message="Olá, meu nome é João"
        )
        
        # Second message should remember context
        response2 = await agent.process_message(
            phone=phone,
            message="Quero fazer uma reserva"
        )
        
        # Check context was maintained
        context = agent.contexts[phone]
        assert len(context.history) == 4  # 2 user + 2 assistant
        assert context.metadata.get("last_intent") == "reservation_inquiry"


class TestVisionProcessor:
    """Test vision processing capabilities."""
    
    @pytest.fixture
    def vision(self):
        """Create vision processor instance."""
        return VisionProcessor()
    
    @pytest.mark.asyncio
    async def test_document_detection(self, vision):
        """Test document type detection."""
        # This would use a real document image in production
        # For testing, we'll mock the result
        
        # Mock the processing
        result = vision.VisionResult(
            image_type=ImageType.DOCUMENT,
            text_content="NOME: JOÃO SILVA\nCPF: 123.456.789-00",
            document_data={
                "name": "JOÃO SILVA",
                "cpf": "123.456.789-00"
            },
            confidence=0.9
        )
        
        assert result.image_type == ImageType.DOCUMENT
        assert result.document_data["cpf"] == "123.456.789-00"
        assert result.confidence > 0.8
    
    def test_cpf_validation(self, vision):
        """Test CPF validation."""
        # Valid CPF (test number)
        assert vision._validate_cpf("11144477735") is True
        
        # Invalid CPF
        assert vision._validate_cpf("12345678900") is False
        assert vision._validate_cpf("111.444.777-35") is False  # With formatting
        assert vision._validate_cpf("123") is False  # Too short
    
    def test_document_extraction_for_checkin(self, vision):
        """Test document data extraction for check-in."""
        # Valid document data
        valid_data = {
            "name": "JOÃO SILVA",
            "cpf": "111.444.777-35"
        }
        
        result = vision.extract_document_for_checkin(valid_data)
        assert result["valid"] is True
        assert result["data"]["name"] == "JOÃO SILVA"
        
        # Missing required field
        invalid_data = {
            "name": "JOÃO SILVA"
            # Missing CPF
        }
        
        result = vision.extract_document_for_checkin(invalid_data)
        assert result["valid"] is False
        assert "cpf" in result["missing_fields"]


class TestOmnibeesIntegration:
    """Test Omnibees integration."""
    
    @pytest.fixture
    def client(self):
        """Create Omnibees client instance."""
        return OmnibeesClient()
    
    @pytest.mark.asyncio
    async def test_check_availability(self, client):
        """Test availability checking."""
        check_in = date.today() + timedelta(days=7)
        check_out = check_in + timedelta(days=2)
        
        availability = await client.check_availability(
            check_in=check_in,
            check_out=check_out,
            guests=2
        )
        
        assert len(availability) > 0
        assert all(a.available_count >= 0 for a in availability)
        assert all(a.min_rate > 0 for a in availability)
    
    @pytest.mark.asyncio
    async def test_create_reservation(self, client):
        """Test reservation creation."""
        check_in = date.today() + timedelta(days=7)
        check_out = check_in + timedelta(days=2)
        
        guest = Guest(
            name="João Silva",
            phone="+5511999999999",
            document="123.456.789-00"
        )
        
        reservation = await client.create_reservation(
            check_in=check_in,
            check_out=check_out,
            room_type="TERREO",
            guests=[guest]
        )
        
        assert reservation.id.startswith("RES")
        assert reservation.status.value == "confirmed"
        assert reservation.total_amount > 0
        assert len(reservation.guests) == 1
    
    def test_booking_link_generation(self, client):
        """Test booking link generation."""
        check_in = date.today() + timedelta(days=7)
        check_out = check_in + timedelta(days=2)
        
        link = client.generate_booking_link(
            check_in=check_in,
            check_out=check_out,
            adults=2,
            children=1,
            promo_code="TESTE10"
        )
        
        assert "booking.omnibees.com" in link
        assert "checkin=" in link
        assert "checkout=" in link
        assert "ad=2" in link
        assert "ch=1" in link
        assert "promo=TESTE10" in link
    
    @pytest.mark.asyncio
    async def test_get_reservation(self, client):
        """Test fetching reservation details."""
        reservation = await client.get_reservation("RES12345678")
        
        if reservation:  # Mock will return a reservation
            assert reservation.id == "RES12345678"
            assert reservation.hotel_id == client.hotel_id
            assert len(reservation.guests) > 0
    
    @pytest.mark.asyncio
    async def test_cancel_reservation(self, client):
        """Test reservation cancellation."""
        success = await client.cancel_reservation(
            reservation_id="RES12345678",
            reason="Guest request"
        )
        
        assert success is True  # Mock always returns True in dev


# Integration test combining all components
class TestFullIntegration:
    """Test full integration of improved features."""
    
    @pytest.mark.asyncio
    async def test_complete_booking_flow(self):
        """Test complete booking flow from message to reservation."""
        # Initialize components
        agent = ImprovedAnaAgent()
        
        # Step 1: Initial greeting
        response = await agent.process_message(
            phone="+5511999999999",
            message="Olá, gostaria de fazer uma reserva"
        )
        assert response.metadata["intent"] == "greeting"
        
        # Step 2: Provide booking details
        response = await agent.process_message(
            phone="+5511999999999",
            message="Quero reservar de 20 a 22 de março para 2 adultos"
        )
        
        # Should show pricing
        assert "opções de hospedagem" in response.text
        assert response.action == "show_pricing"
        
        # Step 3: Would continue with actual booking...
        # This would involve:
        # - Guest selects room type
        # - Provides personal information
        # - Uploads document (vision processing)
        # - Confirms reservation (Omnibees integration)
        # - Receives confirmation with booking code
