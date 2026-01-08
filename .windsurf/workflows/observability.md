---
allowed-tools: "*"
description: Add observability and instrumentation to existing projects
---
allowed-tools: "*"

# Observability Workflow

> **Purpose:** Add metrics, logging, tracing, and monitoring to an existing project.
> Run this when you need to instrument a codebase that wasn't set up with observability from the start.

---
allowed-tools: "*"

## Step 0: Assess Current State
// turbo

1. **Detect existing observability:**
   ```bash
   # Check for existing instrumentation
   grep -r "prometheus\|opentelemetry\|datadog\|newrelic\|sentry" package.json pyproject.toml go.mod Cargo.toml 2>/dev/null || echo "No observability packages found"
   
   # Check for logging libraries
   grep -r "winston\|pino\|bunyan\|structlog\|logrus\|tracing" . --include="*.json" --include="*.toml" 2>/dev/null | head -10
   
   # Check for health endpoints
   grep -rn "health\|ready\|live" . --include="*.ts" --include="*.py" --include="*.go" 2>/dev/null | head -10
   ```

2. **Identify stack from project files:**
   - Node.js: `package.json`
   - Python: `pyproject.toml`, `requirements.txt`
   - Go: `go.mod`
   - Rust: `Cargo.toml`

3. **Display current state:**
   ```
   📊 OBSERVABILITY ASSESSMENT
   
   Stack detected: [Node.js/Python/Go/Rust/etc.]
   
   Current instrumentation:
   - Logging: [None / Winston / Pino / etc.]
   - Metrics: [None / Prometheus / StatsD / etc.]
   - Tracing: [None / OpenTelemetry / Jaeger / etc.]
   - Error tracking: [None / Sentry / Bugsnag / etc.]
   - Health checks: [None / Basic / Full]
   
   Gaps identified:
   - [ ] No structured logging
   - [ ] No metrics collection
   - [ ] No distributed tracing
   - [ ] No error tracking
   - [ ] No health endpoints
   ```

## Step 1: Choose Observability Stack

**Ask the user to select their preferred approach:**

### 1A. Managed Services (Easiest)
Best for: Teams who want minimal setup and maintenance.

| Service | Best For | Pricing Model |
|---
allowed-tools: "*"------|----------|---------------|
| **Datadog** | Full-stack observability, APM | Per host + ingestion |
| **New Relic** | APM, browser monitoring | Per GB ingested |
| **Sentry** | Error tracking, performance | Per event |
| **Honeycomb** | High-cardinality debugging | Per event |
| **Grafana Cloud** | Metrics + logs + traces | Per series/GB |

### 1B. Self-Hosted / Open Source (More Control)
Best for: Cost-conscious teams, data sovereignty requirements.

| Stack | Components | Complexity |
|---
allowed-tools: "*"----|------------|------------|
| **OpenTelemetry + Grafana** | OTel SDK → Collector → Grafana/Loki/Tempo | Medium |
| **Prometheus + Grafana** | Prometheus scraping → Grafana dashboards | Medium |
| **ELK Stack** | Elasticsearch + Logstash + Kibana | High |
| **Jaeger** | Distributed tracing only | Low |

### 1C. Hybrid (Recommended for Most)
Best for: Balance of control and convenience.

```
📦 RECOMMENDED HYBRID STACK:

Logging:     Structured logs → OpenTelemetry Collector → Grafana Loki (or Datadog)
Metrics:     OpenTelemetry SDK → Prometheus → Grafana (or Datadog)
Tracing:     OpenTelemetry SDK → Collector → Jaeger/Tempo (or Datadog)
Errors:      Sentry (managed) - excellent DX, affordable
Uptime:      Better Uptime / Checkly / UptimeRobot (managed)

Why hybrid?
- Sentry is best-in-class for errors (hard to self-host well)
- OpenTelemetry gives you vendor flexibility
- Grafana stack is free and powerful for metrics/logs
```

