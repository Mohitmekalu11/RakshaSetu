from django.core.management.base import BaseCommand
from home.models import NewsArticle
from home.services.nlp_processor import process_article

class Command(BaseCommand):
    help = "Process unprocessed news articles using NLP"

    def handle(self, *args, **kwargs):
        articles = NewsArticle.objects.filter(is_processed=False)
        count = 0
        for article in articles:
            if process_article(article):
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Processed {count} articles"))
