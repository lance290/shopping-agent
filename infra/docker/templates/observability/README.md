# Observability Stack

Complete observability solution with **Prometheus** (metrics), **Grafana** (dashboards), **Jaeger** (tracing), and **Loki** (logs).

---

## The Three Pillars of Observability

### 1. **Metrics** (Prometheus)
- Numbers over time: CPU, memory, request rate
- "How much?" and "How fast?"
- Alerts when things go wrong

### 2. **Logs** (Loki)
- Textual records of events
- "What happened?"
- Debug specific issues

### 3. **Traces** (Jaeger)
- Request flow across services
- "Where is the bottleneck?"
- Performance optimization

---

## Quick Start

```bash
# Start entire observability stack
docker-compose up -d

# Access dashboards
open http://localhost:3000      # Grafana (admin/admin)
open http://localhost:9090      # Prometheus
open http://localhost:16686     # Jaeger

# Send test requests to example app
curl http://localhost:8080/
curl http://localhost:8080/api/slow
```

**View metrics in Grafana:**
1. Login to Grafana (admin/admin)
2. Go to Dashboards
3. See request rate, latency, errors

**View traces in Jaeger:**
1. Open Jaeger UI
2. Select "example-app" service
3. See end-to-end request traces

---

## What's Included

### Prometheus
- Metrics collection and storage
- Query language (PromQL)
- Alert manager (optional)
- **Port**: 9090

### Grafana
- Beautiful dashboards
- Pre-configured data sources
- Alerting
- **Port**: 3000 (admin/admin)

### Jaeger
- Distributed tracing
- Service dependency graph
- Performance analysis
- **Port**: 16686

### Loki (Optional)
- Log aggregation
- Grafana integration
- **Port**: 3100

### Node Exporter (Optional)
- System metrics (CPU, memory, disk)
- **Port**: 9100

---

## Instrumenting Your Application

### Python (FastAPI/Flask)

```python
# Install
pip install prometheus-client opentelemetry-api opentelemetry-instrumentation-fastapi

# Add to your app
from prometheus_client import Counter, Histogram
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

REQUEST_COUNT = Counter('api_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('api_request_duration_seconds', 'Request latency')

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)  # Auto-tracing

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### Node.js (Express)

```javascript
// Install
// npm install prom-client @opentelemetry/auto-instrumentations-node

const prometheus = require('prom-client');
const requestCounter = new prometheus.Counter({
  name: 'api_requests_total',
  help: 'Total requests'
});

// Expose metrics
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', prometheus.register.contentType);
  res.end(await prometheus.register.metrics());
});
```

### Go

```go
// Install
// go get github.com/prometheus/client_golang/prometheus

import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

var requestCounter = prometheus.NewCounter(
    prometheus.CounterOpts{
        Name: "api_requests_total",
        Help: "Total requests",
    },
)

func init() {
    prometheus.MustRegister(requestCounter)
}

// Expose metrics
http.Handle("/metrics", promhttp.Handler())
```

---

## Key Metrics to Track

### Application Metrics
- **Request rate**: `rate(api_requests_total[5m])`
- **Error rate**: `rate(api_errors_total[5m])`
- **Latency (p95)**: `histogram_quantile(0.95, api_request_duration_seconds)`
- **Active users**: `api_active_users_gauge`

### Infrastructure Metrics
- **CPU usage**: `node_cpu_seconds_total`
- **Memory usage**: `node_memory_MemAvailable_bytes`
- **Disk I/O**: `node_disk_io_time_seconds_total`
- **Network**: `node_network_receive_bytes_total`

### Business Metrics
- **Signups**: `signups_total`
- **Purchases**: `purchases_total`
- **Revenue**: `revenue_total`

---

## Creating Dashboards

### In Grafana:

1. **Add Panel**
2. **Select Data Source**: Prometheus
3. **Write PromQL Query**:
```promql
# Request rate
rate(api_requests_total[5m])

# Error rate %
rate(api_errors_total[5m]) / rate(api_requests_total[5m]) * 100

# p95 latency
histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))
```
4. **Visualize**: Graph, Gauge, Table, etc.

---

## Alerting

### Prometheus Alert Rules

Create `prometheus/alerts/rules.yml`:

```yaml
groups:
  - name: application
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(api_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m])) > 1.0
        for: 10m
        labels:
          severity: warning
