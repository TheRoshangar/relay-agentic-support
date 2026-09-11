"""
ASGI config for di_ai_employees_main project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'di_ai_employees_main.settings')

django_asgi_app = get_asgi_application()

from support.async_response_consumer import start_consumer  # noqa: E402


async def application(scope, receive, send):

    if scope["type"] == "lifespan":

        while True:

            message = await receive()

            if message["type"] == "lifespan.startup":
                start_consumer()
                await send({"type": "lifespan.startup.complete"})

            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    else:
        await django_asgi_app(scope, receive, send)