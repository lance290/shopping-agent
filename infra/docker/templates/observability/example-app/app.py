"""
Example instrumented application
Demonstrates: Prometheus metrics + Jaeger tracing
"""
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
import os

# OpenTelemetry setup for tracing
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracing
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
    agent_port=int(os.getenv("JAEGER_AGENT_PORT", 6831)),
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(jaeger_exporter))

app = FastAPI(title="Instrumented Example App")

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Prometheus metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total request count', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('app_request_duration_seconds', 'Request latency', ['endpoint'])

@app.middleware("http")
async def add_metrics(request, call_next):
    """Add metrics to all requests"""
    start_time = time.time()
    response = await call_next(request)
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path
    ).inc()
    
    REQUEST_LATENCY.labels(
        endpoint=request.url.path
    ).observe(time.time() - start_time)
    
    return response

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Instrumented app running", "metrics": "/metrics", "health": "/health"}

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/slow")
async def slow_endpoint():
    """Simulates slow endpoint for testing"""
    time.sleep(2)  # Simulate slow operation
    return {"message": "Slow operation completed"}

@app.get("/api/error")
async def error_endpoint():
    """Simulates error for testing"""
    raise Exception("Intentional error for testing")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
