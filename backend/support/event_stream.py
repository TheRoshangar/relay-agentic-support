import asyncio
import json


# برای SSE چت مشتری — بر اساس user_id
user_listeners = {}

# برای SSE پنل ادمین — بر اساس conversation_id
conversation_listeners = {}


def add_listener(user_id, queue):
    user_listeners.setdefault(user_id, []).append(queue)


def remove_listener(user_id, queue):
    queues = user_listeners.get(user_id)

    if queues and queue in queues:
        queues.remove(queue)

        if not queues:
            del user_listeners[user_id]


def publish_event(event):

    user_id = event.get("user_id")

    print(
        "PUBLISH EVENT CALLED",
        event,
        flush=True
    )

    queues = user_listeners.get(user_id, [])

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
        len(user_listeners.get(user_id, [])),
        flush=True
    )

    try:

        while True:

            event = await queue.get()

            yield f"data: {json.dumps(event)}\n\n"

    finally:

        remove_listener(user_id, queue)


def add_conversation_listener(conversation_id, queue):
    conversation_listeners.setdefault(conversation_id, []).append(queue)


def remove_conversation_listener(conversation_id, queue):
    queues = conversation_listeners.get(conversation_id)

    if queues and queue in queues:
        queues.remove(queue)

        if not queues:
            del conversation_listeners[conversation_id]


def publish_conversation_event(event):

    conversation_id = event.get("conversation_id")

    print(
        "PUBLISH CONVERSATION EVENT CALLED",
        event,
        flush=True
    )

    queues = conversation_listeners.get(conversation_id, [])

    print(
        f"CONVERSATION LISTENERS for conversation {conversation_id}:",
        len(queues),
        flush=True
    )

    for queue in queues:
        queue.put_nowait(event)


async def get_conversation_events(conversation_id):

    queue = asyncio.Queue()

    add_conversation_listener(conversation_id, queue)

    print(
        f"ADMIN SSE CLIENT CONNECTED for conversation {conversation_id}. LISTENERS:",
        len(conversation_listeners.get(conversation_id, [])),
        flush=True
    )

    try:

        while True:

            event = await queue.get()

            yield f"data: {json.dumps(event)}\n\n"

    finally:

        remove_conversation_listener(conversation_id, queue)