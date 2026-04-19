import requests
import json
import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

from groq import Groq

client = Groq(api_key=settings.GROQ_API_KEY)

# ──────────────────────────────────────────────────────────────
# 1. Fetch News
# ──────────────────────────────────────────────────────────────

NEWSDATA_ENDPOINT = "https://newsdata.io/api/1/news"

SEARCH_QUERIES = [
    "Thane crime",
    "Thane police",
    "Thane murder theft robbery",
]


def fetch_thane_news(hours_back=24):
    articles = []
    seen_urls = set()

    for query in SEARCH_QUERIES:
        try:
            params = {
                "apikey": settings.NEWSDATA_API_KEY,
                "q": query,
                "country": "in",
                "language": "en",
                "category": "crime",
            }

            response = requests.get(NEWSDATA_ENDPOINT, params=params, timeout=15)
            data = response.json()

            if data.get("status") != "success":
                continue

            for item in data.get("results", []):
                url = item.get("link", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                pub_str = item.get("pubDate", "")
                try:
                    pub_dt = datetime.strptime(pub_str, "%Y-%m-%d %H:%M:%S")
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)

                    if pub_dt < timezone.now() - timedelta(hours=hours_back):
                        continue
                except:
                    pass

                articles.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "content": item.get("content", ""),
                    "source": item.get("source_id", ""),
                    "author": item.get("creator", [""])[0] if item.get("creator") else "",
                    "url": url,
                    "published_at": pub_str,
                    "city": _extract_city(item),
                })

        except Exception as e:
            print(f"[Fetch ERROR] {e}")

    return articles


def _extract_city(item):
    text = (item.get("title", "") + " " + item.get("description", "")).lower()
    cities = ["thane", "kalyan", "dombivli", "ambernath", "bhiwandi",
              "ulhasnagar", "mira road", "vasai", "navi mumbai"]
    for city in cities:
        if city in text:
            return city.title()
    return "Thane"


# ──────────────────────────────────────────────────────────────
# 2. Save Articles
# ──────────────────────────────────────────────────────────────

def save_articles_to_db(articles):
    from home.models import NewsArticle

    saved = []

    for a in articles:
        try:
            pub_dt = datetime.strptime(a["published_at"], "%Y-%m-%d %H:%M:%S")
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        except:
            pub_dt = timezone.now()

        obj, created = NewsArticle.objects.get_or_create(
            url=a["url"],
            defaults={
                "title": a["title"],
                "description": a["description"],
                "content": a["content"],
                "source": a["source"],
                "author": a["author"],
                "published_at": pub_dt,
                "city": a["city"],
                "country": "India",
                "is_processed": False,
            }
        )

        if created:
            saved.append(obj)

    print(f"[DB] Saved {len(saved)} articles")
    return saved


# ──────────────────────────────────────────────────────────────
# 3. LLaMA Briefing (FIXED VERSION)
# ──────────────────────────────────────────────────────────────

def clean_llama_output(raw):
    """Fix common LLaMA JSON issues"""
    if "```" in raw:
        raw = raw.split("```")[1]
        raw = raw.replace("json", "")

    # Remove trailing commas
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)

    return raw.strip()


def validate_bullets(bullets):
    valid = []
    for b in bullets:
        if all(k in b for k in ["point", "crime_type", "severity", "source_index"]):
            valid.append(b)
    return valid


def generate_sho_briefing(articles):
    if not articles:
        return [], "No news found."

    article_digest = ""
    for i, a in enumerate(articles[:10], 1):
        article_digest += (
            f"{i}. {a.title}\n{a.description}\nURL: {a.url}\n\n"
        )

    prompt = f"""
STRICT:
- Output ONLY JSON
- No explanation
- No markdown
- If unsure return empty bullets

FORMAT:
{{
  "summary": "text",
  "bullets": [
    {{
      "point": "text",
      "crime_type": "type",
      "severity": "low/medium/high/critical",
      "source_index": 1
    }}
  ]
}}

ARTICLES:
{article_digest}
"""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        raw = response.choices[0].message.content.strip()
        raw = clean_llama_output(raw)

        result = json.loads(raw)

        bullets = validate_bullets(result.get("bullets", []))
        summary = result.get("summary", "")

        return bullets, summary

    except Exception as e:
        print("[LLaMA ERROR]", str(e))
        return [], "Failed to generate briefing"


def safe_generate_briefing(articles, retries=2):
    for _ in range(retries):
        bullets, summary = generate_sho_briefing(articles)
        if bullets:
            return bullets, summary
    return [], "Failed after retries"


# ──────────────────────────────────────────────────────────────
# 4. Save Insights
# ──────────────────────────────────────────────────────────────

def save_briefing_to_db(articles, bullets, summary):
    from home.models import IntelligenceInsight, NewsActionInsight

    saved = []

    for i, b in enumerate(bullets):
        idx = b.get("source_index", 1) - 1
        article = articles[idx] if 0 <= idx < len(articles) else articles[0]

        insight = IntelligenceInsight.objects.create(
            article=article,
            trend_type=b.get("crime_type", "other"),
            severity=b.get("severity", "medium"),
            summary=b.get("point", ""),
            baseline_avg=0.0,
            recent_count=1,
        )

        NewsActionInsight.objects.create(
            article=article,
            user_role="sho",
            action_text=b.get("point", ""),
            priority=i + 1,
        )

        saved.append(insight)

    print(f"[DB] Saved {len(saved)} insights")
    return saved


# ──────────────────────────────────────────────────────────────
# 5. Pipeline Runner
# ──────────────────────────────────────────────────────────────

def run_news_briefing_pipeline():
    print("\n=== NEWS PIPELINE START ===")

    raw_articles = fetch_thane_news()
    print(f"Fetched: {len(raw_articles)}")

    if not raw_articles:
        return {"status": "no_articles"}

    save_articles_to_db(raw_articles)

    from home.models import NewsArticle

    articles = list(
        NewsArticle.objects.filter(is_processed=False)
        .order_by('-published_at')[:10]
    )

    bullets, summary = safe_generate_briefing(articles)

    print(f"Bullets: {len(bullets)}")
    print(f"Summary: {summary}")

    save_briefing_to_db(articles, bullets, summary)

    NewsArticle.objects.filter(
        id__in=[a.id for a in articles]
    ).update(is_processed=True)

    print("=== DONE ===\n")

    return {
        "status": "success",
        "bullets": len(bullets),
        "summary": summary,
    }