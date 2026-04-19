from django.apps import AppConfig


class SafetyCopilotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'safety_copilot'

    def ready(self):
        from .seed_data import seed_database
        try:
            seed_database()
        except:
            pass