**Capture selection in `.cfoi/branches/<branch>/observability-config.json`:**
```json
{
  "stack": "hybrid",
  "logging": "opentelemetry",
  "metrics": "prometheus",
  "tracing": "jaeger",
  "errors": "sentry",
  "uptime": "betteruptime"
}
```

## Step 2: Install Instrumentation Libraries

### 2A. Node.js / TypeScript

**OpenTelemetry (Recommended):**
```bash
npm install @opentelemetry/api \
  @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-prometheus \
  @opentelemetry/exporter-trace-otlp-http
```

**Structured Logging (Pino recommended):**
```bash
npm install pino pino-pretty
```

**Error Tracking (Sentry):**
```bash
npm install @sentry/node
```

### 2B. Python

**OpenTelemetry:**
```bash
pip install opentelemetry-api \
  opentelemetry-sdk \
  opentelemetry-instrumentation \
  opentelemetry-exporter-prometheus \
  opentelemetry-exporter-otlp
```

**Structured Logging (structlog):**
```bash
pip install structlog
```

**Error Tracking (Sentry):**
```bash
pip install sentry-sdk
```

### 2C. Go

**OpenTelemetry:**
```bash
go get go.opentelemetry.io/otel \
  go.opentelemetry.io/otel/sdk \
  go.opentelemetry.io/otel/exporters/prometheus \
  go.opentelemetry.io/otel/exporters/otlp/otlptrace
```

**Structured Logging (zerolog or zap):**
```bash
go get github.com/rs/zerolog
# or
go get go.uber.org/zap
```

**Error Tracking (Sentry):**
```bash
go get github.com/getsentry/sentry-go
```

## Step 3: Add Core Instrumentation

### 3A. Tracing Setup (OpenTelemetry)

**Node.js - Create `src/instrumentation.ts`:**
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

process.on('SIGTERM', () => {
  sdk.shutdown().then(() => process.exit(0));
});

export { sdk };
```

**Import at app entry point (MUST be first import):**
```typescript
import './instrumentation';
// ... rest of imports
```

### 3B. Structured Logging

**Node.js - Create `src/lib/logger.ts`:**
```typescript
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label }),
  },
  base: {
    service: process.env.SERVICE_NAME || 'my-service',
    env: process.env.NODE_ENV || 'development',
  },
  // Add trace context for correlation
  mixin() {
    const span = trace.getActiveSpan();
    if (span) {
      const context = span.spanContext();
      return {
        trace_id: context.traceId,
        span_id: context.spanId,
      };
    }
    return {};
  },
});

// Usage:
// logger.info({ userId: 123 }, 'User logged in');
// logger.error({ err, requestId }, 'Failed to process request');
```

### 3C. Error Tracking (Sentry)

**Node.js - Create `src/lib/sentry.ts`:**
```typescript
import * as Sentry from '@sentry/node';

export function initSentry() {
  if (!process.env.SENTRY_DSN) {
    console.warn('SENTRY_DSN not set, error tracking disabled');
    return;
  }

  Sentry.init({
    dsn: process.env.SENTRY_DSN,
    environment: process.env.NODE_ENV || 'development',
    tracesSampleRate: parseFloat(process.env.SENTRY_TRACES_SAMPLE_RATE || '0.1'),
    integrations: [
      // Auto-instrument HTTP, Express, etc.
      ...Sentry.autoDiscoverNodePerformanceMonitoringIntegrations(),
    ],
  });
}

// Capture errors with context
export function captureError(error: Error, context?: Record<string, any>) {
  Sentry.captureException(error, { extra: context });
}
```

### 3D. Health Check Endpoints

**Node.js (Express/Fastify):**
```typescript
// Health check types
interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  checks: {
    database?: { status: string; latency_ms?: number };
    redis?: { status: string; latency_ms?: number };
    external_api?: { status: string };
  };
  version: string;
  uptime_seconds: number;
}

