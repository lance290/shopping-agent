# Message Queue Template

Production-ready message queue infrastructure supporting **Kafka**, **RabbitMQ**, and **Redis Streams**.

---

## Why Message Queues?

**Without Queue:**
```
User → API → [30s processing] → Response
❌ Slow, blocks, can timeout
```

**With Queue:**
```
User → API → Queue → Response (instant)
                ↓
           Worker processes (async)
✅ Fast, reliable, scalable
```

---

## Quick Start

```bash
# Start all infrastructure (Kafka, RabbitMQ, Redis)
docker-compose up -d

# Check status
docker-compose ps

# Send a message
curl -X POST http://localhost:8080/send \
  -H "Content-Type: application/json" \
  -d '{"topic": "tasks", "payload": {"task": "send_email", "to": "user@example.com"}}'

# Watch worker logs
docker-compose logs -f worker
```

**Management UIs:**
- RabbitMQ: http://localhost:15672 (admin/password)
- Kafka: Use `kafka-console-consumer` or install Kafka UI

---

## Supported Queue Systems

### 1. **RabbitMQ** (Recommended for most)
- ✅ Easiest to use
- ✅ Great management UI
- ✅ Perfect for task queues
- **Use for:** Email, notifications, background jobs

### 2. **Kafka** (High-throughput)
- ✅ Handles millions of messages/sec
- ✅ Event streaming
- ✅ Distributed, fault-tolerant
- **Use for:** Analytics, event sourcing, logs

### 3. **Redis Streams** (Lightweight)
- ✅ Simplest setup
- ✅ Already have Redis?
- ✅ Good for small/medium scale
- **Use for:** Real-time updates, simple queues

---

## Comparison

| Feature | RabbitMQ | Kafka | Redis |
|---------|----------|-------|-------|
| **Throughput** | Medium | Very High | Medium |
| **Latency** | Low | Medium | Very Low |
| **Setup** | Easy | Complex | Very Easy |
| **Use Case** | Task queues | Event streams | Simple queues |
| **Persistence** | Yes | Yes | Optional |
| **Management UI** | ✅ Excellent | ❌ None | ❌ Basic |

---

## Architecture

```
┌─────────────┐
│   Your API  │
└──────┬──────┘
       │ POST /send
       ↓
┌─────────────┐     ┌──────────────┐
│  Producer   │────→│ Message Queue│
│     API     │     │ (Kafka/RMQ)  │
└─────────────┘     └──────┬───────┘
                           │
                           ↓
                    ┌──────────────┐
                    │   Workers    │
                    │  (2+ replicas)│
                    └──────────────┘
```

---

## Use Cases

### 1. **Email/Notifications**
```python
# Producer (API)
await send_message({
    "topic": "emails",
    "payload": {
        "to": "user@example.com",
        "subject": "Welcome!",
        "body": "..."
    }
})

# Worker processes asynchronously
def process_message(payload):
    send_email(payload["to"], payload["subject"], payload["body"])
```

### 2. **Image Processing**
```python
# Upload returns instantly
await send_message({
    "topic": "images",
    "payload": {
        "url": "s3://bucket/image.jpg",
        "operations": ["resize", "watermark"]
    }
})

# Worker processes in background
def process_message(payload):
    image = download(payload["url"])
    image.resize(800, 600)
    image.watermark()
    image.save()
```

### 3. **Payment Webhooks**
```python
# Stripe sends webhook
@app.post("/webhooks/stripe")
async def stripe_webhook(payload):
    # Queue for processing (don't block Stripe)
    await send_message({"topic": "payments", "payload": payload})
    return {"status": "received"}

# Worker handles reliably
def process_message(payload):
    update_subscription(payload["customer_id"])
    send_receipt(payload["email"])
```

---

## Configuration

### Switch Queue Type

```bash
# Use RabbitMQ (default)
QUEUE_TYPE=rabbitmq docker-compose up

# Use Kafka
QUEUE_TYPE=kafka docker-compose up

# Use Redis
QUEUE_TYPE=redis docker-compose up
```

### Environment Variables

See `.env.example` for all configuration options.

---

## Scaling

### Horizontal Scaling (More Workers)

```yaml
# docker-compose.yml
worker:
  deploy:
    replicas: 5  # Run 5 workers
```

### Vertical Scaling (Resource Limits)

