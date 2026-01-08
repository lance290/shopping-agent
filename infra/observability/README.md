# Observability Stack

Local development observability stack using OpenTelemetry, Prometheus, Grafana, Jaeger, and Loki.

## Quick Start

```bash
# Start the observability stack
docker compose -f infra/observability/docker-compose.observability.yml up -d

# View logs
docker compose -f infra/observability/docker-compose.observability.yml logs -f
```

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **Jaeger** | http://localhost:16686 | - |
| **Loki** | http://localhost:3100 | - |
| **OTel Collector** | http://localhost:4318 (HTTP) / :4317 (gRPC) | - |

## Architecture

```
┌─────────────────┐     ┌─────────────────────┐
│   Your Service  │────▶│  OTel Collector     │
│                 │     │  (receives all      │
│  - Traces       │     │   telemetry)        │
│  - Metrics      │     └─────────┬───────────┘
│  - Logs         │               │
└─────────────────┘               │
                                  ▼
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
       ┌──────────┐        ┌──────────┐        ┌──────────┐
       │  Jaeger  │        │Prometheus│        │   Loki   │
       │ (traces) │        │ (metrics)│        │  (logs)  │
       └────┬─────┘        └────┬─────┘        └────┬─────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
                                ▼
                         ┌──────────┐
                         │ Grafana  │
                         │(dashboards)
                         └──────────┘
```

## Instrumenting Your Service

### Node.js / TypeScript

1. **Install dependencies:**
```bash
npm install @opentelemetry/api @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-prometheus \
  @opentelemetry/exporter-trace-otlp-http \
  pino @sentry/node
```

2. **Create `src/instrumentation.ts`:**
```typescript
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { PrometheusExporter } from '@opentelemetry/exporter-prometheus';

const sdk = new NodeSDK({
  serviceName: process.env.SERVICE_NAME || 'my-service',
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318/v1/traces',
  }),
  metricReader: new PrometheusExporter({
    port: parseInt(process.env.METRICS_PORT || '9464'),
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
```

3. **Import at the TOP of your entry point:**
```typescript
import './instrumentation';  // MUST be first!
// ... rest of imports
```

### Python

1. **Install dependencies:**
```bash
pip install opentelemetry-api opentelemetry-sdk \
  opentelemetry-instrumentation opentelemetry-exporter-otlp \
  structlog sentry-sdk
```

2. **Initialize in your app:**
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces"))
)
```

## Environment Variables

Add to your `.env`:
```bash
# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=my-service
METRICS_PORT=9464

# Sentry (optional)
SENTRY_DSN=your-sentry-dsn
SENTRY_TRACES_SAMPLE_RATE=0.1

# Logging
LOG_LEVEL=info
```

## Dashboards

Pre-configured dashboards are automatically loaded:

- **Service Overview (RED Metrics)** - Request rate, error rate, latency
- Add custom dashboards to `grafana/provisioning/dashboards/`

## Customization

### Adding More Services to Prometheus

Edit `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'my-new-service'
    static_configs:
      - targets: ['host.docker.internal:9465']
    metrics_path: /metrics
```

### Custom Metrics

```typescript
import { metrics } from '@opentelemetry/api';

const meter = metrics.getMeter('my-service');

// Counter
const requestCounter = meter.createCounter('http_requests_total');
requestCounter.add(1, { method: 'GET', path: '/api/users' });

// Histogram
const latencyHistogram = meter.createHistogram('http_request_duration_ms');
latencyHistogram.record(42, { method: 'GET', path: '/api/users' });
```

## Production Considerations

1. **Sampling** - Don't trace every request:
   ```typescript
   const sampler = new TraceIdRatioBasedSampler(0.1); // 10%
   ```

2. **Data Retention** - Configure in `prometheus.yml`:
   ```yaml
   --storage.tsdb.retention.time=15d
   ```

3. **Security** - The collector config redacts sensitive headers automatically

4. **Managed Services** - For production, consider:
   - Grafana Cloud (metrics + logs)
   - Datadog (full APM)
   - Sentry (errors)

## Troubleshooting

### No traces appearing in Jaeger
- Check OTel Collector logs: `docker compose logs otel-collector`
- Verify your service is sending to the correct endpoint
- Check the collector health: http://localhost:13133

### No metrics in Prometheus
- Check Prometheus targets: http://localhost:9090/targets
- Verify your service exposes `/metrics` endpoint
- Check if `host.docker.internal` resolves (Mac/Windows only)

### Grafana shows "No data"
- Verify data sources are connected (Settings → Data Sources)
- Check time range (default is last 1 hour)
- Run a test query in Prometheus first

## Related Workflows

- `/observability` - Add observability to existing projects
- `/bootup` - Set up observability during project scaffolding
- `/implement` - Observability check in Quick Review Gate
