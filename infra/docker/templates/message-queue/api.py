"""
Producer API - Send messages to queues
Supports: Kafka, RabbitMQ, Redis Streams
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import os
import json

app = FastAPI(title="Message Queue Producer API", version="1.0.0")

# Queue configuration
QUEUE_TYPE = os.getenv("QUEUE_TYPE", "rabbitmq")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:password@localhost:5672/")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Lazy-load clients
_kafka_producer = None
_rabbitmq_connection = None
_redis_client = None

def get_kafka_producer():
    global _kafka_producer
    if _kafka_producer is None:
        from confluent_kafka import Producer
        _kafka_producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
    return _kafka_producer

def get_rabbitmq_connection():
    global _rabbitmq_connection
    if _rabbitmq_connection is None:
        import pika
        params = pika.URLParameters(RABBITMQ_URL)
        _rabbitmq_connection = pika.BlockingConnection(params)
    return _rabbitmq_connection

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        import redis
        _redis_client = redis.from_url(REDIS_URL)
    return _redis_client

# Request models
class Message(BaseModel):
    topic: str  # Kafka topic / RabbitMQ queue / Redis stream
    payload: dict
    queue_type: Optional[Literal["kafka", "rabbitmq", "redis"]] = None

@app.get("/")
async def root():
    return {
        "service": "Message Queue Producer API",
        "queue_type": QUEUE_TYPE,
        "endpoints": {
            "POST /send": "Send message to queue",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "queue_type": QUEUE_TYPE}

@app.post("/send")
async def send_message(message: Message):
    """Send message to configured queue"""
    queue_type = message.queue_type or QUEUE_TYPE
    
    try:
        if queue_type == "kafka":
            return await send_to_kafka(message)
        elif queue_type == "rabbitmq":
            return await send_to_rabbitmq(message)
        elif queue_type == "redis":
            return await send_to_redis(message)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown queue type: {queue_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def send_to_kafka(message: Message):
    """Send message to Kafka topic"""
    producer = get_kafka_producer()
    
    # Serialize payload
    value = json.dumps(message.payload).encode("utf-8")
    
    # Send message
    producer.produce(
        topic=message.topic,
        value=value,
        callback=lambda err, msg: print(f"Delivered to {msg.topic()}" if not err else f"Error: {err}")
    )
    producer.flush()
    
    return {
        "status": "sent",
        "queue_type": "kafka",
        "topic": message.topic,
        "message_id": None  # Kafka doesn't return message ID synchronously
    }

async def send_to_rabbitmq(message: Message):
    """Send message to RabbitMQ queue"""
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Declare queue (idempotent)
    channel.queue_declare(queue=message.topic, durable=True)
    
    # Serialize payload
    body = json.dumps(message.payload).encode("utf-8")
    
    # Send message
    channel.basic_publish(
        exchange="",
        routing_key=message.topic,
        body=body,
        properties=pika.BasicProperties(delivery_mode=2)  # Persistent
    )
    
    return {
        "status": "sent",
        "queue_type": "rabbitmq",
        "queue": message.topic,
        "message_id": None
    }

async def send_to_redis(message: Message):
    """Send message to Redis Stream"""
    client = get_redis_client()
    
    # Add to stream
    message_id = client.xadd(
        message.topic,
        {"payload": json.dumps(message.payload)}
    )
    
    return {
        "status": "sent",
        "queue_type": "redis",
        "stream": message.topic,
        "message_id": message_id.decode("utf-8")
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
