
from google import genai
from django.conf import settings # type: ignore
from .tools import get_order_details , get_refund_history , check_delivery_status , get_customer_risk_profile , search_knowledge_base , search_web
from .models import Conversation , Message , AgentLog
from google.genai import types

import json
import pika  # type: ignore
from django.db.models import F

from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END # type: ignore



class SupportAgentState(TypedDict):
    messages: Annotated[list, operator.add]
    conversation_id: int
    order_id: int
    user_id: int
    steps: int


MAX_STEPS = 6

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)
gemini_model = settings.GEMINI_MODEL


SUPPORT_SYSTEM_PROMPT = """
You are Maya, a customer support agent at CoolBreeze AC.
You help customers with issues related to their AC orders.

Your responsibilities:
- Always use your tools to gather facts before responding
- Check order details when customer mentions their order
- Check refund history before making any refund decisions
- Be empathetic but honest

Your personality:
- Friendly and professional
- Patient even when customer is angry
- Clear and concise in your replies
- No emojies

Important rules:
- Always check order details first before responding
- Never approve or deny a refund yourself
- If refund decision is needed — tell customer you are checking with your team
- Never use bold text, bullet points or any markdown formatting. Plain text only.
- Keep replies concise and conversational. Maximum 3-4 sentences. No long paragraphs.

Refund escalation rule:
- When a customer requests a refund, first check order details.
- Then check refund history.
- If a refund decision is required, you MUST call escalate_to_manager.
- Do not simply tell the customer that you will check with the team.
- The escalation summary MUST contain the customer user_id, order details, refund history, and complaint.
- After receiving the manager's decision, communicate that decision to the customer.
"""

MANAGER_SYSTEM_PROMPT = """
You are a senior support manager at CoolBreeze AC.
A support agent has escalated a customer case to you for a refund decision.

Your responsibilities:
- Review the case summary carefully
- Consider the customer's refund history
- Make a fair and final refund decision
- Give a clear reason for your decision

Your decision options:
- Approve refund — if the case is genuine and within policy
- Deny refund — if the case is suspicious or outside policy
- Escalate to risk team — if you suspect fraud

Important rules:
- Be fair but firm
- Base decision on facts — not emotions
- Always give a specific reason for your decision
- Keep your response concise and professional
"""

RISK_SYSTEM_PROMPT = """
You are a fraud risk analyst at CoolBreeze AC.
A support manager has sent you a customer profile for risk assessment.

Your job:
- Analyse the customer's order and refund patterns
- Identify suspicious behaviour
- Return a clear risk verdict

Risk levels:
- LOW — genuine customer, normal behaviour
- MEDIUM — some suspicious signals, proceed with caution
- HIGH — clear fraud pattern, recommend denial

Your response format:
- Risk Level: LOW / MEDIUM / HIGH
- Key Signals: what you found suspicious or genuine
- Recommendation: what manager should do

Important:
- Be objective — base verdict on data only
- One bad refund does not make someone fraudulent
- Look for patterns — not isolated incidents
"""
#-------------------

