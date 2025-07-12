"""Payment gateway integration for multiple providers."""

import asyncio
import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass
from enum import Enum

import httpx
from cryptography.fernet import Fernet

from aria.core.logging import get_logger
from aria.core.config import settings
from aria.domain.shared.value_objects import Money

logger = get_logger(__name__)


class PaymentStatus(Enum):
    """Payment transaction status."""
    PENDING = "pending"
    PROCESSING = "processing"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    EXPIRED = "expired"


class PaymentMethod(Enum):
    """Supported payment methods."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PIX = "pix"
    BOLETO = "boleto"
    BANK_TRANSFER = "bank_transfer"


@dataclass
class PaymentRequest:
    """Payment request data."""
    amount: Money
    method: PaymentMethod
    customer_id: str
    order_id: str
    description: str
    metadata: Optional[Dict] = None
    return_url: Optional[str] = None
    webhook_url: Optional[str] = None
    
    # Card details (if applicable)
    card_number: Optional[str] = None
    card_holder: Optional[str] = None
    card_expiry: Optional[str] = None
    card_cvv: Optional[str] = None
    card_token: Optional[str] = None
    
    # PIX details
    pix_key: Optional[str] = None
    pix_expiration: Optional[int] = 3600  # seconds
    
    # Customer details
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_document: Optional[str] = None


@dataclass
class PaymentResponse:
    """Payment response data."""
    transaction_id: str
    status: PaymentStatus
    amount: Money
    method: PaymentMethod
    provider: str
    created_at: datetime
    
    # Additional data based on method
    authorization_code: Optional[str] = None
    qr_code: Optional[str] = None
    qr_code_url: Optional[str] = None
    pix_key: Optional[str] = None
    boleto_url: Optional[str] = None
    boleto_barcode: Optional[str] = None
    
    # Error info
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # Raw response for debugging
    raw_response: Optional[Dict] = None


class PaymentProvider(ABC):
    """Abstract base class for payment providers."""
    
    @abstractmethod
    async def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process a payment request."""
        pass
    
    @abstractmethod
    async def get_payment_status(self, transaction_id: str) -> PaymentResponse:
        """Get payment status by transaction ID."""
        pass
    
    @abstractmethod
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Money] = None,
        reason: Optional[str] = None
    ) -> PaymentResponse:
        """Refund a payment (full or partial)."""
        pass
    
    @abstractmethod
    async def cancel_payment(self, transaction_id: str) -> PaymentResponse:
        """Cancel a pending payment."""
        pass


