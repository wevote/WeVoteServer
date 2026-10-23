import os
import logging

from config.environment_variable_functions import get_environment_variable_default
from opentelemetry import metrics, trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging.handler import LoggingHandler

from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

_initialized = False

def setup_opentelemetry():
    global _initialized
    if _initialized or os.getenv("OTEL_SDK_ENABLED", "").lower() not in ("true", "1"):
        print ("OpenTelemetry Already Initialized. Skipping setup...")
        return
    
    print ("Initializing OpenTelemetry...")
    resource = Resource.create({
        SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "WevoteApi-DevAPI"),
    })

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if endpoint:
        #Set up trace collection and export to OTLP
        provider_kwargs = {"resource": resource}
        if os.getenv("OTEL_PYTHON_ID_GENERATOR") == "xray":
            provider_kwargs["id_generator"] = AwsXRayIdGenerator()

        provider = TracerProvider(**provider_kwargs)
        if endpoint:
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)

        #Set up metrics collection and export to OTLP. default 30 second batches.
        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=endpoint),
            export_interval_millis=int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL", "30000")),
        )
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))

        #Set up logging collection and export to OTLP
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint))
        )
        set_logger_provider(logger_provider)
        log_level = get_environment_variable_default("LOG_FILE_LEVEL", "INFO")
        logging.getLogger().addHandler(
            LoggingHandler(level=log_level, logger_provider=logger_provider)
        )

    DjangoInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    SystemMetricsInstrumentor().instrument()
    print ("OpenTelemetry Initialized Successfully")
    _initialized = True