// GET /health - Basic liveness
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// GET /health/ready - Readiness with dependency checks
app.get('/health/ready', async (req, res) => {
  const checks: HealthStatus['checks'] = {};
  let overallStatus: HealthStatus['status'] = 'healthy';

  // Check database
  try {
    const start = Date.now();
    await db.query('SELECT 1');
    checks.database = { status: 'ok', latency_ms: Date.now() - start };
  } catch (err) {
    checks.database = { status: 'error' };
    overallStatus = 'unhealthy';
  }

  // Check Redis
  try {
    const start = Date.now();
    await redis.ping();
    checks.redis = { status: 'ok', latency_ms: Date.now() - start };
  } catch (err) {
    checks.redis = { status: 'error' };
    overallStatus = 'degraded';
  }

  const response: HealthStatus = {
    status: overallStatus,
    checks,
    version: process.env.APP_VERSION || '0.0.0',
    uptime_seconds: process.uptime(),
  };

  res.status(overallStatus === 'unhealthy' ? 503 : 200).json(response);
});

// GET /metrics - Prometheus metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', 'text/plain');
  res.send(await promClient.register.metrics());
});
```

### 3E. Custom Metrics

**Node.js - Create `src/lib/metrics.ts`:**
```typescript
import { metrics } from '@opentelemetry/api';

const meter = metrics.getMeter('my-service');

// Counter - things that only go up
export const requestCounter = meter.createCounter('http_requests_total', {
  description: 'Total HTTP requests',
});

// Histogram - measure distributions (latency, sizes)
export const requestDuration = meter.createHistogram('http_request_duration_ms', {
  description: 'HTTP request duration in milliseconds',
  unit: 'ms',
});

// Gauge - current value (connections, queue size)
export const activeConnections = meter.createObservableGauge('active_connections', {
  description: 'Number of active connections',
});

// Usage in middleware:
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    
    requestCounter.add(1, {
      method: req.method,
      path: req.route?.path || req.path,
      status: res.statusCode.toString(),
    });
    
    requestDuration.record(duration, {
      method: req.method,
      path: req.route?.path || req.path,
    });
  });
  
  next();
});
```

## Step 4: Add Infrastructure Components

### 4A. Docker Compose for Local Development

**Create/update `infra/docker-compose.observability.yml`:**
```yaml
services:
  # OpenTelemetry Collector - receives and exports telemetry
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./observability/otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8889:8889"   # Prometheus metrics
    depends_on:
      - jaeger
      - prometheus

  # Jaeger - distributed tracing
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686" # UI
      - "14268:14268" # Accept spans

  # Prometheus - metrics storage
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  # Grafana - dashboards
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./observability/grafana/provisioning:/etc/grafana/provisioning
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
      - jaeger

  # Loki - log aggregation
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml

volumes:
  grafana-data:
```

### 4B. OpenTelemetry Collector Config

**Create `infra/observability/otel-collector-config.yaml`:**
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  
  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  # Export traces to Jaeger
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true

  # Export metrics to Prometheus
  prometheus:
    endpoint: "0.0.0.0:8889"

  # Export logs to Loki
  loki:
    endpoint: http://loki:3100/loki/api/v1/push

  # Debug logging (disable in production)
  logging:
    loglevel: debug

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [jaeger, logging]
    
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
    
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [loki]
```

### 4C. Prometheus Config

**Create `infra/observability/prometheus.yml`:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Scrape Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Scrape OpenTelemetry Collector
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']

  # Scrape your services (add your service endpoints)
  - job_name: 'backend'
    static_configs:
      - targets: ['host.docker.internal:9464']
    metrics_path: '/metrics'
```

## Step 5: Environment Variables

**Add to `.env.example`:**
```bash
# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=my-service
METRICS_PORT=9464

# Sentry (get DSN from sentry.io)
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1