class StripeProvider(PaymentProvider):
    """Stripe payment provider implementation."""
    
    def __init__(self):
        self.api_key = settings.get("STRIPE_API_KEY")
        self.webhook_secret = settings.get("STRIPE_WEBHOOK_SECRET")
        self.base_url = "https://api.stripe.com/v1"
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
    
    async def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process payment through Stripe."""
        try:
            # Create payment intent
            data = {
                "amount": int(request.amount.amount * 100),  # Convert to cents
                "currency": request.amount.currency.lower(),
                "description": request.description,
                "metadata[order_id]": request.order_id,
                "metadata[customer_id]": request.customer_id
            }
            
            # Add payment method
            if request.card_token:
                data["payment_method"] = request.card_token
                data["confirm"] = "true"
            elif request.method == PaymentMethod.PIX:
                # Stripe doesn't support PIX directly
                # Would need to use a local provider
                pass
            
            response = await self.client.post("/payment_intents", data=data)
            response.raise_for_status()
            
            result = response.json()
            
            return PaymentResponse(
                transaction_id=result["id"],
                status=self._map_stripe_status(result["status"]),
                amount=request.amount,
                method=request.method,
                provider="stripe",
                created_at=datetime.fromtimestamp(result["created"]),
                authorization_code=result.get("charges", {}).get("data", [{}])[0].get("id"),
                raw_response=result
            )
            
        except Exception as e:
            logger.error("Stripe payment failed", error=str(e))
            return PaymentResponse(
                transaction_id=str(uuid4()),
                status=PaymentStatus.FAILED,
                amount=request.amount,
                method=request.method,
                provider="stripe",
                created_at=datetime.now(),
                error_message=str(e)
            )
    
    async def get_payment_status(self, transaction_id: str) -> PaymentResponse:
        """Get payment status from Stripe."""
        try:
            response = await self.client.get(f"/payment_intents/{transaction_id}")
            response.raise_for_status()
            
            result = response.json()
            
            return PaymentResponse(
                transaction_id=result["id"],
                status=self._map_stripe_status(result["status"]),
                amount=Money(Decimal(result["amount"]) / 100, result["currency"].upper()),
                method=PaymentMethod.CREDIT_CARD,  # Default
                provider="stripe",
                created_at=datetime.fromtimestamp(result["created"]),
                raw_response=result
            )
            
        except Exception as e:
            logger.error("Failed to get Stripe payment status", error=str(e))
            raise
    
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Money] = None,
        reason: Optional[str] = None
    ) -> PaymentResponse:
        """Refund a Stripe payment."""
        try:
            data = {"payment_intent": transaction_id}
            
            if amount:
                data["amount"] = int(amount.amount * 100)
            
            if reason:
                data["reason"] = reason
            
            response = await self.client.post("/refunds", data=data)
            response.raise_for_status()
            
            result = response.json()
            
            return PaymentResponse(
                transaction_id=result["id"],
                status=PaymentStatus.REFUNDED,
                amount=Money(Decimal(result["amount"]) / 100, result["currency"].upper()),
                method=PaymentMethod.CREDIT_CARD,
                provider="stripe",
                created_at=datetime.fromtimestamp(result["created"]),
                raw_response=result
            )
            
        except Exception as e:
            logger.error("Stripe refund failed", error=str(e))
            raise
    
    async def cancel_payment(self, transaction_id: str) -> PaymentResponse:
        """Cancel a Stripe payment."""
        try:
            response = await self.client.post(
                f"/payment_intents/{transaction_id}/cancel"
            )
            response.raise_for_status()
            
            result = response.json()
            
            return PaymentResponse(
                transaction_id=result["id"],
                status=PaymentStatus.CANCELLED,
                amount=Money(Decimal(result["amount"]) / 100, result["currency"].upper()),
                method=PaymentMethod.CREDIT_CARD,
                provider="stripe",
                created_at=datetime.now(),
                raw_response=result
            )
            
        except Exception as e:
            logger.error("Stripe cancellation failed", error=str(e))
            raise
    
    def _map_stripe_status(self, stripe_status: str) -> PaymentStatus:
        """Map Stripe status to our status."""
        mapping = {
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PENDING,
            "requires_action": PaymentStatus.PENDING,
            "processing": PaymentStatus.PROCESSING,
            "requires_capture": PaymentStatus.AUTHORIZED,
            "succeeded": PaymentStatus.CAPTURED,
            "canceled": PaymentStatus.CANCELLED,
            "failed": PaymentStatus.FAILED
        }
        return mapping.get(stripe_status, PaymentStatus.PENDING)


class MercadoPagoProvider(PaymentProvider):
    """MercadoPago payment provider (popular in Brazil)."""
    
    def __init__(self):
        self.access_token = settings.get("MERCADOPAGO_ACCESS_TOKEN")
        self.public_key = settings.get("MERCADOPAGO_PUBLIC_KEY")
        self.base_url = "https://api.mercadopago.com"
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        )
    
    async def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process payment through MercadoPago."""
        try:
            if request.method == PaymentMethod.PIX:
                return await self._process_pix_payment(request)
            elif request.method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
                return await self._process_card_payment(request)
            else:
                raise ValueError(f"Unsupported payment method: {request.method}")
            
        except Exception as e:
            logger.error("MercadoPago payment failed", error=str(e))
            return PaymentResponse(
                transaction_id=str(uuid4()),
                status=PaymentStatus.FAILED,
                amount=request.amount,
                method=request.method,
                provider="mercadopago",
                created_at=datetime.now(),
                error_message=str(e)
            )
    
    async def _process_pix_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process PIX payment through MercadoPago."""
        data = {
            "transaction_amount": float(request.amount.amount),
            "description": request.description,
            "payment_method_id": "pix",
            "payer": {
                "email": request.customer_email or "guest@hotelpassarim.com.br"
            },
            "metadata": {
                "order_id": request.order_id,
                "customer_id": request.customer_id
            },
            "date_of_expiration": (
                datetime.now() + timedelta(seconds=request.pix_expiration)
            ).isoformat()
        }
        
        response = await self.client.post("/v1/payments", json=data)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract PIX data
        qr_code = result.get("point_of_interaction", {}).get("transaction_data", {})
        
        return PaymentResponse(
            transaction_id=str(result["id"]),
            status=self._map_mp_status(result["status"]),
            amount=request.amount,
            method=PaymentMethod.PIX,
            provider="mercadopago",
            created_at=datetime.fromisoformat(result["date_created"]),
            qr_code=qr_code.get("qr_code"),
            qr_code_url=qr_code.get("qr_code_base64", "").replace("data:image/png;base64,", ""),
            pix_key=qr_code.get("qr_code"),
            raw_response=result
        )
    
    async def _process_card_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process card payment through MercadoPago."""
        data = {
            "transaction_amount": float(request.amount.amount),
            "token": request.card_token,  # Must be generated client-side
            "description": request.description,
            "installments": 1,
            "payment_method_id": "visa",  # Would be dynamic
            "payer": {
                "email": request.customer_email
            },
            "metadata": {
                "order_id": request.order_id,
                "customer_id": request.customer_id
            }
        }
        
        response = await self.client.post("/v1/payments", json=data)
        response.raise_for_status()
        
        result = response.json()
        
        return PaymentResponse(
            transaction_id=str(result["id"]),
            status=self._map_mp_status(result["status"]),
            amount=request.amount,
            method=request.method,
            provider="mercadopago",
            created_at=datetime.fromisoformat(result["date_created"]),
            authorization_code=result.get("authorization_code"),
            raw_response=result
        )
    
    async def get_payment_status(self, transaction_id: str) -> PaymentResponse:
        """Get payment status from MercadoPago."""
        try:
            response = await self.client.get(f"/v1/payments/{transaction_id}")
            response.raise_for_status()
            
            result = response.json()
            
            return PaymentResponse(
                transaction_id=str(result["id"]),
                status=self._map_mp_status(result["status"]),
                amount=Money(Decimal(str(result["transaction_amount"])), "BRL"),
                method=self._map_mp_payment_method(result["payment_method_id"]),
                provider="mercadopago",
                created_at=datetime.fromisoformat(result["date_created"]),
                raw_response=result
            )
            
        except Exception as e:
            logger.error("Failed to get MercadoPago payment status", error=str(e))
            raise
    
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Money] = None,
        reason: Optional[str] = None
    ) -> PaymentResponse:
        """Refund a MercadoPago payment."""
        try:
            data = {}
            if amount:
                data["amount"] = float(amount.amount)
            
            response = await self.client.post(
                f"/v1/payments/{transaction_id}/refunds",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            
            return PaymentResponse(
                transaction_id=str(result["id"]),
                status=PaymentStatus.REFUNDED,
                amount=Money(Decimal(str(result["amount"])), "BRL"),
                method=PaymentMethod.PIX,  # Default
                provider="mercadopago",
                created_at=datetime.fromisoformat(result["date_created"]),
                raw_response=result
            )
            
        except Exception as e:
            logger.error("MercadoPago refund failed", error=str(e))
            raise
    
    async def cancel_payment(self, transaction_id: str) -> PaymentResponse:
        """Cancel a MercadoPago payment."""
        try:
            response = await self.client.put(
                f"/v1/payments/{transaction_id}",
                json={"status": "cancelled"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            return PaymentResponse(
                transaction_id=str(result["id"]),
                status=PaymentStatus.CANCELLED,
                amount=Money(Decimal(str(result["transaction_amount"])), "BRL"),
                method=self._map_mp_payment_method(result["payment_method_id"]),
                provider="mercadopago",
                created_at=datetime.now(),
                raw_response=result
            )
            
        except Exception as e:
            logger.error("MercadoPago cancellation failed", error=str(e))
            raise
    
    def _map_mp_status(self, mp_status: str) -> PaymentStatus:
        """Map MercadoPago status to our status."""
        mapping = {
            "pending": PaymentStatus.PENDING,
            "approved": PaymentStatus.CAPTURED,
            "authorized": PaymentStatus.AUTHORIZED,
            "in_process": PaymentStatus.PROCESSING,
            "in_mediation": PaymentStatus.PROCESSING,
            "rejected": PaymentStatus.FAILED,
            "cancelled": PaymentStatus.CANCELLED,
            "refunded": PaymentStatus.REFUNDED,
            "charged_back": PaymentStatus.REFUNDED
        }
        return mapping.get(mp_status, PaymentStatus.PENDING)
    
    def _map_mp_payment_method(self, method_id: str) -> PaymentMethod:
        """Map MercadoPago payment method to our enum."""
        if method_id == "pix":
            return PaymentMethod.PIX
        elif method_id in ["visa", "mastercard", "amex", "elo"]:
            return PaymentMethod.CREDIT_CARD
        elif method_id == "debit_card":
            return PaymentMethod.DEBIT_CARD
        else:
            return PaymentMethod.CREDIT_CARD  # Default


class PaymentGateway:
    """Main payment gateway that routes to appropriate provider."""
    
    def __init__(self):
        """Initialize payment gateway with providers."""
        self.providers: Dict[str, PaymentProvider] = {
            "stripe": StripeProvider(),
            "mercadopago": MercadoPagoProvider()
        }
        
        # Encryption for sensitive data
        self.cipher_suite = Fernet(settings.get("PAYMENT_ENCRYPTION_KEY", Fernet.generate_key()))
        
        # Transaction storage (would be database in production)
        self.transactions: Dict[str, PaymentResponse] = {}
    
    async def process_payment(
        self,
        request: PaymentRequest,
        provider: Optional[str] = None
    ) -> PaymentResponse:
        """
        Process a payment through the appropriate provider.
        
        Args:
            request: Payment request details
            provider: Specific provider to use (optional)
            
        Returns:
            Payment response with transaction details
        """
        # Validate request
        self._validate_payment_request(request)
        
        # Encrypt sensitive data
        if request.card_number:
            request.card_number = self._encrypt_data(request.card_number)
        if request.card_cvv:
            request.card_cvv = self._encrypt_data(request.card_cvv)
        
        # Select provider
        if not provider:
            provider = self._select_provider(request)
        
        if provider not in self.providers:
            raise ValueError(f"Unknown payment provider: {provider}")
        
        # Process payment
        logger.info(
            "Processing payment",
            provider=provider,
            method=request.method.value,
            amount=float(request.amount.amount),
            order_id=request.order_id
        )
        
        try:
            response = await self.providers[provider].process_payment(request)
            
            # Store transaction
            self.transactions[response.transaction_id] = response
            
            # Log result
            logger.info(
                "Payment processed",
                transaction_id=response.transaction_id,
                status=response.status.value,
                provider=provider
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Payment processing failed",
                provider=provider,
                error=str(e)
            )
            raise
    
    async def get_payment_status(
        self,
        transaction_id: str,
        provider: Optional[str] = None
    ) -> PaymentResponse:
        """Get payment status by transaction ID."""
        # Check cache first
        if transaction_id in self.transactions:
            cached = self.transactions[transaction_id]
            provider = cached.provider
        
        if not provider:
            # Try to determine provider from transaction ID format
            provider = self._detect_provider_from_id(transaction_id)
        
        if not provider:
            raise ValueError("Cannot determine payment provider")
        
        response = await self.providers[provider].get_payment_status(transaction_id)
        
        # Update cache
        self.transactions[transaction_id] = response
        
        return response
    
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Money] = None,
        reason: Optional[str] = None
    ) -> PaymentResponse:
        """Refund a payment."""
        # Get original transaction
        original = await self.get_payment_status(transaction_id)
        
        if original.status not in [PaymentStatus.CAPTURED, PaymentStatus.PARTIALLY_REFUNDED]:
            raise ValueError(f"Cannot refund payment in status {original.status}")
        
        provider = self.providers[original.provider]
        response = await provider.refund_payment(transaction_id, amount, reason)
        
        # Update cache
        self.transactions[transaction_id] = response
        
        logger.info(
            "Payment refunded",
            transaction_id=transaction_id,
            amount=float(amount.amount) if amount else "full",
            reason=reason
        )
        
        return response
    
    async def create_pix_payment(
        self,
        amount: Money,
        customer_id: str,
        order_id: str,
        description: str,
        expiration_minutes: int = 60
    ) -> PaymentResponse:
        """Create a PIX payment with QR code."""
        request = PaymentRequest(
            amount=amount,
            method=PaymentMethod.PIX,
            customer_id=customer_id,
            order_id=order_id,
            description=description,
            pix_expiration=expiration_minutes * 60
        )
        
        # PIX is only supported by MercadoPago in our implementation
        return await self.process_payment(request, provider="mercadopago")
    
    def verify_webhook(self, provider: str, headers: Dict, body: bytes) -> bool:
        """Verify webhook signature from provider."""
        if provider == "stripe":
            return self._verify_stripe_webhook(headers, body)
        elif provider == "mercadopago":
            return self._verify_mercadopago_webhook(headers, body)
        else:
            logger.warning(f"Unknown provider for webhook verification: {provider}")
            return False
    
    def _validate_payment_request(self, request: PaymentRequest):
        """Validate payment request data."""
        if request.amount.amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        if request.method == PaymentMethod.CREDIT_CARD:
            if not request.card_token and not request.card_number:
                raise ValueError("Card token or card details required")
        
        if request.method == PaymentMethod.PIX:
            if request.amount.currency != "BRL":
                raise ValueError("PIX only supports BRL currency")
    
    def _select_provider(self, request: PaymentRequest) -> str:
        """Select appropriate provider based on payment method and region."""
        if request.method == PaymentMethod.PIX:
            return "mercadopago"
        elif request.amount.currency == "BRL":
            return "mercadopago"
        else:
            return "stripe"
    
    def _detect_provider_from_id(self, transaction_id: str) -> Optional[str]:
        """Try to detect provider from transaction ID format."""
        if transaction_id.startswith("pi_") or transaction_id.startswith("ch_"):
            return "stripe"
        elif transaction_id.isdigit():
            return "mercadopago"
        return None
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted: str) -> str:
        """Decrypt sensitive data."""
        return self.cipher_suite.decrypt(encrypted.encode()).decode()
    
    def _verify_stripe_webhook(self, headers: Dict, body: bytes) -> bool:
        """Verify Stripe webhook signature."""
        signature = headers.get("stripe-signature", "")
        secret = settings.get("STRIPE_WEBHOOK_SECRET", "")
        
        # Parse signature
        elements = {}
        for element in signature.split(","):
            key, value = element.split("=", 1)
            elements[key] = value
        
        # Verify timestamp
        timestamp = int(elements.get("t", "0"))
        if abs(datetime.now().timestamp() - timestamp) > 300:  # 5 minutes
            return False
        
        # Verify signature
        signed_payload = f"{timestamp}.{body.decode()}"
        expected_signature = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(elements.get("v1", ""), expected_signature)
    
    def _verify_mercadopago_webhook(self, headers: Dict, body: bytes) -> bool:
        """Verify MercadoPago webhook signature."""
        # MercadoPago uses x-signature header
        signature = headers.get("x-signature", "")
        secret = settings.get("MERCADOPAGO_WEBHOOK_SECRET", "")
        
        # Extract TS and hash
        parts = {}
        for part in signature.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key.strip()] = value.strip()
        
        # Verify
        ts = parts.get("ts", "")
        v1 = parts.get("v1", "")
        
        signed_template = f"id:{body.decode()};request-id:{headers.get('x-request-id', '')};ts:{ts};"
        
        expected = hmac.new(
            secret.encode(),
            signed_template.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(v1, expected)


# Singleton instance
_payment_gateway = None


def get_payment_gateway() -> PaymentGateway:
    """Get or create payment gateway instance."""
    global _payment_gateway
    
    if _payment_gateway is None:
        _payment_gateway = PaymentGateway()
    
    return _payment_gateway
