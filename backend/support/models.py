from django.db import models # type: ignore
from django.contrib.auth.models import User # type: ignore
from orders.models import Order

# Create your models here.
class Conversation(models.Model):
    user = models.ForeignKey(User , on_delete=models.CASCADE , related_name="conversations")
    order = models.ForeignKey(Order ,  on_delete=models.CASCADE , related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)


    total_input_tokens = models.PositiveIntegerField(default=0)
    total_output_tokens = models.PositiveIntegerField(default=0)
    tavily_calls = models.PositiveIntegerField(default=0)

    GEMINI_INPUT_PRICE_PER_MILLION = 0.30
    GEMINI_OUTPUT_PRICE_PER_MILLION = 2.50
    TAVILY_PRICE_PER_CALL = 0.008  

    @property
    def estimated_cost_usd(self):
        input_cost = (self.total_input_tokens / 1_000_000) * self.GEMINI_INPUT_PRICE_PER_MILLION
        output_cost = (self.total_output_tokens / 1_000_000) * self.GEMINI_OUTPUT_PRICE_PER_MILLION
        tavily_cost = self.tavily_calls * self.TAVILY_PRICE_PER_CALL
        return round(input_cost + output_cost + tavily_cost, 6)


    def __str__(self):
        return f"Conversation #{self.id} - {self.user.username} / Order #{self.order.id}"

    @property
    def manager_involved(self):
        return self.agentlogs.filter(event_type="manager").exists()

    @property
    def risk_assessed(self):
        return self.agentlogs.filter(event_type="risk").exists()

class Message(models.Model): 
    ROLE_CHOICES = [
        ('user' ,'User' ) , 
        ( 'model', 'Model'),
    ]
    conversation = models.ForeignKey(Conversation , on_delete=models.CASCADE , related_name="messages")
    role = models.CharField(max_length=20 , choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class AgentLog(models.Model):
     
     EVENT_CHOICES = [
        ("support", "Support Agent"),
        ("tool_call", "Tool Call"),
        ("tool_result", "Tool Result"),
        ("manager", "Manager Agent"),
        ("risk", "Risk Agent"),
        ("final", "Final Reply"),
    ]
     conversation = models.ForeignKey(Conversation , on_delete=models.CASCADE , related_name="agentlogs")
     event_type = models.CharField(max_length=20 , choices=EVENT_CHOICES)
     message = models.TextField()
     created_at = models.DateTimeField(auto_now_add=True)

     def __str__(self):
      return f"[{self.event_type}] - {self.message[:40]}"

class ProcessedEvent(models.Model):
    event_id = models.UUIDField(unique=True)
    event_type = models.CharField(max_length=50)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} - {self.event_id}"