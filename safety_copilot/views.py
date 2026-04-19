from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .safety_engine import generate_safety_response


@api_view(["POST"])
def safety_chat(request):

    message = request.data.get("message", "")

    result = generate_safety_response(message)

    return Response(result)

# UI PAGE
def copilot_ui(request):
    return render(request, "copilot.html")