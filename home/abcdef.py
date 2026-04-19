

import json
import math
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from groq import Groq
from django.conf import settings


@method_decorator(csrf_exempt, name='dispatch')
class IncidentAnalyzeView(View):
    """
    Core AI incident analysis endpoint.
    Works for both citizens and police officers.
    Role is auto-detected from session.
    """

    def post(self, request):
        try:
            data      = json.loads(request.body)
            text      = data.get('text', '').strip()
            latitude  = data.get('latitude')
            longitude = data.get('longitude')

            if not text:
                return JsonResponse({'error': 'Incident description required'}, status=400)

            # Detect user role
            role = 'citizen'
            user_name = 'Anonymous'
            if request.user.is_authenticated:
                try:
                    from home.models import userProfile
                    profile   = userProfile.objects.get(user=request.user)
                    role      = profile.role or 'citizen'
                    user_name = request.user.get_full_name() or request.user.username
                except Exception:
                    pass

            # Get ward context if coordinates provided
            ward_context = ''
            ward_name    = None
            if latitude and longitude:
                ward_name, ward_context = _get_ward_context(float(latitude), float(longitude))

            # Get recent crime pattern context for this ward
            pattern_context = _get_crime_pattern_context(ward_name)

            # Call Claude for structured analysis
            analysis = _analyze_incident(text, role, ward_context, pattern_context)

            # Find nearest officers if coordinates provided
            nearest_officers = []
            nearest_station  = None
            if latitude and longitude:
                nearest_officers = _get_nearest_officers(float(latitude), float(longitude), limit=3)
                nearest_station  = _get_nearest_station(float(latitude), float(longitude))

            # Auto-alert if severity is high/critical and user is citizen
            alert_sent = False
            if analysis.get('severity') in ('high', 'critical') and role == 'citizen':
                if nearest_officers:
                    alert_sent = _send_incident_alert(
                        nearest_officers[:1],
                        text, analysis, latitude, longitude, user_name
                    )

            return JsonResponse({
                'status':           'success',
                'analysis':         analysis,
                'ward':             ward_name,
                'nearest_officers': nearest_officers,
                'nearest_station':  nearest_station,
                'alert_sent':       alert_sent,
                'timestamp':        timezone.now().strftime('%H:%M:%S'),
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ──────────────────────────────────────────────────────────────
# Claude Analysis
# ──────────────────────────────────────────────────────────────

def _analyze_incident(text, role, ward_context='', pattern_context=''):
    """
    Sends incident text to Claude.
    Returns structured JSON with severity, actions, predictions.
    """

    role_instruction = {
        'citizen': (
            "You are an emergency response AI for Thane Police. "
            "The user is a citizen reporting an incident. "
            "Use simple, calm, reassuring language. "
            "Prioritize their safety first."
        ),
        'police': (
            "You are a tactical intelligence AI for Thane Police officers. "
            "Use precise operational language. "
            "Focus on deployment, escalation risk, and coordination."
        ),
        'sho': (
            "You are a command intelligence AI for the Station Head Officer. "
            "Focus on resource allocation, escalation risk, "
            "and cross-ward coordination."
        ),
    }.get(role, 'citizen')

    prompt = f"""
{role_instruction}

{f"Location context: {ward_context}" if ward_context else ""}
{f"Recent crime patterns: {pattern_context}" if pattern_context else ""}

A user has reported the following incident:
"{text}"

Analyze this incident and respond ONLY with this exact JSON structure:
{{
  "crime_type": "assault / theft / accident / fire / medical / disturbance / other",
  "severity": "low / medium / high / critical",
  "severity_score": 0-10,
  "confidence": 0-100,
  "summary": "one sentence plain summary of the incident",
  "immediate_actions": [
    "action 1 for the user right now",
    "action 2",
    "action 3"
  ],
  "dispatch_recommendation": "what units/resources should be dispatched",
  "escalation_risk": "low / medium / high",
  "escalation_reason": "why escalation risk is this level",
  "safety_tip": "one safety tip specific to this incident type",
  "estimated_response_time": "X-Y minutes",
  "emergency_numbers": ["112", "1091"]
}}

Be concise. No markdown. Valid JSON only.
""".strip()

    client = Groq(api_key=settings.GROQ_API_KEY)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # or mixtral / gemma
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=600,
        temperature=0.2,  # keep low for structured JSON
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback safe response
        return {
            "crime_type":             "other",
            "severity":               "medium",
            "severity_score":         5,
            "confidence":             60,
            "summary":                text[:100],
            "immediate_actions":      ["Call 112 immediately", "Stay safe", "Wait for assistance"],
            "dispatch_recommendation": "Send nearest patrol unit",
            "escalation_risk":        "medium",
            "escalation_reason":      "Unable to fully analyze — manual review required",
            "safety_tip":             "Stay in a safe, visible location",
            "estimated_response_time": "10-15 minutes",
            "emergency_numbers":      ["112", "1091"],
        }


# ──────────────────────────────────────────────────────────────
# Ward + Pattern Context
# ──────────────────────────────────────────────────────────────

def _get_ward_context(lat, lon):
    """Returns (ward_name, context_string) for given coordinates."""
    try:
        from home.models import Ward
        wards = Ward.objects.exclude(centroid_latitude=None, centroid_longitude=None)
        closest, min_dist = None, float('inf')
        for ward in wards:
            d = _haversine(lat, lon, float(ward.centroid_latitude), float(ward.centroid_longitude))
            if d < min_dist:
                min_dist = d
                closest  = ward
        if closest:
            return closest.lgd_name, f"{closest.lgd_name}, {closest.townname}"
        return None, ''
    except Exception:
        return None, ''


def _get_crime_pattern_context(ward_name):
    """Returns recent crime pattern string for the ward."""
    if not ward_name:
        return ''
    try:
        from home.models import CrimeRecord, Ward
        from django.db.models import Count
        import datetime
        ward     = Ward.objects.get(lgd_name=ward_name)
        cutoff   = timezone.now().date() - datetime.timedelta(days=30)
        top      = (CrimeRecord.objects
                    .filter(ward=ward, date_reported__gte=cutoff)
                    .values('crime_type')
                    .annotate(c=Count('id'))
                    .order_by('-c')[:3])
        if top:
            crimes = ', '.join(f"{r['crime_type']}({r['c']})" for r in top)
            return f"Last 30 days in {ward_name}: {crimes}"
    except Exception:
        pass
    return ''


# ──────────────────────────────────────────────────────────────
# Nearest Officers + Station
# ──────────────────────────────────────────────────────────────

def _get_nearest_officers(lat, lon, limit=3):
    """Returns nearest on-duty officers as list of dicts."""
    try:
        from home.models import userProfile
        officers = list(userProfile.objects.filter(
            role='police', is_on_duty=True, is_approved=True,
        ).exclude(current_latitude=None, current_longitude=None))

        for o in officers:
            o._dist = _haversine(lat, lon,
                                 float(o.current_latitude),
                                 float(o.current_longitude))

        officers.sort(key=lambda o: o._dist)
        return [
            {
                'id':           o.id,
                'name':         o.user.get_full_name() or o.user.username,
                'specialty':    o.specialty or 'General',
                'distance_km':  round(o._dist, 2),
                'phone':        o.phone or o.contact or '',
                'latitude':     float(o.current_latitude),
                'longitude':    float(o.current_longitude),
            }
            for o in officers[:limit]
        ]
    except Exception:
        return []


def _get_nearest_station(lat, lon):
    """Returns nearest police station as dict."""
    try:
        from home.models import PoliceStation
        stations = list(PoliceStation.objects.all())
        # PoliceStation may not have coordinates — return first one as fallback
        if stations:
            return {'name': stations[0].name, 'address': stations[0].address or ''}
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────
# Auto-Alert
# ──────────────────────────────────────────────────────────────

def _send_incident_alert(officers, text, analysis, lat, lon, reporter_name):
    """Sends SMS alert to nearest officer for high/critical incidents."""
    try:
        from home.sos_utils import send_sms
        maps_link = f"https://maps.google.com/?q={lat},{lon}" if lat and lon else "Location unavailable"
        severity  = analysis.get('severity', 'unknown').upper()
        crime     = analysis.get('crime_type', 'incident')

        message = (
            f"[{severity} INCIDENT] {crime.title()} reported by {reporter_name}. "
            f"Location: {maps_link}. "
            f"Details: {text[:100]}. "
            f"Action: {analysis.get('dispatch_recommendation', 'Respond immediately')}."
        )

        for officer in officers:
            phone = officer.get('phone', '')
            if phone:
                if not phone.startswith('+'):
                    phone = '+91' + phone.lstrip('0')
                send_sms(phone, message)

        return True
    except Exception as e:
        print(f"[Alert Error] {e}")
        return False


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat/2)**2 +
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
            math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))