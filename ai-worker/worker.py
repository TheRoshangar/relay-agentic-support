import json
import time
import uuid
from datetime import datetime, timezone as tz

import pika  # type: ignore

import config
import db
from agents import run_support_agent  # type: ignore


EVENT_VERSION = 1


def build_envelope(event_type, payload, correlation_id=None):
    envelope = {
        "event_id": str(uuid.uuid4()),
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "type": event_type,
        "version": EVENT_VERSION,
        "timestamp": datetime.now(tz.utc).isoformat(),
    }
    envelope.update(payload)
    return envelope


RABBITMQ_HOST = config.RABBITMQ_HOST
RABBITMQ_PORT = config.RABBITMQ_PORT
RABBITMQ_USER = config.RABBITMQ_USER
RABBITMQ_PASSWORD = config.RABBITMQ_PASSWORD


QUEUE_NAME = "support_events"
RESPONSE_QUEUE_NAME = "support_responses"


def publish_support_response(event_data):

    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD,
    )

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=600,
        )
    )

    try:
        channel = connection.channel()

        channel.exchange_declare(
        exchange="support_responses",
        exchange_type="fanout",
        durable=True,
        )

        channel.queue_declare(
        queue=RESPONSE_QUEUE_NAME,
        durable=True,
        )

        channel.queue_bind(
        exchange="support_responses",
        queue=RESPONSE_QUEUE_NAME,
        )

        channel.basic_publish(
        exchange="support_responses",
        routing_key="",
        body=json.dumps(event_data),
        properties=pika.BasicProperties(
        delivery_mode=2,
        ),
    )

    finally:
        connection.close()

DLX_NAME = "support_events_dlx"
DLQ_NAME = "support_events_dlq"


def declare_events_queue(channel):

    channel.exchange_declare(
        exchange=DLX_NAME,
        exchange_type="fanout",
        durable=True,
    )
    channel.queue_declare(
        queue=DLQ_NAME,
        durable=True,
    )
    channel.queue_bind(
        exchange=DLX_NAME,
        queue=DLQ_NAME,
    )

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
        arguments={"x-dead-letter-exchange": DLX_NAME},
    )

MAX_RETRIES = 3
BASE_DELAY = 2


def process_event(envelope):
    event_id = envelope["event_id"]
    correlation_id = envelope["correlation_id"]

    if db.is_duplicate_event(event_id):
        print(f"Skipping duplicate event {event_id}", flush=True)
        return

    print("========== SUPPORT EVENT ==========", flush=True)
    print(envelope, flush=True)

    conversation_id = envelope["conversation_id"]
    order_id = envelope["order_id"]
    user_id = envelope["user_id"]
    user_message = envelope["message"]

    attempt = 0
    while True:
        try:
            reply = run_support_agent(
                user_message,
                conversation_id,
                order_id,
                user_id,
                correlation_id,
            )
            break
        except Exception as e:
            attempt += 1
            if attempt > MAX_RETRIES:
                print(f"Giving up on event {event_id} after {attempt} attempts: {e}", flush=True)
                raise
            delay = BASE_DELAY * (2 ** (attempt - 1))
            print(f"Attempt {attempt} failed ({e}), retrying in {delay}s", flush=True)
            time.sleep(delay)

    db.get_conversation(conversation_id)

    reply_message_id = db.insert_message(
        conversation_id=conversation_id,
        role="model",
        content=reply,
        correlation_id=correlation_id,
    )

    db.mark_event_processed(event_id, envelope["type"])

    response_envelope = build_envelope(
        event_type="support_response",
        payload={
            "conversation_id": conversation_id,
            "order_id": order_id,
            "user_id": user_id,
            "reply": reply,
            "reply_message_id": reply_message_id
        },
        correlation_id=correlation_id,
    )

    publish_support_response(response_envelope)

    print("========== AGENT RESPONSE ==========", flush=True)
    print(reply, flush=True)

    print("========== RESPONSE EVENT PUBLISHED ==========", flush=True)
    print(response_envelope, flush=True)

def callback(ch, method, properties, body):

    try:
        event = json.loads(body)

        process_event(event)

        ch.basic_ack(
            delivery_tag=method.delivery_tag
        )

    except Exception as e:

        print(
            f"Worker error: {e}",
            flush=True
        )

        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )


def main():

    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD,
    )

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=600,
        )
    )

    channel = connection.channel()

    declare_events_queue(channel)

    channel.basic_qos(
        prefetch_count=1
    )

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback,
    )

    print(
        "ai-worker started. Waiting for support events...",
        flush=True
    )

    channel.start_consuming()


if __name__ == "__main__":
    main()