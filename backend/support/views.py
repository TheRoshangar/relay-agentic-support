from django.shortcuts import render , get_object_or_404 # type: ignore
from django.http import JsonResponse # type: ignore
from orders.models import Order
from .models import Conversation , Message

import json
import time
import asyncio
from django.http import StreamingHttpResponse

from .events import publish_support_event

from django.contrib.admin.views.decorators import staff_member_required # type: ignore
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework.permissions import IsAuthenticated


from .event_stream import get_events




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat(request, order_id):
    if request.method == 'POST':
        data = request.data
        user_message = data.get("message")

        if not user_message:
            return JsonResponse({"error": "Empty message"}, status=400)
        
        order = get_object_or_404(Order, id=order_id, user=request.user)

        conversation, created = Conversation.objects.get_or_create(
            user=request.user,
            order=order
        )

        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message
        )

        publish_support_event({
        "conversation_id": conversation.id,
        "order_id": order_id,
        "user_id": request.user.id,
        "message": user_message,
        })

        return JsonResponse({
        "status": "processing",
    })

    return JsonResponse({
        "error": "Only POST allowed"
    }, status=405)  


@api_view(["GET"])
def dashboard(request):
    conversations = Conversation.objects.filter(
        user=request.user
    ).order_by("-created_at")

    data = []

    for conversation in conversations:
        data.append({
            "id": conversation.id,
            "user_id": conversation.user_id,
            "order_id": conversation.order_id,
            "created_at": conversation.created_at,
        })

    return Response(data)


@api_view(["GET"])
def conversation_detail(request, conversation_id):

    conversation = get_object_or_404(
    Conversation,
    id=conversation_id,
    user=request.user
    )

    messages = conversation.messages.order_by("created_at")
    agentlogs = conversation.agentlogs.order_by("created_at")

    data = {
        "conversation": {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "order_id": conversation.order_id,
            "created_at": conversation.created_at,
        },
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in messages
        ],
        "agentlogs": [
            {
               "id": log.id,
               "event_type": log.event_type,
               "message": log.message,
               "created_at": log.created_at,
            }
            for log in agentlogs
        ],
    }

    return Response(data)



@staff_member_required
def dashboard_view(request):
    conversations = Conversation.objects.all().order_by("-created_at")
    return render(request, "support/dashboard.html", {
        "conversations": conversations
    })


@staff_member_required
def conversation_detail_view(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    messages = conversation.messages.order_by("created_at")
    agentlogs = conversation.agentlogs.order_by("created_at")
    return render(request, "support/conversation_detail.html", {
        "conversation": conversation,
        "messages": messages,
        "agentlogs": agentlogs,
    })

async def support_events(request):

    user = await request.auser()

    if not user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    print(
        f"SUPPORT EVENTS VIEW CALLED for user {user.id}",
        flush=True
    )

    response = StreamingHttpResponse(
        get_events(user.id),
        content_type="text/event-stream",
    )

    response["Cache-Control"] = "no-cache"

    return response