```yaml
worker:
  deploy:
    resources:
      limits:
        cpus: "2"
        memory: 2G
```

---

## Production Deployment

### Option 1: Railway
```bash
# Deploy producer API
railway up

# Deploy workers
railway up --service worker
```

### Option 2: GCP Cloud Run
```bash
# API
gcloud run deploy queue-api --source .

# Workers (Cloud Run Jobs)
gcloud run jobs create queue-worker \
  --image gcr.io/PROJECT/worker \
  --tasks 10 \
  --max-retries 3
```

### Option 3: Kubernetes
```yaml
# worker-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: queue-worker
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: worker
        image: your-registry/worker:latest
```

---

## Monitoring

### Built-in Metrics

Producer API exposes `/metrics` endpoint (Prometheus format):
- `queue_messages_sent_total`
- `queue_errors_total`
- `worker_tasks_processed_total`
- `worker_task_duration_seconds`

### RabbitMQ Dashboard

Access at http://localhost:15672
- Queue depth
- Message rate
- Consumer count
- Memory usage

### Kafka Monitoring

Use Kafka Manager or Confluent Control Center.

---

## Advanced Features

### Dead Letter Queues

```python
# RabbitMQ: Failed messages go to DLQ
channel.queue_declare(
    queue="tasks",
    arguments={
        "x-dead-letter-exchange": "dlx",
        "x-dead-letter-routing-key": "tasks.failed"
    }
)
```

### Message Prioritization

```python
# RabbitMQ: Priority queues
channel.queue_declare(
    queue="tasks",
    arguments={"x-max-priority": 10}
)

channel.basic_publish(
    body=message,
    properties=pika.BasicProperties(priority=9)  # High priority
)
```

### Delayed Messages

```python
# RabbitMQ: Schedule for future
channel.basic_publish(
    body=message,
    properties=pika.BasicProperties(
        headers={"x-delay": 60000}  # 60 seconds
    )
)
```

---

## Troubleshooting

### Issue: Messages not being consumed

**Check:**
1. Worker is running: `docker-compose ps`
2. Queue has messages: RabbitMQ UI
3. No errors in logs: `docker-compose logs worker`

### Issue: Queue filling up

**Solutions:**
1. Scale workers: Increase `replicas`
2. Optimize processing: Make `process_message()` faster
3. Add more resources: Increase CPU/memory

### Issue: Message loss

**Ensure:**
1. Persistent queues: `durable=True`
2. Message acknowledgment: `basic_ack()` after processing
3. Replication (Kafka): `replication_factor >= 3`

---

## Cost Optimization

### Development
- Use Redis (cheapest, simplest)
- Single worker replica

### Production
**RabbitMQ:**
- **Self-hosted**: $20-50/month (small instance)
- **CloudAMQP**: Free tier available, then $19/month

**Kafka:**
- **Self-hosted**: $100+/month (requires 3+ brokers)
- **Confluent Cloud**: $0.11/GB ingress

**Redis:**
- **Self-hosted**: $10-30/month
- **Redis Cloud**: Free tier, then $10/month

---

## Best Practices

1. ✅ **Idempotent processing** - Handle duplicate messages
2. ✅ **Error handling** - Retry with exponential backoff
3. ✅ **Monitoring** - Alert on queue depth, errors
4. ✅ **Dead letter queues** - Don't lose failed messages
5. ✅ **Message schema** - Validate payload structure
6. ✅ **Graceful shutdown** - Finish current tasks before exit

---

## When to Use Which?

### Use RabbitMQ when:
- Task queues (emails, notifications, jobs)
- Need management UI
- Traditional request/response patterns
- Priority queues

### Use Kafka when:
- Event streaming (analytics, logs)
- High throughput (millions/sec)
- Event sourcing
- Multiple consumers per message

### Use Redis when:
- Simple use case
- Already using Redis
- Real-time updates
- Low message volume

---

## Examples

See `examples/` directory:
- `email_worker.py` - Send emails asynchronously
- More examples coming...

---

## Resources

- **RabbitMQ**: https://www.rabbitmq.com/
- **Kafka**: https://kafka.apache.org/
- **Redis Streams**: https://redis.io/docs/data-types/streams/
- **Celery** (task framework): https://docs.celeryq.dev/

---

**Created:** November 16, 2025  
**Status:** Production-Ready  
**Queues:** RabbitMQ, Kafka, Redis
