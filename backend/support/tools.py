from datetime import timedelta

from orders.models import Order , RefundRequest
from django.utils import timezone
from .tracking_data import DELIVERY_DATA
from .rag import search_knowledge_base as rag_search
from django.conf import settings
from tavily import TavilyClient # type: ignore

def get_order_details(order_id) :
    try:
        order = Order.objects.get(id=order_id)
        return {
            "order_id" : order.id,
            "product_name" : order.product_name,
            "amount" : str(order.amount),
            "status" : order.status,
            "carrier" : order.carrier,
            "tracking_number" : order.tracking_number,
            "delivery_address" : order.delivery,
            "ordered_on" : order.created_at.strftime("%d %b %Y"),
            "days_since_order" : (timezone.now() - order.created_at).days

        }
    except Order.DoesNotExist: 
        return {"error" : f"Order #{order_id} not found."}


def get_refund_history(user_id):
   refunds = RefundRequest.objects.filter(user_id = user_id).order_by("-created_at")

   history = []
   for refund in refunds :
       history.append({
           'order_id': refund.order.id,
           'product' : refund.order.product_name,
           'reason' : refund.reason,
           'status' : refund.status,
           'requested_on' : refund.created_at.strftime("%d %b %Y")
       })
        
   return {
         "total_refund_request" : len(history) ,
         "history" : history,
     }        


def check_delivery_status(tracking_number , carrier) : 

    if not isinstance(tracking_number, str) or not (1 <= len(tracking_number.strip()) <= 40):
        return {"error": "Invalid tracking number."}

    if not isinstance(carrier, str) or not (1 <= len(carrier.strip()) <= 40):
        return {"error": "Invalid carrier."}

    tracking_number = tracking_number.strip()
    carrier = carrier.strip()
    
    default_response = {
        "status": "Unknown",
        "last_location": "Tracking info unavailable",
        "last_update": "N/A",
        "estimated_delivery": "Contact carrier directly",
        "delay_reason": "No updates from carrier",
    }
    result = DELIVERY_DATA.get(tracking_number , default_response)
    result["tracking_number"] = tracking_number
    result["carrier"] = carrier
    return result


def get_customer_risk_profile(user_id):
    refunds = RefundRequest.objects.filter(user_id=user_id)
    orders = Order.objects.filter(user_id=user_id)

    recent_refunds = refunds.filter(created_at__gte = timezone.now() - timedelta(days = 90)).count()

    denied = refunds.filter(status = "denied").count()
    approved = refunds.filter(status = "approved").count()
    pending = refunds.filter(status = "pending").count()


    total_orders = orders.count()
    total_refunds = refunds.count()


    if total_orders > 0 :
        refund_to_order_ratio = round( total_refunds / total_orders, 2)

    else :
        refund_to_order_ratio = 0

    return {
        "user_id": user_id,
        "total_orders": total_orders,
        "total_refund_requests": total_refunds,
        "refunds_last_90_days": recent_refunds,
        "denied_refunds": denied,
        "approved_refunds": approved,
        "pending_refunds": pending,
        "refund_to_order_ratio": refund_to_order_ratio
    }

def search_knowledge_base(query):
    return rag_search(query)


tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)


def search_web(query):
    try:
        response = tavily_client.search(
            query=query,
            max_results=3,
            include_answer=False,
        )
    except Exception as e:
        return {"error": f"Web search failed: {str(e)}"}

    results = []
    for r in response.get("results", []):
        results.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "content": r.get("content"),
        })

    return {
        "source": "web",
        "results": results,
    }
