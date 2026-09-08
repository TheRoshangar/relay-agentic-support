import os
from google import genai
from decouple import config


print(config("GEMINI_API_KEY"))
# ۱. تعریف کلاینت
client = genai.Client(api_key=config("GEMINI_API_KEY"))

# ۲. فراخوانی مدل
model_name = config("GEMINI_MODEL", default="gemini-2.5-flash")

response = client.models.generate_content(
    model=model_name,
    contents="give me 5 animals name"
)

print(response.text)