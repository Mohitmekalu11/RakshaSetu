import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def parse_user_query(user_query):
    prompt = f"""
You are an AI that converts user queries into structured JSON.

Supported intents:
- safest_areas
- dangerous_areas
- crime_trend

Extract:
- intent
- location
- time (morning, evening, night, or specific hour)
- crime_type (optional)

Return ONLY valid JSON.

User Query: {user_query}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except:
        return {
            "intent": "unknown",
            "location": None,
            "time": None,
            "crime_type": None
        }