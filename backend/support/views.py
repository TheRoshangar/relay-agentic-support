from django.shortcuts import render , get_object_or_404 # type: ignore
from django.http import JsonResponse # type: ignore
from orders.models import Order
from .models import Conversation , Message


from django.http import StreamingHttpResponse
from orders.permissions import is_support_agent

from .events import publish_support_event , build_envelope

from django.contrib.admin.views.decorators import staff_member_required # type: ignore
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework.permissions import IsAuthenticated
import os
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required



from .event_stream import get_events, get_conversation_events, publish_conversation_event

from langfuse import get_client # type: ignore
from django.conf import settings

langfuse_client = get_client()

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
        envelope = build_envelope(
            event_type="process_support_message",
            payload={
                "conversation_id": conversation.id,
                "order_id": order_id,
                "user_id": request.user.id,
                "message": user_message,
            },
        )

        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message,
            correlation_id=envelope["correlation_id"],
        )

        publish_conversation_event({
            "type": "user_message",
            "conversation_id": conversation.id,
            "role": "user",
            "content": user_message,
        })

        publish_support_event(envelope)

        return JsonResponse({
        "status": "processing",
        })

    return JsonResponse({
        "error": "Only POST allowed"
    }, status=405)  


@api_view(["GET"])
def dashboard(request):
    if is_support_agent(request.user):
        conversations = Conversation.objects.all().order_by("-created_at")
    else:
        conversations = Conversation.objects.filter(user=request.user).order_by("-created_at")


    data = []

    for conversation in conversations:
        data.append({
            "id": conversation.id,
            "user_id": conversation.user_id,
            "order_id": conversation.order_id,
            "created_at": conversation.created_at,
            "estimated_cost_usd": conversation.estimated_cost_usd,
        })

    return Response(data)


@api_view(["GET"])
def conversation_detail(request, conversation_id):

    if is_support_agent(request.user):
        conversation = get_object_or_404(Conversation, id=conversation_id)
    else:
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)

    messages = conversation.messages.order_by("created_at")
    agentlogs = conversation.agentlogs.order_by("created_at")

    data = {
        "conversation": {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "order_id": conversation.order_id,
            "created_at": conversation.created_at,
            "estimated_cost_usd": conversation.estimated_cost_usd,
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


async def conversation_events(request, conversation_id):

    user = await request.auser()

    if not user.is_authenticated or not user.is_staff:
        return JsonResponse({"error": "Staff authentication required"}, status=401)

    print(
        f"ADMIN CONVERSATION EVENTS VIEW CALLED for conversation {conversation_id}",
        flush=True
    )

    response = StreamingHttpResponse(
        get_conversation_events(conversation_id),
        content_type="text/event-stream",
    )

    response["Cache-Control"] = "no-cache"

    return response

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
    message_id = request.data.get("message_id")
    score = request.data.get("score") 
    comment = request.data.get("comment", "")

    if score not in (1, -1):
        return JsonResponse({"error": "score must be 1 or -1"}, status=400)

    message = get_object_or_404(
        Message,
        id=message_id,
        role="model",
        conversation__user=request.user,
    )

    if not message.correlation_id:
        return JsonResponse({"error": "No trace linked to this message"}, status=400)

    try:
        trace_id = langfuse_client.create_trace_id(seed=message.correlation_id)
        langfuse_client.create_score(
            trace_id=trace_id,
            name="user_feedback",
            value=float(score),
            data_type="NUMERIC",
            comment=comment,
        )
        langfuse_client.flush()
    except Exception as e:
        return JsonResponse({"error": f"Failed to record feedback: {e}"}, status=502)

    return JsonResponse({"status": "recorded"})


DOCUMENTS_DIR = os.path.join(settings.BASE_DIR, "support", "documents")

ALLOWED_DOCUMENTS = {
    "product_faq.pdf",
    "warranty_policy.pdf",
    "refund_policy.pdf",
}


@login_required
def download_document(request, filename):
    if filename not in ALLOWED_DOCUMENTS:
        raise Http404("Document not found")

    file_path = os.path.join(DOCUMENTS_DIR, filename)
    if not os.path.isfile(file_path):
        raise Http404("Document not found")

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )