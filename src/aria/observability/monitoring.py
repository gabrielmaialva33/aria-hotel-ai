"""Monitoring and observability system with OpenTelemetry."""

import time
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from functools import wraps
import traceback

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from prometheus_client import Counter, Histogram, Gauge, Info
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from aria.core.logging import get_logger
from aria.core.config import settings

logger = get_logger(__name__)


# Metrics definitions
REQUEST_COUNT = Counter(
    'aria_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'aria_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'aria_http_requests_active',
    'Active HTTP requests'
)

AI_INFERENCE_DURATION = Histogram(
    'aria_ai_inference_duration_seconds',
    'AI model inference duration',
    ['model', 'operation']
)

AI_TOKEN_USAGE = Counter(
    'aria_ai_tokens_used_total',
    'Total AI tokens used',
    ['model', 'type']  # type: prompt, completion
)

MESSAGE_PROCESSED = Counter(
    'aria_messages_processed_total',
    'Total messages processed',
    ['channel', 'status']  # channel: whatsapp, web; status: success, error
)

PAYMENT_TRANSACTIONS = Counter(
    'aria_payment_transactions_total',
    'Total payment transactions',
    ['provider', 'method', 'status']
)

RESERVATION_OPERATIONS = Counter(
    'aria_reservation_operations_total',
    'Total reservation operations',
    ['operation', 'status']  # operation: create, modify, cancel
)

SYSTEM_INFO = Info(
    'aria_system',
    'System information'
)

# Custom exceptions
class MonitoringError(Exception):
    """Base monitoring error."""
    pass


class MetricsCollector:
    """Collects and exposes custom metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = time.time()
        
        # Update system info
        SYSTEM_INFO.info({
            'version': '2.0.0',
            'environment': settings.app_env,
            'python_version': '3.11'
        })
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_ai_inference(self, model: str, operation: str, duration: float, tokens: Dict[str, int]):
        """Record AI inference metrics."""
        AI_INFERENCE_DURATION.labels(
            model=model,
            operation=operation
        ).observe(duration)
        
        for token_type, count in tokens.items():
            AI_TOKEN_USAGE.labels(
                model=model,
                type=token_type
            ).inc(count)
    
    def record_message(self, channel: str, status: str):
        """Record message processing."""
        MESSAGE_PROCESSED.labels(
            channel=channel,
            status=status
        ).inc()
    
    def record_payment(self, provider: str, method: str, status: str):
        """Record payment transaction."""
        PAYMENT_TRANSACTIONS.labels(
            provider=provider,
            method=method,
            status=status
        ).inc()
    
    def record_reservation_operation(self, operation: str, status: str):
        """Record reservation operation."""
        RESERVATION_OPERATIONS.labels(
            operation=operation,
            status=status
        ).inc()
    
    @property
    def uptime(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self.start_time


class TracingService:
    """OpenTelemetry tracing service."""
    
    def __init__(self):
        """Initialize tracing service."""
        self.resource = Resource.create({
            "service.name": "aria-hotel-ai",
            "service.version": "2.0.0",
            "deployment.environment": settings.app_env
        })
        
        self.tracer_provider = None
        self.tracer = None
        self._initialized = False
    
    def initialize(self):
        """Initialize OpenTelemetry tracing."""
        if self._initialized:
            return
        
        try:
            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=self.resource)
            
            # Add OTLP exporter if configured
            if settings.get("OTLP_ENDPOINT"):
                otlp_exporter = OTLPSpanExporter(
                    endpoint=settings.get("OTLP_ENDPOINT"),
                    insecure=settings.app_env == "development"
                )
                
                span_processor = BatchSpanProcessor(otlp_exporter)
                self.tracer_provider.add_span_processor(span_processor)
            
            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
            # Instrument libraries
            FastAPIInstrumentor.instrument()
            HTTPXClientInstrumentor.instrument()
            RedisInstrumentor.instrument()
            SQLAlchemyInstrumentor.instrument()
            
            self._initialized = True
            logger.info("Tracing service initialized")
            
        except Exception as e:
            logger.error("Failed to initialize tracing", error=str(e))
    
    @asynccontextmanager
    async def trace_operation(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Context manager for tracing operations."""
        if not self.tracer:
            yield
            return
        
        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            else:
                span.set_status(Status(StatusCode.OK))
    
    def trace_async(self, name: str = None):
        """Decorator for tracing async functions."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                span_name = name or f"{func.__module__}.{func.__name__}"
                
                async with self.trace_operation(span_name):
                    return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def trace_sync(self, name: str = None):
        """Decorator for tracing sync functions."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.tracer:
                    return func(*args, **kwargs)
                
                span_name = name or f"{func.__module__}.{func.__name__}"
                
                with self.tracer.start_as_current_span(span_name) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            
            return wrapper
        return decorator


