from django.shortcuts import render , get_object_or_404 # type: ignore
import json
from django.http import JsonResponse # type: ignore
from orders.models import Order
from .models import Conversation , Message
from support.agents import run_support_agent
from django.contrib.admin.views.decorators import staff_member_required # type: ignore

# Create your views here.
def chat(request, order_id):
    if request.method == 'POST':
        data = json.loads(request.body)
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



@staff_member_required
def dashboard(request):
    conversations = Conversation.objects.all().order_by("-created_at")
    context = {
        'conversations' : conversations
    }

    return render(request , "support/dashboard.html" , context)


def conversation_detail(request , conversation_id) :
    conversation = get_object_or_404(Conversation , id=conversation_id)
    messages = conversation.messages.order_by("created_at")
    agentlogs = conversation.agentlogs.order_by("created_at")

    context = {
            'conversations' : conversation,
            'messages' : messages,
            'agentlogs' : agentlogs,
    }
    
    return render(request , "support/conversation_detail.html" , context)



