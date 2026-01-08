"""
Message Queue Worker - Consume and process messages
Supports: Kafka, RabbitMQ, Redis Streams
"""
import os
import json
import time
import signal
import sys

# Configuration
QUEUE_TYPE = os.getenv("QUEUE_TYPE", "rabbitmq")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:password@localhost:5672/")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Graceful shutdown
shutdown_flag = False

def signal_handler(sig, frame):
    global shutdown_flag
    print("\nShutdown signal received, finishing current tasks...")
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def process_message(payload: dict):
    """
    Process message - CUSTOMIZE THIS FOR YOUR USE CASE
    
    Examples:
    - Send email
    - Process image
    - Call external API
    - Update database
    """
    print(f"Processing message: {payload}")
    
    # Simulate work
    time.sleep(1)
    
    print(f"✓ Completed: {payload.get('id', 'unknown')}")
    return True

def consume_kafka():
    """Consume messages from Kafka"""
    from confluent_kafka import Consumer, KafkaError
    
    consumer = Consumer({
        "bootstrap.servers": KAFKA_BOOTSTRAP,
        "group.id": "worker-group",
        "auto.offset.reset": "earliest"
    })
    
    # Subscribe to topics
    topics = os.getenv("KAFKA_TOPICS", "tasks").split(",")
    consumer.subscribe(topics)
    
    print(f"Kafka worker started, listening to topics: {topics}")
    
    try:
        while not shutdown_flag:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Error: {msg.error()}")
                continue
            
            # Process message
            try:
                payload = json.loads(msg.value().decode("utf-8"))
                process_message(payload)
            except Exception as e:
                print(f"Error processing message: {e}")
    
    finally:
        consumer.close()
        print("Kafka consumer closed")

def consume_rabbitmq():
    """Consume messages from RabbitMQ"""
    import pika
    
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    
    # Declare queue
    queue_name = os.getenv("RABBITMQ_QUEUE", "tasks")
    channel.queue_declare(queue=queue_name, durable=True)
    
    # Fair dispatch - don't overwhelm workers
    channel.basic_qos(prefetch_count=1)
    
    print(f"RabbitMQ worker started, listening to queue: {queue_name}")
    
    def callback(ch, method, properties, body):
        try:
            payload = json.loads(body.decode("utf-8"))
            success = process_message(payload)
            
            if success:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        except Exception as e:
            print(f"Error processing message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    
    try:
        while not shutdown_flag:
            connection.process_data_events(time_limit=1)
    finally:
        channel.close()
        connection.close()
        print("RabbitMQ consumer closed")

def consume_redis():
    """Consume messages from Redis Stream"""
    import redis
    
    client = redis.from_url(REDIS_URL)
    stream_name = os.getenv("REDIS_STREAM", "tasks")
    consumer_group = "worker-group"
    consumer_name = f"worker-{os.getpid()}"
    
    # Create consumer group (idempotent)
    try:
        client.xgroup_create(stream_name, consumer_group, id="0", mkstream=True)
    except redis.exceptions.ResponseError:
        pass  # Group already exists
    
    print(f"Redis worker started, listening to stream: {stream_name}")
    
    try:
        while not shutdown_flag:
            # Read messages from stream
            messages = client.xreadgroup(
                consumer_group,
                consumer_name,
                {stream_name: ">"},
                count=10,
                block=1000
            )
            
            for stream, msgs in messages:
                for msg_id, data in msgs:
                    try:
                        payload = json.loads(data[b"payload"].decode("utf-8"))
                        success = process_message(payload)
                        
                        if success:
                            # Acknowledge message
                            client.xack(stream_name, consumer_group, msg_id)
                    except Exception as e:
                        print(f"Error processing message: {e}")
    
    finally:
        client.close()
        print("Redis consumer closed")

def main():
    """Start worker based on QUEUE_TYPE"""
    print(f"Starting worker with queue type: {QUEUE_TYPE}")
    
    try:
        if QUEUE_TYPE == "kafka":
            consume_kafka()
        elif QUEUE_TYPE == "rabbitmq":
            consume_rabbitmq()
        elif QUEUE_TYPE == "redis":
            consume_redis()
        else:
            print(f"Unknown queue type: {QUEUE_TYPE}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nWorker stopped by user")
    except Exception as e:
        print(f"Worker error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
