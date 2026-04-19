from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import json

from .models import IPCSection, SafetyGuideline, ChatLog
from .utils import predict_intent, calculate_severity


@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    data = json.loads(request.body)
    message = data.get("message", "").strip()

    if not message:
        return JsonResponse({"error": "Message cannot be empty"}, status=400)

    # -----------------------------
    # STEP 1: Context Memory
    # -----------------------------
    original_message = message  # preserve clean input

    if request.user.is_authenticated:
        last_chat = ChatLog.objects.filter(user=request.user).order_by("-created_at").first()
        if last_chat:
            context_message = last_chat.message + " " + message
        else:
            context_message = message
    else:
        context_message = message

    intent = predict_intent(context_message).strip().upper()

    # IMPORTANT: severity only on fresh message
    severity = calculate_severity(original_message)

    # Default fallback response (ALWAYS exists)
    response_text = (
        "I'm here to assist with:\n\n"
        "• IPC legal information\n"
        "• Personal safety guidance\n"
        "• Complaint filing steps\n"
        "• Emergency assistance\n\n"
        "Please clearly describe what happened."
    )

    # -----------------------------
    # STEP 3: Emergency Override
    # -----------------------------
    if severity >= 0.9 and intent != "CHECK_IPC":
        intent = "EMERGENCY"


    # -----------------------------
    # STEP 4: Intent Routing
    # -----------------------------

    if intent == "CHECK_IPC":

        best_match = None
        highest_score = 0

        for section in IPCSection.objects.all():
            keywords = [k.strip().lower() for k in section.keywords.split(",")]
            score = sum(1 for keyword in keywords if keyword in message.lower())

            if score > highest_score:
                highest_score = score
                best_match = section

        if best_match:
            response_text = (
                f"🔹 IPC Section {best_match.section_number}: {best_match.title}\n\n"
                f"{best_match.description}\n\n"
                f"⚖ Punishment: {best_match.punishment}"
            )
        else:
            response_text = "No strongly matching IPC section found. Please provide more details."

    elif intent == "SAFETY_ADVICE":

        matched = False

        for rule in SafetyGuideline.objects.all():
            if rule.category.lower() in message.lower():
                response_text = rule.advice
                matched = True
                break

        if not matched:
            response_text = (
                "Ensure you are in a safe public place.\n"
                "Contact trusted persons.\n"
                "Call 112 immediately if you feel unsafe."
            )

    elif intent == "HOW_TO_COMPLAIN":

        response_text = (
            "To file a complaint:\n\n"
            "1. Visit nearest police station or official online portal.\n"
            "2. Provide complete details of the incident.\n"
            "3. Submit any evidence (messages, photos, recordings).\n"
            "4. Request a copy of the FIR for your records.\n\n"
            "Emergency Helpline: 112\n"
            "Women Helpline: 181"
        )

    elif intent == "EMERGENCY":

        response_text = (
            "⚠ You appear to be in immediate danger.\n\n"
            "Call 112 immediately.\n"
            "Move to a safe public location.\n"
            "Inform trusted contacts."
        )

    elif intent == "AREA_SAFETY":

        response_text = (
            "Area safety analytics will provide crime trends and safety ratings "
            "based on historical incident data."
        )

    elif intent == "REPORT_INCIDENT":

        response_text = (
            "Your situation may require formal reporting.\n\n"
            "Would you like assistance in filing a complaint?\n"
            "You can proceed to submit details securely through the platform."
        )

    # -----------------------------
    # STEP 5: Moderate Severity Warning
    # -----------------------------
    if 0.7 <= severity < 0.9:
        response_text = (
            "⚠ This situation appears serious.\n\n"
            "Please consider contacting authorities immediately.\n"
            "Emergency Helpline: 112\n"
            "Women Helpline: 181\n\n"
        ) + response_text

    # -----------------------------
    # STEP 6: Log Conversation
    # -----------------------------
    if request.user.is_authenticated:
        ChatLog.objects.create(
            user=request.user,
            message=message,
            intent=intent,
            response=response_text,
            severity_score=severity
        )

    # -----------------------------
    # STEP 7: Return Response
    # -----------------------------
    return JsonResponse({
        "intent": intent,
        "severity": severity,
        "response": response_text
    })


def chat_page(request):
    return render(request, "chatbot/chat.html")
