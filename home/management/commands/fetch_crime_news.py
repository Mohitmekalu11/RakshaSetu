import requests
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.conf import settings
from home.models import NewsArticle

NEWS_API_URL = "https://newsapi.org/v2/everything"

CRIME_KEYWORDS = [
    "crime", "murder", "robbery", "assault",
    "theft", "rape", "fraud", "drugs"
]

class Command(BaseCommand):
    help = "Fetch crime-related news articles"

    def handle(self, *args, **kwargs):
        query = " OR ".join(CRIME_KEYWORDS)

        params = {
            "q": f"{query} India",
            "language": "en",
            "sortBy": "publishedAt",
            "apiKey": settings.NEWS_API_KEY,
        }


        response = requests.get(NEWS_API_URL, params=params)
        data = response.json()

        if data.get("status") != "ok":
            self.stderr.write("Failed to fetch news")
            return

        saved = 0

        for article in data["articles"]:
            if not article["title"] or not article["url"]:
                continue

            obj, created = NewsArticle.objects.get_or_create(
                url=article["url"],
                defaults={
                    "title": article["title"],
                    "description": article.get("description", ""),
                    "source": article["source"]["name"],
                    "published_at": parse_datetime(article["publishedAt"]),
                }
            )

            if created:
                saved += 1

        self.stdout.write(self.style.SUCCESS(f"Saved {saved} new articles"))
