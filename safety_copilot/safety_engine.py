from .models import SafetyKnowledge, Helpline


def detect_incident_type(text):
    text = text.lower()

    mapping = {
        "theft": ["stolen", "theft", "snatched", "robbed", "lost phone", "pickpocket"],
        "cyber": ["scam", "fraud", "otp", "hack", "phishing", "bank link"],
        "harassment": ["stalk", "threat", "follow", "harass", "blackmail"],
        "assault": ["attack", "hit", "hurt", "fight", "injured"]
    }

    scores = {}

    for incident, keywords in mapping.items():
        score = 0
        for word in keywords:
            if word in text:
                score += 1
        scores[incident] = score

    best_match = max(scores, key=scores.get)

    if scores[best_match] == 0:
        return "general"

    return best_match



def generate_safety_response(user_text):
    incident = detect_incident_type(user_text)
    urgent = detect_urgency(user_text)

    knowledge = SafetyKnowledge.objects.filter(
        incident_type__icontains=incident
    ).first()

    helplines = Helpline.objects.all()

    response = {
        "incident_detected": incident,
        "urgent": urgent
    }

    if urgent:
        response["emergency_alert"] = "⚠️ You may be in immediate danger. Call 112 right now."

    if knowledge:
        response["immediate_steps"] = knowledge.immediate_steps
        response["evidence"] = knowledge.evidence_to_collect
        response["safety"] = knowledge.safety_measures
    else:
        response["immediate_steps"] = "Contact emergency services if in danger."
        response["evidence"] = "Collect any proof related to the incident."
        response["safety"] = "Stay in a safe location."

    response["helplines"] = list(
        helplines.values("name", "number", "category")
    )
    
    followups = {
        "theft": "Was this online theft or physical theft?",
        "cyber": "Did you already contact your bank?",
        "harassment": "Is the person known to you?",
        "assault": "Are you injured right now?"
    }

    if incident in followups:
        response["followup"] = followups[incident]

    return response


def detect_urgency(text):
    urgent_words = ["bleeding", "weapon", "knife", "gun", "kidnap", "unconscious", "immediate danger"]

    text = text.lower()

    for word in urgent_words:
        if word in text:
            return True

    return False
