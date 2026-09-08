
from google import genai
from django.conf import settings
from .tools import get_order_details , get_refund_history , check_delivery_status
from .models import Conversation , Message , AgentLog
from google.genai import types


client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)
gemini_model = settings.GEMINI_MODEL


# Support System Prompt
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
"""




#-------------------

SUPPORT_TOOLS = [
    {
        "name": "get_order_details",
        "description": "Fetch complete order details including status, carrier, tracking number and days since order was placed. Use this when customer mentions their order or complains about delivery.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "The order ID to look up"
                }
            },
            "required": ["order_id"]
        }
    },

    {
        "name": "get_refund_history",
        "description": "Get complete refund history for a user. Use this before making any refund related decisions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "The user ID to check refund history for"
                }
            },
            "required": ["user_id"]
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
]




#-------------------

def execute_tool(tool_name , input_tool):
    if tool_name == "get_order_details" :
        return get_order_details(input_tool["order_id"])
    elif tool_name == "get_refund_history" :
        return get_refund_history(input_tool["user_id"])
    elif tool_name == "check_delivery_status" :
        return check_delivery_status(input_tool["tracking_number"] , input_tool["carrier"])

#-------------------
    
    
def run_support_agent(user_message, conversation_id, order_id, user_id):
    conv = Conversation.objects.get(id=conversation_id)
    conversation_messages = []

    for msg in conv.messages.order_by("created_at"):
        conversation_messages.append(
            types.Content(
                role=msg.role,
                parts=[
                    types.Part.from_text(text=msg.content)
                ],
            )
        )


    while True:

        response = client.models.generate_content(
            model=gemini_model,
            contents=conversation_messages,
            config=types.GenerateContentConfig(
                system_instruction=
                    SUPPORT_SYSTEM_PROMPT +
                    f"\n\nContext: This conversation is about Order #{order_id}, user: {user_id}",
                tools=[
                    types.Tool(
                        function_declarations=[
                            types.FunctionDeclaration(
                                name=tool["name"],
                                description=tool["description"],
                                parameters=tool["input_schema"]
                            )
                            for tool in SUPPORT_TOOLS
                        ]
                    )
                ]
            )
        )


        # اگر Gemini درخواست tool داشت
        if response.function_calls:

            tool_results = []

            for function_call in response.function_calls:

                tool_name = function_call.name
                tool_args = function_call.args

                print("Executing tool:", tool_name)
                print("Arguments:", tool_args)


                result = execute_tool(
                    tool_name,
                    tool_args
                )


                tool_results.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={
                            "result": result
                        }
                    )
                )


            # اضافه کردن درخواست مدل به history
            conversation_messages.append(
                response.candidates[0].content
            )


            # اضافه کردن نتیجه ابزار به history
            conversation_messages.append(
                types.Content(
                    role="user",
                    parts=tool_results
                )
            )


        else:
            return response.text

     

 