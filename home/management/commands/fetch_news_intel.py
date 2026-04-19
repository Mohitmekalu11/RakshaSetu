import requests
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from home.models import NewsIntel
from home.services.ai_service import analyze_news


class Command(BaseCommand):
    help = "Fetch and store only valid crime news"

    # 🔥 STRONG CRIME FILTER (refined)
    CRIME_KEYWORDS = [
        "murder", "killed", "kill", "robbery", "theft",
        "fraud", "scam", "rape", "assault", "attack",
        "arrested", "arrest", "police", "crime branch",
        "extortion", "cyber crime", "hacking",
        "shooting", "stabbing", "gang", "loot",
        "smuggling", "narcotics", "drugs", "accused",
        "case registered", "FIR", "investigation"
    ]

    # 🚫 explicit junk blockers (IMPORTANT FIX)
    BLOCKLIST = [
        "review",
        "movie",
        "film",
        "trailer",
        "box office",
        "entertainment",
        "celebrity",
        "song",
        "music",
        "sport",
        "match report",
        "analysis of",
        "opinion"
    ]

    def is_valid_crime_news(self, text):
        text = text.lower()

        # ❌ BLOCK NON-CRIME CONTENT FIRST
        if any(word in text for word in self.BLOCKLIST):
            return False

        # ✅ MUST contain at least 1 strong crime indicator
        return any(word in text for word in self.CRIME_KEYWORDS)

    # 🔥 LOCATION (simple but stable)
    def extract_location(self, text):
        text = text.lower()

        if "thane" in text:
            return "Thane"
        if "navi mumbai" in text:
            return "Navi Mumbai"
        if "mumbai" in text:
            return "Mumbai"
        if "maharashtra" in text:
            return "Maharashtra"

        return "Unknown"

    # 🔥 PRIORITY SCORE
    def get_priority_score(self, crime_type, risk_level):
        score = 0

        if risk_level == "HIGH":
            score += 50
        elif risk_level == "MEDIUM":
            score += 30

        weights = {
            "Murder": 50,
            "Attempted Murder": 45,
            "Extortion": 35,
            "Robbery": 30,
            "Fraud": 20,
            "Cyber Crime": 25,
            "Espionage": 20
        }

        return score + weights.get(crime_type, 10)

    def handle(self, *args, **kwargs):

        print("🚀 Fetching news...")

        url = f"https://newsapi.org/v2/everything?q=crime+mumbai+thane&apiKey={settings.NEWS_API_KEY}"

        try:
            res = requests.get(url, timeout=10)
            data = res.json()
        except Exception as e:
            print("❌ API failed:", e)
            return

        if data.get("status") != "ok":
            print("❌ API Error:", data)
            return

        articles = data.get("articles", [])[:20]

        for article in articles:

            title = article.get("title") or ""
            description = article.get("description") or ""

            text = f"{title} {description}".strip()

            print(f"\n📰 Processing: {title}")

            # 🔥 HARD FILTER (IMPORTANT)
            if not self.is_valid_crime_news(text):
                print("⛔ Skipped (not crime-related)")
                continue

            location = self.extract_location(text)

            url = article.get("url", "")

            if NewsIntel.objects.filter(url=url).exists():
                print("⚠️ Duplicate skipped")
                continue

            try:
                ai_output = analyze_news(title, description)

                if not ai_output:
                    print("⛔ AI failed")
                    continue

                cleaned = ai_output.strip().replace("```json", "").replace("```", "")

                parsed = json.loads(cleaned)

                crime_type = parsed.get("crime_type", "Unknown").title()
                risk_level = parsed.get("risk_level", "LOW").upper()

                suggested_action = parsed.get("suggested_action", "")

                # 🔥 FIX weak AI actions
                if any(x in suggested_action.lower() for x in ["investigate", "review", "analyze"]):
                    suggested_action = "Deploy patrol units and increase surveillance"

                priority_score = self.get_priority_score(crime_type, risk_level)

                NewsIntel.objects.get_or_create(
                    url=url,
                    defaults={
                        "title": title,
                        "source": article.get("source", {}).get("name", ""),
                        "location": location,
                        "crime_type": crime_type,
                        "summary": parsed.get("summary", ""),
                        "insight": parsed.get("insight", ""),
                        "impact": parsed.get("impact", ""),
                        "description": description,
                        "content": article.get("content", ""),
                        "author": article.get("author", ""),
                        "image_url": article.get("urlToImage", ""),
                        "published_at": article.get("publishedAt"),
                        "risk_level": risk_level,
                        "suggested_action": suggested_action,
                        "priority_score": priority_score,
                        "threat_escalation": parsed.get("threat_escalation", "no"),
                        "similar_pattern_keywords": parsed.get("similar_pattern_keywords", []),
                    }
                )

                print(f"✅ Saved (Priority: {priority_score})")

            except Exception as e:
                print("❌ Error:", e)

        print("\n🎯 Done")