class ErrorTracker:
    """Error tracking with Sentry."""
    
    def __init__(self):
        """Initialize error tracker."""
        self._initialized = False
    
    def initialize(self):
        """Initialize Sentry error tracking."""
        if self._initialized or not settings.get("SENTRY_DSN"):
            return
        
        try:
            sentry_sdk.init(
                dsn=settings.get("SENTRY_DSN"),
                environment=settings.app_env,
                traces_sample_rate=0.1 if settings.is_production else 1.0,
                profiles_sample_rate=0.1 if settings.is_production else 1.0,
                integrations=[
                    FastApiIntegration(transaction_style="endpoint"),
                    SqlalchemyIntegration()
                ],
                before_send=self._before_send,
                attach_stacktrace=True,
                send_default_pii=False  # Don't send PII
            )
            
            self._initialized = True
            logger.info("Error tracking initialized")
            
        except Exception as e:
            logger.error("Failed to initialize error tracking", error=str(e))
    
    def _before_send(self, event: Dict, hint: Dict) -> Optional[Dict]:
        """Filter events before sending to Sentry."""
        # Don't send certain errors
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info']
            
            # Skip client errors
            if exc_type.__name__ in ['HTTPException'] and hasattr(exc_value, 'status_code'):
                if exc_value.status_code < 500:
                    return None
        
        # Remove sensitive data
        if 'request' in event:
            request = event['request']
            
            # Remove auth headers
            if 'headers' in request:
                request['headers'] = {
                    k: v for k, v in request['headers'].items()
                    if k.lower() not in ['authorization', 'x-api-key', 'cookie']
                }
            
            # Remove sensitive query params
            if 'query_string' in request:
                # Parse and filter query string
                pass
        
        return event
    
    def capture_exception(
        self,
        error: Exception,
        context: Optional[Dict] = None,
        user_info: Optional[Dict] = None
    ):
        """Capture exception with context."""
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            
            if user_info:
                scope.set_user(user_info)
            
            sentry_sdk.capture_exception(error)
    
    def capture_message(
        self,
        message: str,
        level: str = "info",
        context: Optional[Dict] = None
    ):
        """Capture message with context."""
        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_context(key, value)
            
            sentry_sdk.capture_message(message, level=level)


