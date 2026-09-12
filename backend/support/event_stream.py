import asyncio
import json


listeners = {}


def add_listener(user_id, queue):
    listeners.setdefault(user_id, []).append(queue)


def remove_listener(user_id, queue):
    queues = listeners.get(user_id)

    if queues and queue in queues:
        queues.remove(queue)

        if not queues:
            del listeners[user_id]


def publish_event(event):

    user_id = event.get("user_id")

    print(
        "PUBLISH EVENT CALLED",
        event,
        flush=True
    )

    queues = listeners.get(user_id, [])

    print(
        f"LISTENERS for user {user_id}:",
        len(queues),
        flush=True
    )

    for queue in queues:
        queue.put_nowait(event)


async def get_events(user_id):

    queue = asyncio.Queue()

    add_listener(user_id, queue)

    print(
        f"SSE CLIENT CONNECTED for user {user_id}. LISTENERS:",
        len(listeners.get(user_id, [])),
        flush=True
    )

    try:

        while True:

            event = await queue.get()

            yield f"data: {json.dumps(event)}\n\n"

    finally:

        remove_listener(user_id, queue)
