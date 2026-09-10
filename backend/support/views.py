from django.shortcuts import render , get_object_or_404 # type: ignore
from django.http import JsonResponse # type: ignore
from orders.models import Order
from .models import Conversation , Message
from support.agents import run_support_agent
from django.contrib.admin.views.decorators import staff_member_required # type: ignore
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["POST"])
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

        reply = run_support_agent(user_message, conversation.id , order_id , request.user.id)

        Message.objects.create(
            conversation=conversation,
            role="model",
            content=reply
        )

        return JsonResponse({
            "reply": reply
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