class HealthChecker:
    """System health checker."""
    
    def __init__(self):
        """Initialize health checker."""
        self.checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, Dict] = {}
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check."""
        self.checks[name] = check_func
    
    async def check_health(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        all_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(check_func):
                    is_healthy = await check_func()
                else:
                    is_healthy = check_func()
                
                duration = time.time() - start_time
                
                results["checks"][name] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "duration_ms": round(duration * 1000, 2)
                }
                
                if not is_healthy:
                    all_healthy = False
                
            except Exception as e:
                results["checks"][name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                all_healthy = False
        
        results["status"] = "healthy" if all_healthy else "unhealthy"
        self.last_check_results = results
        
        return results
    
    async def check_database(self) -> bool:
        """Check database health."""
        try:
            from aria.core.database.session import get_db
            
            async with get_db() as db:
                result = await db.execute("SELECT 1")
                return result.scalar() == 1
        except Exception:
            return False
    
    async def check_redis(self) -> bool:
        """Check Redis health."""
        try:
            import redis.asyncio as redis
            
            client = await redis.from_url(settings.redis_url)
            await client.ping()
            await client.close()
            return True
        except Exception:
            return False
    
    async def check_ai_service(self) -> bool:
        """Check AI service health."""
        try:
            # Simple check - verify API key exists
            return bool(settings.openai_api_key or settings.groq_api_key)
        except Exception:
            return False


# Global instances
metrics_collector = MetricsCollector()
tracing_service = TracingService()
error_tracker = ErrorTracker()
health_checker = HealthChecker()


def initialize_observability():
    """Initialize all observability components."""
    logger.info("Initializing observability")
    
    # Initialize components
    tracing_service.initialize()
    error_tracker.initialize()
    
    # Register health checks
    health_checker.register_check("database", health_checker.check_database)
    health_checker.register_check("redis", health_checker.check_redis)
    health_checker.register_check("ai_service", health_checker.check_ai_service)
    
    logger.info("Observability initialized")


# Middleware for FastAPI
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse


async def observability_middleware(request: Request, call_next):
    """Middleware to track requests and errors."""
    # Track active requests
    ACTIVE_REQUESTS.inc()
    
    # Start timer
    start_time = time.time()
    
    # Get or create trace span
    span = trace.get_current_span()
    if span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.scheme", request.url.scheme)
        span.set_attribute("http.host", request.url.hostname)
        span.set_attribute("http.target", request.url.path)
    
    try:
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        metrics_collector.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration
        )
        
        # Update span
        if span:
            span.set_attribute("http.status_code", response.status_code)
        
        return response
        
    except Exception as e:
        # Record error
        duration = time.time() - start_time
        metrics_collector.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=500,
            duration=duration
        )
        
        # Capture exception
        error_tracker.capture_exception(
            e,
            context={
                "request": {
                    "method": request.method,
                    "url": str(request.url),
                    "headers": dict(request.headers)
                }
            }
        )
        
        # Update span
        if span:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.set_attribute("http.status_code", 500)
        
        # Return error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(e) if settings.app_debug else "An error occurred"
            }
        )
        
    finally:
        # Decrement active requests
        ACTIVE_REQUESTS.dec()


def setup_monitoring(app: FastAPI):
    """Setup monitoring for FastAPI app."""
    # Initialize observability
    initialize_observability()
    
    # Add middleware
    app.middleware("http")(observability_middleware)
    
    # Add health endpoint
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        results = await health_checker.check_health()
        status_code = 200 if results["status"] == "healthy" else 503
        return JSONResponse(content=results, status_code=status_code)
    
    # Add metrics endpoint (Prometheus format)
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    logger.info("Monitoring setup complete")


# Decorators for monitoring
def monitor_async(
    name: str = None,
    record_duration: bool = True,
    capture_errors: bool = True
):
    """Decorator to monitor async functions."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = name or f"{func.__module__}.{func.__name__}"
            
            # Start tracing
            async with tracing_service.trace_operation(func_name) as span:
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    if record_duration:
                        duration = time.time() - start_time
                        if span:
                            span.set_attribute("duration_ms", round(duration * 1000, 2))
                    
                    return result
                    
                except Exception as e:
                    if capture_errors:
                        error_tracker.capture_exception(
                            e,
                            context={
                                "function": func_name,
                                "args": str(args)[:1000],
                                "kwargs": str(kwargs)[:1000]
                            }
                        )
                    raise
        
        return wrapper
    return decorator


# Example usage
"""
@monitor_async(name="process_payment", record_duration=True)
async def process_payment_with_monitoring(request: PaymentRequest):
    # Your payment processing logic
    # Automatically traced and monitored
    pass

@tracing_service.trace_async()
async def complex_operation():
    async with tracing_service.trace_operation("step_1"):
        # Step 1 logic
        pass
    
    async with tracing_service.trace_operation("step_2"):
        # Step 2 logic
        pass
"""
