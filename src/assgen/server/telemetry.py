"""OpenTelemetry instrumentation for assgen-server.

Instruments the FastAPI application to emit the Google SRE 4 Golden Signals:

  Latency    — http.server.request.duration histogram (P50/P95/P99 via FastAPI auto-instrumentation)
  Traffic    — http.server.request.duration count (rate = requests per second)
  Errors     — http.server.request.duration filtered by http_response_status_code >= 400
  Saturation — assgen.jobs.active + assgen.jobs.queued (custom UpDownCounters)

Custom job metrics:
  assgen.jobs.enqueued   counter   — jobs submitted
  assgen.jobs.completed  counter   — jobs finished successfully
  assgen.jobs.failed     counter   — jobs finished with an error
  assgen.jobs.active     gauge     — jobs currently being processed
  assgen.jobs.queued     gauge     — jobs waiting in queue
  assgen.jobs.duration   histogram — seconds from start to completion

All telemetry is exported via OTLP HTTP to the endpoint configured in
server.yaml under ``telemetry.otlp_endpoint`` (default: http://localhost:4318).

When the opentelemetry packages are not installed, every function here is a
no-op so the server starts normally without observability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature flag — set to True once the OTel SDK is imported successfully
# ---------------------------------------------------------------------------
_OTEL_AVAILABLE = False

try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace as otel_trace
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_AVAILABLE = True
except ImportError:
    logger.debug("opentelemetry packages not installed — telemetry disabled")

_LOG_OTEL_AVAILABLE = False
try:
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    _LOG_OTEL_AVAILABLE = True
except ImportError:
    pass

_FASTAPI_INSTRUMENTATION_AVAILABLE = False
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    _FASTAPI_INSTRUMENTATION_AVAILABLE = True
except ImportError:
    pass

_HTTPX_INSTRUMENTATION_AVAILABLE = False
try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    _HTTPX_INSTRUMENTATION_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Job metrics container
# ---------------------------------------------------------------------------


@dataclass
class JobMetrics:
    """Custom OTel metrics for the assgen job pipeline.

    Tracks the Saturation golden signal (active/queued jobs) and job
    throughput/failure rates for SRE visibility.
    """

    enqueued: Any = field(default=None)
    completed: Any = field(default=None)
    failed: Any = field(default=None)
    active: Any = field(default=None)
    queued: Any = field(default=None)
    duration: Any = field(default=None)

    def record_enqueued(self, job_type: str) -> None:
        if self.enqueued:
            self.enqueued.add(1, {"job_type": job_type})
        if self.queued:
            self.queued.add(1, {"job_type": job_type})

    def record_started(self, job_type: str) -> None:
        if self.active:
            self.active.add(1, {"job_type": job_type})
        if self.queued:
            self.queued.add(-1, {"job_type": job_type})

    def record_completed(self, job_type: str, duration_seconds: float) -> None:
        if self.completed:
            self.completed.add(1, {"job_type": job_type})
        if self.active:
            self.active.add(-1, {"job_type": job_type})
        if self.duration:
            self.duration.record(duration_seconds, {"job_type": job_type})

    def record_failed(self, job_type: str, duration_seconds: float) -> None:
        if self.failed:
            self.failed.add(1, {"job_type": job_type})
        if self.active:
            self.active.add(-1, {"job_type": job_type})
        if self.duration:
            self.duration.record(duration_seconds, {"job_type": job_type})

    def record_cancelled(self, job_type: str) -> None:
        if self.active:
            self.active.add(-1, {"job_type": job_type})
        if self.queued:
            self.queued.add(-1, {"job_type": job_type})


# Module-level singleton populated by setup_telemetry()
_job_metrics: JobMetrics | None = None


def get_job_metrics() -> JobMetrics | None:
    return _job_metrics


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def setup_telemetry(tel_cfg: dict[str, Any], app_version: str = "unknown") -> None:
    """Initialise OTel providers from server config.

    Safe to call even if the otel packages are not installed — logs a warning
    and returns without raising.

    Args:
        tel_cfg: The ``telemetry`` sub-dict from the server config.
        app_version: Injected from ``get_version_info()`` for the service.version resource attribute.
    """
    global _job_metrics  # noqa: PLW0603

    if not _OTEL_AVAILABLE:
        logger.warning(
            "OpenTelemetry SDK not installed — install assgen[telemetry] to enable observability"
        )
        _job_metrics = JobMetrics()  # no-op metrics
        return

    endpoint = tel_cfg.get("otlp_endpoint", "http://localhost:4318")
    service_name = tel_cfg.get("service_name", "assgen-server")
    export_interval_ms = int(tel_cfg.get("export_interval_ms", 5000))

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: app_version,
            "deployment.environment": "local",
        }
    )

    # ── Traces ────────────────────────────────────────────────────────────────
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    otel_trace.set_tracer_provider(tracer_provider)

    # ── Metrics ───────────────────────────────────────────────────────────────
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
        export_interval_millis=export_interval_ms,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    otel_metrics.set_meter_provider(meter_provider)

    # ── Logs ──────────────────────────────────────────────────────────────────
    if _LOG_OTEL_AVAILABLE:
        log_provider = LoggerProvider(resource=resource)
        log_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{endpoint}/v1/logs"))
        )
        set_logger_provider(log_provider)

    # ── HTTPX outbound instrumentation ────────────────────────────────────────
    if _HTTPX_INSTRUMENTATION_AVAILABLE:
        HTTPXClientInstrumentor().instrument()

    # ── Custom job metrics ────────────────────────────────────────────────────
    meter = otel_metrics.get_meter(service_name)
    _job_metrics = JobMetrics(
        enqueued=meter.create_counter(
            "assgen.jobs.enqueued",
            unit="{job}",
            description="Total number of jobs submitted to the queue",
        ),
        completed=meter.create_counter(
            "assgen.jobs.completed",
            unit="{job}",
            description="Total number of jobs that completed successfully",
        ),
        failed=meter.create_counter(
            "assgen.jobs.failed",
            unit="{job}",
            description="Total number of jobs that failed or were cancelled",
        ),
        active=meter.create_up_down_counter(
            "assgen.jobs.active",
            unit="{job}",
            description="Number of jobs currently being processed (running)",
        ),
        queued=meter.create_up_down_counter(
            "assgen.jobs.queued",
            unit="{job}",
            description="Number of jobs waiting in the queue",
        ),
        duration=meter.create_histogram(
            "assgen.jobs.duration",
            unit="s",
            description="Wall-clock duration from job start to completion (seconds)",
        ),
    )

    logger.info(
        "OpenTelemetry initialised",
        extra={"otlp_endpoint": endpoint, "service_name": service_name},
    )


def instrument_app(app: Any) -> None:
    """Auto-instrument a FastAPI app instance.

    Must be called AFTER ``setup_telemetry()`` and after the FastAPI app
    object is created.  Safe to call when otel is unavailable.
    """
    if not _FASTAPI_INSTRUMENTATION_AVAILABLE:
        return
    FastAPIInstrumentor().instrument_app(
        app,
        server_request_hook=_server_request_hook,
    )


# ---------------------------------------------------------------------------
# Request hook — enrich spans with assgen-specific attributes
# ---------------------------------------------------------------------------


def _server_request_hook(span: Any, scope: dict[str, Any]) -> None:
    """Called for every incoming request span — add extra assgen attributes."""
    if span and span.is_recording():
        span.set_attribute("assgen.component", "server")