SUPPORT_TOOLS = [
    
    {
    "name": "get_order_details",
    "description": "Fetch complete order details for the customer's order in this conversation, including status, carrier, tracking number and days since order was placed.",
    "input_schema": {
        "type": "object",
        "properties": {}
    }
    },
    {
    "name": "get_refund_history",
    "description": "Get complete refund history for the current authenticated customer. Use this before making any refund related decisions.",
    "input_schema": {
        "type": "object",
        "properties": {}
    }
    },

    {
        "name": "check_delivery_status",
        "description": "Check current delivery status using tracking number and carrier. Use this when customer complains about delayed or missing delivery.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tracking_number": {
                    "type": "string",
                    "description": "The shipment tracking number"
                },
                "carrier": {
                    "type": "string",
                    "description": "The carrier name for example BlueDart or Delhivery"
                }
            },
            "required": ["tracking_number", "carrier"]
        }
    },

    {
        "name": "escalate_to_manager",
        "description": "Escalate the case to manager for refund decision. Always include customer's user_id in the case summary so manager can assess fraud risk accurately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_summary": {
                    "type": "string",
                    "description": "Complete case summary. Must include: customer user_id, order details, refund history and complaint. Format: Start with 'Customer User ID: X' on the first line."
                }
            },
            "required": ["case_summary"]
        }
    },
    {
        "name": "search_knowledge_base",
        "description": "Search CoolBreeze AC company documents including refund policy, warranty policy, and product FAQs. Use this when customer asks about company policies, warranty coverage, warranty claims, refund eligibility, or any general product information that requires accurate company documentation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant information from company documents. Be specific — for example 'refund eligibility within 30 days' instead of just 'refund'."
                }
            },
            "required": ["query"]
        }
    }
     ,
    {
        "name": "search_web",
        "description": "Search the public web for current external information that is not part of the company's own data — for example news, strikes, weather, or general topics outside CoolBreeze AC's orders and policy documents. Do not use this for order status, refund history, or company policy — those must come from the other tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the public web."
                }
            },
            "required": ["query"]
        }
    }
]


MANAGER_TOOLS = [
    {
    "name": "assess_fraud_risk",
    "description": "Consult the risk agent to assess fraud risk for the customer in this case.",
    "input_schema": {
        "type": "object",
        "properties": {}
    }
    }
]

RISK_TOOLS = [
    {
    "name": "get_customer_risk_profile",
    "description": "Get complete risk profile for the customer being assessed, including order history and refund ratio.",
    "input_schema": {
        "type": "object",
        "properties": {}
    }
    }
]
#-------------------

def support_agent_node(state: SupportAgentState):
    response = client.models.generate_content(
        model=gemini_model,
        contents=state["messages"],
        config=types.GenerateContentConfig(
            system_instruction=(
                SUPPORT_SYSTEM_PROMPT
                + f"\n\nContext: This conversation is about Order #{state['order_id']}, user: {state['user_id']}"
            ),
            tools=[
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=tool["name"],
                            description=tool["description"],
                            parameters=tool["input_schema"],
                        )
                        for tool in SUPPORT_TOOLS
                    ]
                )
            ],
        ),
    )
    _record_gemini_usage(state["conversation_id"], response)
    return {
        "messages": [response.candidates[0].content],
        "steps": state["steps"] + 1,
    }


def support_tools_node(state: SupportAgentState):
    conv = Conversation.objects.get(id=state["conversation_id"])
    last_content = state["messages"][-1]

    tool_results = []
    for part in last_content.parts:
        if not part.function_call:
            continue

        tool_name = part.function_call.name
        tool_args = dict(part.function_call.args)

        _create_log(conv, "tool_call", f"Calling tool {tool_name} with {tool_args}")
        result = execute_tool(tool_name, tool_args, state["conversation_id"] , order_id=state["order_id"],user_id=state["user_id"],)
        _create_log(conv, "tool_result", f"{tool_name} returned: {str(result)[:200]}")

        tool_results.append(
            types.Part.from_function_response(
                name=tool_name,
                response={"result": result},
            )
        )

    return {"messages": [types.Content(role="user", parts=tool_results)]}


def support_finalize_node(state: SupportAgentState):
    response = client.models.generate_content(
        model=gemini_model,
        contents=state["messages"] + [
            types.Content(
                role="user",
                parts=[types.Part.from_text(
                    text="You have reached the step limit. Answer the customer now, "
                         "in plain text, using whatever information you already gathered."
                )],
            )
        ],
        config=types.GenerateContentConfig(system_instruction=SUPPORT_SYSTEM_PROMPT),
    )
    _record_gemini_usage(state["conversation_id"], response)
    return {"messages": [response.candidates[0].content]}


