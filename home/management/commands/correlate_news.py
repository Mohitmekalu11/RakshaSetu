from django.core.management.base import BaseCommand
from home.models import NewsArticle
from home.services.correlation_engine import compute_correlation

class Command(BaseCommand):
    help = "Correlate processed news with crime data & predictions"

    def handle(self, *args, **kwargs):
        articles = NewsArticle.objects.filter(
            is_processed=True,
            correlation__isnull=True
        )

        count = 0
        for article in articles:
            if article.city:
                compute_correlation(article)
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Correlated {count} articles")
        )
