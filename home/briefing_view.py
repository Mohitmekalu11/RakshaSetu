"""
briefing_view.py

GET /api/sho/briefing/
Returns today's 5-bullet briefing for the SHO dashboard.
Also exposes a manual refresh endpoint.
"""

import json
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta


class SHOBriefingView(View):
    """
    GET /api/sho/briefing/
    Returns today's intelligence bullets for the SHO dashboard.
    """

    def get(self, request):
        from home.models import IntelligenceInsight, NewsActionInsight  # ← change 'home'

        # Get insights from last 24 hours
        since = timezone.now() - timedelta(hours=24)

        insights = IntelligenceInsight.objects.filter(
            generated_at__gte=since
        ).select_related('article').order_by('-generated_at')[:10]

        actions = NewsActionInsight.objects.filter(
            user_role='sho',
            created_at__gte=since,
        ).select_related('article').order_by('priority')[:5]

        # Build response
        bullets = []
        for action in actions:
            insight = insights.filter(article=action.article).first()
            bullets.append({
                "priority":    action.priority,
                "point":       action.action_text,
                "crime_type":  insight.trend_type if insight else "other",
                "severity":    insight.severity   if insight else "medium",
                "source":      action.article.source,
                "source_url":  action.article.url,
                "published_at": action.article.published_at.strftime("%d %b %Y, %H:%M"),
            })

        # Overall summary from most recent insight
        summary = ""
        if insights.exists():
            summary = insights.first().summary

        # Last updated time
        last_updated = None
        if actions.exists():
            last_updated = actions.first().created_at.strftime("%d %b %Y, %H:%M")

        return JsonResponse({
            "bullets":      bullets,
            "summary":      summary,
            "last_updated": last_updated,
            "count":        len(bullets),
        })


@method_decorator(csrf_exempt, name='dispatch')
class RefreshBriefingView(View):
    """
    POST /api/sho/briefing/refresh/
    Manually trigger pipeline from SHO dashboard.
    SHO-only endpoint.
    """

    def post(self, request):
        try:
            # Only SHO can trigger
            from home.models import userProfile  # ← change 'home'
            profile = userProfile.objects.get(user=request.user)
            if profile.role != 'sho':
                return JsonResponse({'error': 'SHO access only'}, status=403)
        except Exception:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        try:
            from home.news_pipeline import run_news_briefing_pipeline  # ← change 'home'
            result = run_news_briefing_pipeline()
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)