def support_should_continue(state: SupportAgentState):
    last_content = state["messages"][-1]
    has_calls = any(part.function_call for part in last_content.parts)

    if not has_calls:
        return "stop"
    if state["steps"] >= MAX_STEPS:
        return "finalize"
    return "tools"



#-------------------

def _publish_agent_log_event(conversation_id, event_type, message):
    """
    Publish an agent log event to the same RabbitMQ fanout exchange used
    for final replies, tagged with type "agent_log" so the async consumer
    on the backend side can route it to the admin panel's SSE stream
    (publish_conversation_event), instead of the customer chat SSE stream.
    """

    credentials = pika.PlainCredentials(
        settings.RABBITMQ_USER,
        settings.RABBITMQ_PASSWORD,
    )

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=600,
        )
    )

    try:
        channel = connection.channel()

        channel.exchange_declare(
            exchange="support_responses",
            exchange_type="fanout",
            durable=True,
        )

        channel.queue_declare(
            queue="support_responses",
            durable=True,
        )

        channel.queue_bind(
            exchange="support_responses",
            queue="support_responses",
        )

        channel.basic_publish(
            exchange="support_responses",
            routing_key="",
            body=json.dumps({
                "type": "agent_log",
                "conversation_id": conversation_id,
                "event_type": event_type,
                "message": message,
            }),
            properties=pika.BasicProperties(
                delivery_mode=2,
            ),
        )

    finally:
        connection.close()


def _create_log(conv, event_type, message):
    """
    Save an AgentLog row (as before) AND publish it live to the admin
    panel via RabbitMQ, so the "Agent Activity" panel updates in
    real time instead of only after a page refresh.
    """

    AgentLog.objects.create(
        conversation=conv,
        event_type=event_type,
        message=message,
    )

    _publish_agent_log_event(conv.id, event_type, message)


def _record_gemini_usage(conversation_id, response):
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return

    input_tokens = getattr(usage, "prompt_token_count", 0) or 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0

    Conversation.objects.filter(id=conversation_id).update(
        total_input_tokens=F("total_input_tokens") + input_tokens,
        total_output_tokens=F("total_output_tokens") + output_tokens,
    )
#-------------------

support_graph_builder = StateGraph(SupportAgentState)
support_graph_builder.add_node("agent", support_agent_node)
support_graph_builder.add_node("tools", support_tools_node)
support_graph_builder.add_node("finalize", support_finalize_node)

support_graph_builder.set_entry_point("agent")
support_graph_builder.add_conditional_edges(
    "agent",
    support_should_continue,
    {"tools": "tools", "finalize": "finalize", "stop": END},
)
support_graph_builder.add_edge("tools", "agent")
support_graph_builder.add_edge("finalize", END)

support_graph = support_graph_builder.compile()
#-------------------

def execute_tool(tool_name, input_tool, conversation_id, order_id=None, user_id=None):
    if tool_name == "get_order_details":
        return get_order_details(order_id)
    elif tool_name == "get_refund_history":
        return get_refund_history(user_id)
    elif tool_name == "check_delivery_status":
        return check_delivery_status(input_tool["tracking_number"], input_tool["carrier"])
    elif tool_name == "escalate_to_manager":
        case_summary = input_tool["case_summary"]
        decision = run_manager_agent(case_summary, conversation_id, user_id)
        return decision
    elif tool_name == "assess_fraud_risk":
        verdict = run_risk_agent(user_id, conversation_id)
        return verdict
    elif tool_name == "get_customer_risk_profile":
        return get_customer_risk_profile(user_id)
    elif tool_name == "search_knowledge_base":
        return search_knowledge_base(input_tool["query"])
    elif tool_name == "search_web":
        return search_web(input_tool["query"] , conversation_id=conversation_id) 
        

