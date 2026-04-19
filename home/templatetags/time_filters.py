from django import template
from django.utils.timezone import now

register = template.Library()

@register.filter
def time_ago(value):
    if not value:
        return ""

    diff = now() - value

    seconds = diff.total_seconds()

    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    elif seconds < 86400:
        return f"{int(seconds // 3600)} hours ago"
    else:
        return f"{int(seconds // 86400)} days ago"