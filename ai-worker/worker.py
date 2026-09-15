import json
import os
import sys
sys.path.insert(0, "/backend")
import pika  # type: ignore
import time

from support.events import build_envelope, is_duplicate_event, mark_event_processed # type: ignore




os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "di_ai_employees_main.settings"
)

import django

django.setup()


from django.shortcuts import get_object_or_404
from support.agents import run_support_agent # type: ignore
from support.models import Conversation, Message # type: ignore


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")


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

    if is_duplicate_event(event_id):
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

    conversation = get_object_or_404(Conversation, id=conversation_id)

    reply_message = Message.objects.create(
        conversation=conversation,
        role="model",
        content=reply,
        correlation_id=correlation_id,
    )

    mark_event_processed(event_id, envelope["type"])

    response_envelope = build_envelope(
        event_type="support_response",
        payload={
            "conversation_id": conversation_id,
            "order_id": order_id,
            "user_id": user_id,
            "reply": reply,
            "reply_message_id": reply_message.id
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