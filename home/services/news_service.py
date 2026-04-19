import requests
from django.conf import settings

class ThaneNewsService:

    def fetch_thane_news(self):
        url = "https://newsapi.org/v2/everything"

        params = {
            "q": "crime Thane Maharashtra",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 30,
            "apiKey": settings.NEWS_API_KEY
        }

        response = requests.get(url, params=params)
        data = response.json()
        return data.get("articles", [])
