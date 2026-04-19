"""
fetch_news_briefing.py

Run manually:
  python manage.py fetch_news_briefing
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Fetch last 24h Thane crime news and generate SHO briefing'

    def handle(self, *args, **kwargs):
        from home.news_pipeline import run_news_briefing_pipeline

        try:
            result = run_news_briefing_pipeline()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Pipeline crashed: {str(e)}"))
            return

        # Safe extraction (NO KeyError ever again)
        status   = result.get("status", "failed")
        articles = result.get("articles", 0)
        bullets  = result.get("bullets", 0)
        summary  = result.get("summary", "No summary generated.")

        if status == "success":
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Briefing ready\n"
                f"Articles processed: {articles}\n"
                f"Key insights: {bullets}\n"
                f"Summary: {summary}\n"
            ))

        elif status == "no_articles":
            self.stdout.write(self.style.WARNING(
                "\nNo articles found in the last 24 hours.\n"
            ))

        else:
            self.stdout.write(self.style.ERROR(
                "\nPipeline failed or returned invalid response.\n"
                f"Debug Info: {result}\n"
            ))