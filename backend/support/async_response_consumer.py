import asyncio
import json

import aio_pika
from django.conf import settings

from .event_stream import publish_event


RESPONSE_QUEUE_NAME = "support_responses"
EXCHANGE_NAME = "support_responses"

_consumer_task = None


async def _consume():

    rabbitmq_url = (
        f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}"
        f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
    )

    while True:

        try:
            connection = await aio_pika.connect_robust(rabbitmq_url)

            async with connection:

                channel = await connection.channel()

                await channel.set_qos(prefetch_count=10)

                exchange = await channel.declare_exchange(
                    EXCHANGE_NAME,
                    aio_pika.ExchangeType.FANOUT,
                    durable=True,
                )

                queue = await channel.declare_queue(
                    RESPONSE_QUEUE_NAME,
                    durable=True,
                )

                await queue.bind(exchange)

                print(
                    "ASYNC RESPONSE CONSUMER STARTED. "
                    "Waiting for support responses...",
                    flush=True,
                )

                async with queue.iterator() as queue_iter:

                    async for message in queue_iter:

                        async with message.process():

                            event = json.loads(message.body)

                            print(
                                "========== SSE RELAY: SUPPORT RESPONSE ==========",
                                flush=True,
                            )
                            print(event, flush=True)

                            publish_event(event)

        except Exception as e:

            print(
                f"ASYNC RESPONSE CONSUMER ERROR: {e}. Retrying in 5s...",
                flush=True,
            )

            await asyncio.sleep(5)


def start_consumer():

    global _consumer_task

    if _consumer_task is None:
        loop = asyncio.get_event_loop()
        _consumer_task = loop.create_task(_consume())