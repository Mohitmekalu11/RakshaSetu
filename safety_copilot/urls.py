from django.urls import path
from .views import *

urlpatterns = [
    path("", copilot_ui), 
    path("chat/", safety_chat),
]
