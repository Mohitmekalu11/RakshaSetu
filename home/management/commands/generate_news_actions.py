from django.core.management.base import BaseCommand
from home.models import NewsArticle
from home.services.action_engine import generate_actions

class Command(BaseCommand):
    help = "Generate action insights from correlated news articles"

    def handle(self, *args, **kwargs):
        articles = NewsArticle.objects.filter(
            correlation__isnull=False,
            actions__isnull=True
        )

        count = 0
        for article in articles:
            generate_actions(article)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Generated actions for {count} articles")
        )