```

### Grafana Alerts

1. Go to dashboard panel
2. Click "Alert" tab
3. Set condition (e.g., "WHEN avg() OF query IS ABOVE 100")
4. Configure notification channel (Slack, PagerDuty, email)

---

## Distributed Tracing with Jaeger

### Why Tracing?

**Without tracing:**
- "The API is slow" (but why?)

**With tracing:**
- API: 2s total
  - Auth service: 100ms ✅
  - Database query: 1.8s ❌ (FOUND IT!)
  - Cache: 50ms ✅

### View Traces

1. Open Jaeger UI (http://localhost:16686)
2. Select service
3. Find slow traces
4. Click trace to see spans
5. Identify bottleneck

### Custom Spans

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def process_payment(amount):
    with tracer.start_as_current_span("process_payment"):
        # Your code here
        charge_card(amount)
        send_receipt()
```

---

## Production Deployment

### Option 1: Managed Services

**Metrics:**
- Grafana Cloud (free tier, then $8/month)
- Datadog ($15/host/month)
- New Relic ($100/month)

**Traces:**
- Grafana Tempo (free with Grafana Cloud)
- Datadog APM (included)
- Jaeger (self-hosted on K8s)

**Logs:**
- Grafana Loki (free tier)
- Datadog Logs (included)
- CloudWatch (AWS native)

### Option 2: Self-Hosted (Kubernetes)

```yaml
# prometheus-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:v2.48.0
        ports:
        - containerPort: 9090
```

---

## Cost Optimization

### Development
- Self-hosted: Free (runs on Docker)
- Storage: Local volumes

### Production (100k req/day)

**Self-Hosted:**
- $50-100/month (small VPS for Prometheus + Grafana)
- Storage: ~10GB/month

**Managed (Grafana Cloud):**
- Free tier: 10k series, 50GB logs
- Paid: $29-100/month depending on scale

**Enterprise (Datadog):**
- $300-1000+/month
- But: Full-featured, no maintenance

---

## Best Practices

### 1. **Use Labels Wisely**
```python
# ✅ Good: Low cardinality
requests_total.labels(method='GET', status='200')

# ❌ Bad: High cardinality (user ID changes constantly)
requests_total.labels(user_id='12345')  # Don't do this!
```

### 2. **Set Up Alerts Early**
- High error rate (> 1%)
- High latency (p95 > 1s)
- Service down (up == 0)

### 3. **Use Dashboards**
- Overview dashboard (RED: Rate, Errors, Duration)
- Per-service dashboards
- Infrastructure dashboard

### 4. **Retention Policies**
- Metrics: 15-30 days (Prometheus)
- Logs: 7-14 days (Loki)
- Traces: 7 days (Jaeger)

### 5. **Sample Traces**
- Production: 1-10% sampling
- Dev: 100% sampling

---

## Troubleshooting

### Issue: Prometheus not scraping targets

**Check:**
1. Is app exposing `/metrics`? `curl http://app:8080/metrics`
2. Is target configured in `prometheus.yml`?
3. Check Prometheus logs: `docker-compose logs prometheus`

### Issue: High memory usage

**Solutions:**
1. Reduce retention: `--storage.tsdb.retention.time=7d`
2. Reduce scrape frequency: `scrape_interval: 30s`
3. Use recording rules for expensive queries

### Issue: Grafana dashboard not showing data

**Check:**
1. Data source configured correctly?
2. Time range correct?
3. Query returning data in Prometheus UI?

---

## Integration with Your Stack

### Add to existing docker-compose.yml

```yaml
# Your existing services
services:
  your-api:
    build: .
    environment:
      - PROMETHEUS_PORT=8080
      - JAEGER_AGENT_HOST=jaeger
    
  # Add observability
  prometheus:
    image: prom/prometheus:v2.48.0
    volumes:
      - ./observability/prometheus:/etc/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:10.2.2
    ports:
      - "3000:3000"
```

---

## Example Queries

### Request Rate
```promql
rate(api_requests_total[5m])
```

### Error Percentage
```promql
rate(api_errors_total[5m]) / rate(api_requests_total[5m]) * 100
```

### P95 Latency
```promql
histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))
```

### Memory Usage %
```promql
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100
```

### Top 5 Endpoints by Traffic
```promql
topk(5, rate(api_requests_total[5m]))
```

---

## Resources

- **Prometheus**: https://prometheus.io/
- **Grafana**: https://grafana.com/
- **Jaeger**: https://www.jaegertracing.io/
- **OpenTelemetry**: https://opentelemetry.io/
- **Loki**: https://grafana.com/oss/loki/

---

**Created:** November 16, 2025  
**Status:** Production-Ready  
**Stack:** Prometheus + Grafana + Jaeger + Loki
