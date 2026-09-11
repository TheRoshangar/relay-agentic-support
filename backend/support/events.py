import json
import pika # type: ignore
from django.conf import settings


def publish_support_event(event_data):

    credentials = pika.PlainCredentials(
        settings.RABBITMQ_USER,
        settings.RABBITMQ_PASSWORD,
    )

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
        )
    )

    try:
        channel = connection.channel()

        channel.queue_declare(
            queue="support_events",
            durable=True,
        )

        channel.basic_publish(
            exchange="",
            routing_key="support_events",
            body=json.dumps(event_data),
            properties=pika.BasicProperties(
                delivery_mode=2,
            ),
        )
    finally:
        connection.close()