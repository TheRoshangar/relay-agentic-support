import json
import pika # type: ignore
from django.conf import settings
import uuid
from datetime import datetime, timezone as dt_timezone

EVENT_VERSION = 1

def build_envelope(event_type, payload, correlation_id=None):
    
    envelope = {
        "event_id": str(uuid.uuid4()),
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "type": event_type,
        "version": EVENT_VERSION,
        "timestamp": datetime.now(dt_timezone.utc).isoformat(),
    }
    envelope.update(payload)
    return envelope


def is_duplicate_event(event_id):
    from .models import ProcessedEvent
    return ProcessedEvent.objects.filter(event_id=event_id).exists()


def mark_event_processed(event_id, event_type):
    from .models import ProcessedEvent
    ProcessedEvent.objects.get_or_create(
        event_id=event_id,
        defaults={"event_type": event_type},
    )


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