"""
ASGI config for Skillsphere project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skillsphere.settings')

application = get_asgi_application()

# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from home.consumers import CrimeReportConsumer  # Update the import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skillsphere.settings')  

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/crime-alerts/', CrimeReportConsumer.as_asgi()),
        ])
    ),
})

