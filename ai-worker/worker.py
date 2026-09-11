import json
import os
import sys

import pika  # type: ignore


# دسترسی worker به کدهای Django
sys.path.insert(0, "/backend")

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "di_ai_employees_main.settings"
)

import django

django.setup()


from django.shortcuts import get_object_or_404
from support.agents import run_support_agent
from support.models import Conversation, Message


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


def process_event(event):

    print("========== SUPPORT EVENT ==========", flush=True)
    print(event, flush=True)

    conversation_id = event["conversation_id"]
    order_id = event["order_id"]
    user_id = event["user_id"]
    user_message = event["message"]

    reply = run_support_agent(
        user_message,
        conversation_id,
        order_id,
        user_id,
    )

    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
    )

    Message.objects.create(
        conversation=conversation,
        role="model",
        content=reply,
    )

    response_event = {
        "type": "support_response",
        "conversation_id": conversation_id,
        "order_id": order_id,
        "user_id": user_id,
        "reply": reply,
    }

    publish_support_response(response_event)

    print("========== AGENT RESPONSE ==========", flush=True)
    print(reply, flush=True)

    print(
        "========== RESPONSE EVENT PUBLISHED ==========",
        flush=True
    )
    print(response_event, flush=True)


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
        )
    )

    channel = connection.channel()

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
    )

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