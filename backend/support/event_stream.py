import asyncio
import json


listeners = []


def add_listener(queue):
    listeners.append(queue)


def remove_listener(queue):
    if queue in listeners:
        listeners.remove(queue)



def publish_event(event):

    print(
        "PUBLISH EVENT CALLED",
        event,
        flush=True
    )

    print(
        "LISTENERS:",
        len(listeners),
        flush=True
    )

    for queue in listeners:
        queue.put_nowait(event)



async def get_events():

    queue = asyncio.Queue()

    add_listener(queue)

    print(
        "SSE CLIENT CONNECTED. LISTENERS:",
        len(listeners),
        flush=True
    )

    try:

        while True:

            event = await queue.get()

            yield f"data: {json.dumps(event)}\n\n"


    finally:

        remove_listener(queue)