# Logging
LOG_LEVEL=info
```

## Step 6: Verify Instrumentation

### 6A. Start Observability Stack
```bash
docker compose -f infra/docker-compose.observability.yml up -d
```

### 6B. Start Your Service
```bash
npm run dev
```

### 6C. Generate Traffic
```bash
# Hit your endpoints a few times
curl http://localhost:3000/health
curl http://localhost:3000/api/users
```

### 6D. Verify Each Component

| Component | URL | What to Check |
|---
allowed-tools: "*"--------|-----|---------------|
| **Jaeger** | http://localhost:16686 | Traces appear, spans linked |
| **Prometheus** | http://localhost:9090 | Metrics scraped, queries work |
| **Grafana** | http://localhost:3001 | Dashboards load, data sources connected |
| **Metrics endpoint** | http://localhost:9464/metrics | Prometheus format output |

### 6E. Checklist
```
📊 OBSERVABILITY VERIFICATION

Tracing:
- [ ] Traces appear in Jaeger
- [ ] Spans are properly linked (parent-child)
- [ ] Service name is correct
- [ ] HTTP requests are auto-instrumented

Metrics:
- [ ] /metrics endpoint returns Prometheus format
- [ ] Custom metrics appear (http_requests_total, etc.)
- [ ] Prometheus is scraping successfully
- [ ] Grafana can query Prometheus

Logging:
- [ ] Logs are structured JSON
- [ ] Logs include trace_id for correlation
- [ ] Log levels work (info, warn, error)
- [ ] Logs appear in Loki/Grafana

Errors:
- [ ] Sentry receives test error
- [ ] Stack traces are readable
- [ ] Source maps work (if applicable)

Health:
- [ ] /health returns 200
- [ ] /health/ready checks dependencies
- [ ] Unhealthy state returns 503
```

## Step 7: Create Grafana Dashboards

### 7A. Service Overview Dashboard

**Create `infra/observability/grafana/provisioning/dashboards/service-overview.json`:**

Key panels to include:
1. **Request Rate** - `rate(http_requests_total[5m])`
2. **Error Rate** - `rate(http_requests_total{status=~"5.."}[5m])`
3. **Latency P50/P95/P99** - `histogram_quantile(0.95, rate(http_request_duration_ms_bucket[5m]))`
4. **Active Connections** - `active_connections`
5. **Database Latency** - From health check metrics
6. **Error Log Count** - From Loki

### 7B. RED Metrics Dashboard

The RED method (Rate, Errors, Duration) is standard for services:

```
Rate:     How many requests per second?
Errors:   How many of those requests are failing?
Duration: How long do the requests take?
```

## Step 8: Production Considerations

### 8A. Sampling Strategy
```typescript
// Don't trace every request in production
const sampler = new TraceIdRatioBasedSampler(0.1); // 10% of traces

// Or use adaptive sampling
const sampler = new ParentBasedSampler({
  root: new TraceIdRatioBasedSampler(0.1),
});
```

### 8B. Sensitive Data
```typescript
// Redact sensitive attributes
const spanProcessor = new SimpleSpanProcessor(exporter);
spanProcessor.onStart = (span) => {
  // Remove sensitive headers
  span.setAttribute('http.request.header.authorization', '[REDACTED]');
};
```

### 8C. Cost Management
- **Metrics:** Use recording rules to pre-aggregate
- **Traces:** Sample aggressively (1-10%)
- **Logs:** Set appropriate log levels, use structured logging
- **Retention:** Configure data retention policies

## Wrap Up

**Display summary:**
```
✅ OBSERVABILITY SETUP COMPLETE

Installed:
- OpenTelemetry SDK + auto-instrumentation
- Pino structured logging
- Sentry error tracking
- Health check endpoints
- Custom metrics

Infrastructure:
- OpenTelemetry Collector
- Jaeger (tracing)
- Prometheus (metrics)
- Grafana (dashboards)
- Loki (logs)

Endpoints:
- /health - Liveness probe
- /health/ready - Readiness probe
- /metrics - Prometheus metrics

Dashboards:
- Service Overview
- RED Metrics

Next steps:
1. Add SENTRY_DSN to production secrets
2. Configure alerting rules in Grafana
3. Set up uptime monitoring (Better Uptime, Checkly)
4. Review sampling rates for production

Run: docker compose -f infra/docker-compose.observability.yml up -d
```

**Save configuration to:** `.cfoi/branches/<branch>/observability-config.json`
