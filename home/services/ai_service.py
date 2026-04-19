"""
home/services/ai_service.py
Groq-powered news intelligence analysis.
5 layers: classification → risk → insight → directive → prediction
"""

import json
from groq import Groq
from django.conf import settings


def analyze_news(title: str, description: str) -> str:
    """
    Single-call Groq analysis. Returns raw JSON string.
    Called by the fetch_news_intel management command.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    prompt = f"""
You are an elite law enforcement intelligence analyst for Thane District Police, Maharashtra.

Analyze this news article and return ONLY a JSON object — no markdown, no explanation.

Article title: {title}
Article description: {description}

Return this exact JSON:
{{
  "crime_type": "one of: Murder / Attempted Murder / Robbery / Theft / Fraud / Cyber Crime / Narcotics / Sexual Assault / Extortion / Kidnapping / Riot / Terrorism / Other",
  "risk_level": "HIGH or MEDIUM or LOW",
  "summary": "3-sentence tactical briefing for police commander. What happened, where, current status.",
  "insight": "One sharp strategic intelligence observation — pattern, modus operandi, or threat vector. Max 2 sentences.",
  "impact": "Operational impact on Thane district — HIGH / MEDIUM / LOW with one-line reason.",
  "suggested_action": "Specific, actionable field directive for officers. Start with a verb. E.g. Deploy two patrol units to...",
  "threat_escalation": "yes or no — is this likely to escalate in 48 hours?",
  "similar_pattern_keywords": ["keyword1", "keyword2", "keyword3"]
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Groq Error] {e}")
        return None


def generate_threat_brief(top_alerts: list, patterns: list, trends: list) -> str:
    """
    Called by the SHO dashboard API.
    Generates a 60-word AI situation report from current intelligence.
    Returns plain text — no JSON.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    alert_summaries = "\n".join([
        f"- [{a['risk_level']}] {a['crime_type']} in {a['location']}: {a['summary'][:80]}"
        for a in top_alerts[:3]
    ])
    pattern_text = ", ".join([
        f"{p['crime_type']} rising in {p['location']} ({p['count']} incidents)"
        for p in patterns[:3]
    ]) or "No patterns detected"

    trend_text = ", ".join([
        f"{t['crime_type']} in {t['location']} is {t['trend']}"
        for t in trends[:3]
    ]) or "No trend data"

    prompt = f"""
You are the AI intelligence officer for Thane Police.
Write a 60-word situation report (SITREP) for the Station Head Officer.
Tone: urgent, precise, military-style briefing.

Current intelligence:
{alert_summaries}

Patterns: {pattern_text}
Trends: {trend_text}

Write ONLY the SITREP text. No headers, no labels. Start with the most critical threat.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[SITREP Error] {e}")
        return "Intelligence feed unavailable. Manual review required."


def generate_ask_intel(question: str, context_alerts: list) -> str:
    """
    Natural language Q&A against the current intel feed.
    Called by the /ask-intel/ API endpoint.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    context = "\n".join([
        f"- [{a.risk_level}] {a.crime_type} in {a.location}: {a.summary}"
        for a in context_alerts[:8]
    ])

    prompt = f"""
You are an AI intelligence analyst for Thane District Police.
Answer the officer's question using ONLY the intelligence below.
Be direct, tactical, and concise (max 3 sentences).
If the answer is not in the intelligence, say "No data available in current feed."

Current Intelligence Feed:
{context}

Officer's Question: {question}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[AskIntel Error] {e}")
        return "Analysis engine unavailable. Please try again."


def generate_prediction(crime_type: str, location: str, recent_count: int) -> dict:
    """
    48-hour predictive threat assessment for a specific crime/location pair.
    Returns dict with probability, reasoning, recommended_units.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    prompt = f"""
You are a predictive crime analyst for Thane Police.
Based on the data below, assess the 48-hour threat level.

Crime type: {crime_type}
Location: {location}
Incidents in last 24h: {recent_count}

Return ONLY this JSON:
{{
  "probability": 0-100,
  "reasoning": "one sentence why",
  "recommended_units": 1-5,
  "recommended_action": "specific patrol directive"
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[Prediction Error] {e}")
        return {
            "probability": 50,
            "reasoning": "Insufficient data for analysis.",
            "recommended_units": 2,
            "recommended_action": "Maintain standard patrol coverage."
        }