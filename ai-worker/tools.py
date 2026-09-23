from datetime import datetime, timedelta, timezone as tz

import db
import config
from tracking_data import DELIVERY_DATA
from rag import search_knowledge_base as rag_search
from tavily import TavilyClient  # type: ignore


def get_order_details(order_id):
    order = db.get_order(order_id)
    if order is None:
        return {"error": f"Order #{order_id} not found."}

    return {
        "order_id": order["id"],
        "product_name": order["product_name"],
        "amount": str(order["amount"]),
        "status": order["status"],
        "carrier": order["carrier"],
        "tracking_number": order["tracking_number"],
        "delivery_address": order["delivery"],
        "ordered_on": order["created_at"].strftime("%d %b %Y"),
        "days_since_order": (datetime.now(tz.utc) - order["created_at"]).days,
    }


def get_refund_history(user_id):
    refunds = db.get_refund_history(user_id)

    history = [
        {
            "order_id": r["order_id"],
            "product": r["product_name"],
            "reason": r["reason"],
            "status": r["status"],
            "requested_on": r["created_at"].strftime("%d %b %Y"),
        }
        for r in refunds
    ]

    return {
        "total_refund_request": len(history),
        "history": history,
    }


def check_delivery_status(tracking_number, carrier):

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
    result = DELIVERY_DATA.get(tracking_number, default_response)
    result["tracking_number"] = tracking_number
    result["carrier"] = carrier
    return result


def get_customer_risk_profile(user_id):
    counts = db.get_customer_risk_counts(user_id)

    total_orders = counts["total_orders"]
    total_refunds = counts["total_refunds"]

    if total_orders > 0:
        refund_to_order_ratio = round(total_refunds / total_orders, 2)
    else:
        refund_to_order_ratio = 0

    return {
        "user_id": user_id,
        "total_orders": total_orders,
        "total_refund_requests": total_refunds,
        "refunds_last_90_days": counts["refunds_last_90_days"],
        "denied_refunds": counts["denied_refunds"],
        "approved_refunds": counts["approved_refunds"],
        "pending_refunds": counts["pending_refunds"],
        "refund_to_order_ratio": refund_to_order_ratio,
    }


def search_knowledge_base(query):
    return rag_search(query)


tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)


def search_web(query, conversation_id=None):
    try:
        response = tavily_client.search(
            query=query,
            max_results=3,
            include_answer=False,
        )
    except Exception as e:
        return {"error": f"Web search failed: {str(e)}"}

    if conversation_id:
        db.increment_tavily_calls(conversation_id)

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