#-------------------
    
    
def run_support_agent(user_message, conversation_id, order_id, user_id):
    conv = Conversation.objects.get(id=conversation_id)
    conversation_messages = []

    for msg in conv.messages.order_by("created_at"):
        conversation_messages.append(
            types.Content(role=msg.role, parts=[types.Part.from_text(text=msg.content)])
        )

    final_state = support_graph.invoke({
        "messages": conversation_messages,
        "conversation_id": conversation_id,
        "order_id": order_id,
        "user_id": user_id,
        "steps": 0,
    })

    last_content = final_state["messages"][-1]
    final_reply = "".join(part.text for part in last_content.parts if part.text)

    _create_log(conv, "final", final_reply)
    return final_reply

def run_manager_agent(case_summary , conversation_id , user_id) :

    conv = Conversation.objects.get(id=conversation_id)

    _create_log(conv, "manager", f"Case received for review: {case_summary[:200]}")


    manager_messages = [
    types.Content(
        role="user",
        parts=[
            types.Part.from_text(text=case_summary)
        ]
    )
]

    while True:
    
            response = client.models.generate_content(
                model=gemini_model,
                contents=manager_messages,
                config=types.GenerateContentConfig(
                    system_instruction=
                        MANAGER_SYSTEM_PROMPT,
                    tools=[
                        types.Tool(
                            function_declarations=[
                                types.FunctionDeclaration(
                                    name=tool["name"],
                                    description=tool["description"],
                                    parameters=tool["input_schema"]
                                )
                                for tool in MANAGER_TOOLS
                            ]
                        )
                    ]
                )
            )
            _record_gemini_usage(conversation_id, response)
    
    
   
            if response.function_calls:
    
                tool_results = []
    
                for function_call in response.function_calls:
    
                    tool_name = function_call.name
                    tool_args = function_call.args



                    _create_log(conv, "manager", "Consulting risk agent for fraud assessment...")

                    result = execute_tool(
                        tool_name,
                        tool_args,
                        conversation_id,
                        user_id=user_id,
                    )
    
    
                    tool_results.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={
                                "result": result
                            }
                        )
                    )
    
    
                manager_messages.append(
                    response.candidates[0].content
                )
    
    
          
                manager_messages.append(
                    types.Content(
                        role="user",
                        parts=tool_results
                    )
                )
    
    
            else:
                decision = response.text
                _create_log(conv, "manager", f"Decision: {decision[:200]}")
                return decision

def run_risk_agent(user_id , conversation_id) :

    conv = Conversation.objects.get(id=conversation_id)
    _create_log(conv, "risk", f"Starting fraud assessment for user {user_id}")

    risk_messages = [
    types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text=f"Please assess the fraud risk for user ID {user_id}. Use your tool to get their profile and return a verdict."
            )
        ]
    )
]

    while True:
    
            response = client.models.generate_content(
                model=gemini_model,
                contents=risk_messages,
                config=types.GenerateContentConfig(
                    system_instruction=
                        RISK_SYSTEM_PROMPT,
                    tools=[
                        types.Tool(
                            function_declarations=[
                                types.FunctionDeclaration(
                                    name=tool["name"],
                                    description=tool["description"],
                                    parameters=tool["input_schema"]
                                )
                                for tool in RISK_TOOLS
                            ]
                        )
                    ]
                )
            )

            _record_gemini_usage(conversation_id, response)
   
            if response.function_calls:
    
                tool_results = []
    
                for function_call in response.function_calls:
    
                    tool_name = function_call.name
                    tool_args = function_call.args

                    _create_log(conv, "risk", f"Calling {tool_name} to get customer risk profile...")
    
                    result = execute_tool(
                        tool_name,
                        tool_args,
                        conversation_id,
                        user_id=user_id,
                    )
    
    
                    tool_results.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={
                                "result": result
                            }
                        )
                    )
    
    
                risk_messages.append(
                    response.candidates[0].content
                )
    
    
          
                risk_messages.append(
                    types.Content(
                        role="user",
                        parts=tool_results
                    )
                )
    
    
            else:
                verdict = response.text
                _create_log(conv, "risk", f"Verdict: {verdict[:200]}")
                return verdict