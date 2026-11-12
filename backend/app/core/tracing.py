# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

from .config import get_settings

logger = get_logger(__name__)

# Module-level reference so shutdown can flush the provider
_tracer_provider: Optional[object] = None


def setup_tracing(app) -> None:
    global _tracer_provider
    settings = get_settings()

    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing is disabled (OTEL_ENABLED=false)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.semconv.resource import ResourceAttributes
        from opentelemetry.sdk.trace.sampling import (
            TraceIdRatioBased,
            ALWAYS_ON,
        )
    except ImportError as e:
        logger.warning(
            "OpenTelemetry packages not installed, tracing disabled: %s", e
        )
        return

    # Build resource identity
    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: settings.otel_service_name,
            ResourceAttributes.SERVICE_VERSION: settings.app_version,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.environment,
        }
    )

    # Configure sampler
    if settings.otel_traces_sample_rate >= 1.0:
        sampler = ALWAYS_ON
    else:
        sampler = TraceIdRatioBased(settings.otel_traces_sample_rate)

    provider = TracerProvider(resource=resource, sampler=sampler)

    # OTLP exporter to a collector (Jaeger, Tempo, etc.)
    try:
        if settings.otel_exporter_otlp_protocol == "grpc":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
        else:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(
            "OTLP exporter configured",
            extra={
                "endpoint": settings.otel_exporter_otlp_endpoint,
                "protocol": settings.otel_exporter_otlp_protocol,
            },
        )
    except Exception as e:  # noqa: BLE001  # startup boundary — OTLP exporter setup must not block app boot
        logger.warning("Failed to configure OTLP exporter: %s", e)

    # Optional console exporter for local development
    if settings.otel_log_spans:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Console span exporter enabled (OTEL_LOG_SPANS=true)")

    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    # --- Instrument libraries ---
    _instrument_fastapi(app)
    _instrument_sqlalchemy()
    _instrument_redis()
    _instrument_httpx()

    logger.info(
        "OpenTelemetry tracing initialized",
        extra={
            "service": settings.otel_service_name,
            "sample_rate": settings.otel_traces_sample_rate,
        },
    )


def shutdown_tracing() -> None:
    global _tracer_provider
    if _tracer_provider is None:
        return

    try:
        _tracer_provider.shutdown()
        logger.info("OpenTelemetry tracer provider shut down")
    except Exception as e:  # noqa: BLE001  # shutdown boundary — tracer flush must not block app shutdown
        logger.warning("Error shutting down tracer provider: %s", e)
    finally:
        _tracer_provider = None


# ---------------------------------------------------------------------------
# Library-specific instrumentation
# ---------------------------------------------------------------------------


def _instrument_fastapi(app) -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health,health/db",
        )
        logger.info("FastAPI instrumented for tracing")
    except Exception as e:  # noqa: BLE001  # startup boundary — instrumentation must not block app boot
        logger.warning("Failed to instrument FastAPI: %s", e)


def _instrument_sqlalchemy() -> None:
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from .database import engine

        if engine is not None:
            SQLAlchemyInstrumentor().instrument(
                engine=engine.sync_engine,
            )
            logger.info("SQLAlchemy instrumented for tracing")
        else:
            logger.info("SQLAlchemy engine is None (migration mode?), skipping instrumentation")
    except Exception as e:  # noqa: BLE001  # startup boundary — instrumentation must not block app boot
        logger.warning("Failed to instrument SQLAlchemy: %s", e)


def _instrument_redis() -> None:
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
        logger.info("Redis instrumented for tracing")
    except Exception as e:  # noqa: BLE001  # startup boundary — instrumentation must not block app boot
        logger.warning("Failed to instrument Redis: %s", e)


def _instrument_httpx() -> None:
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        logger.info("httpx instrumented for tracing")
    except Exception as e:  # noqa: BLE001  # startup boundary — instrumentation must not block app boot
        logger.warning("Failed to instrument httpx: %s", e)


# ---------------------------------------------------------------------------
# Convenience helpers for manual instrumentation in service code
# ---------------------------------------------------------------------------


def get_tracer(name: str):
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        # Return a no-op object whose ``start_as_current_span`` is a pass-through
        return _NoOpTracer()


def get_current_span():
    try:
        from opentelemetry import trace
        return trace.get_current_span()
    except ImportError:
        return _NoOpSpan()


def add_span_attributes(**attrs) -> None:
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span and span.is_recording():
            for key, value in attrs.items():
                if value is not None:
                    span.set_attribute(key, value)
    except ImportError:
        logger.debug("OpenTelemetry not installed, skipping span attribute setting")


def record_exception(exc: BaseException) -> None:
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span and span.is_recording():
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
    except ImportError:
        logger.debug("OpenTelemetry not installed, skipping exception recording")


# ---------------------------------------------------------------------------
# No-op fallbacks (when OpenTelemetry is not installed)
# ---------------------------------------------------------------------------


class _NoOpSpan:

    def set_attribute(self, key, value):
        pass

    def set_status(self, *args, **kwargs):
        pass

    def record_exception(self, exc):
        pass

    def is_recording(self):
        return False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _NoOpTracer:

    def start_as_current_span(self, name, **kwargs):
        return _NoOpSpan()

    def start_span(self, name, **kwargs):
        return _NoOpSpan()
