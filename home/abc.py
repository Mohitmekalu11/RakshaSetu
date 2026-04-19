"""
views.py — CrimeCast Complete Views
All 12 view classes merged into one file.
Change 'home' to your actual app name throughout.
"""

# ── Dispatch engine (station-based dispatch) ──────────────────────────────────
from home.dispatch_engine import (          # ← change 'home'
    resolve_station,
    pick_officer,
    create_real_alert,
    reassign_alert,
    get_sho_for_station,
    _log_timeline,
)

import json
import math
import datetime
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings

from home.models import (                   # ← change 'home'
    IncidentAlert, IncidentStatus, IncidentTimeline,
    userProfile,                            # your existing user profile model
)


# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

CRITICAL_KEYWORDS = [
    "gun", "pistol", "rifle", "shoot", "shooting", "shot",
    "knife", "stabbed", "stabbing", "blade",
    "blood", "bleeding", "unconscious", "not breathing", "no pulse",
    "fire", "burning", "explosion", "bomb",
    "kidnap", "kidnapping", "abduction",
    "rape", "sexual assault",
    "murder", "killing", "dead body", "corpse",
    "overdose", "suicide", "hanging",
    "acid attack", "mob", "riot",
]

HIGH_KEYWORDS = [
    "fight", "assault", "beating", "attack", "hit", "punch",
    "theft", "robbery", "snatching", "stolen",
    "accident", "crash", "collision", "injured", "injury",
    "fainted", "collapsed",
    "domestic violence", "harassment",
    "drug", "narcotics",
]

CRIME_TYPE_KEYWORDS = {
    "assault":   ["fight", "assault", "beating", "attack", "punch", "hit", "stab", "knife", "weapon"],
    "theft":     ["theft", "robbery", "snatching", "stolen", "pickpocket", "chain snatching"],
    "fire":      ["fire", "burning", "smoke", "flames", "explosion"],
    "medical":   ["unconscious", "not breathing", "heart", "collapsed", "fainted", "overdose", "injured"],
    "kidnapping":["kidnap", "abduction", "missing", "taken"],
    "sexual":    ["rape", "sexual assault", "molestation", "harassment"],
    "accident":  ["accident", "crash", "collision", "vehicle"],
    "narcotics": ["drug", "narcotics", "dealer", "smuggling"],
}

LANDMARK_MAP = {
    "kopri":         "Ward No.21",
    "station road":  "Ward No.1",
    "thane station": "Ward No.1",
    "viviana":       "Ward No.15",
    "korum":         "Ward No.8",
    "upvan":         "Ward No.12",
    "hiranandani":   "Ward No.40",
    "ambernath":     "Ward No.35",
    "kalwa":         "Ward No.28",
    "wagle":         "Ward No.16",
    "charai":        "Ward No.3",
    "ghantali":      "Ward No.7",
    "naupada":       "Ward No.5",
}


# ══════════════════════════════════════════════════════════════
# SAFETY RULES OVERRIDE
# ══════════════════════════════════════════════════════════════

def apply_safety_rules(text, ai_output):
    text_lower = text.lower()
    overridden = False

    if any(k in text_lower for k in CRITICAL_KEYWORDS):
        ai_output["severity"]   = "critical"
        ai_output["confidence"] = max(ai_output.get("confidence", 50), 95)
        ai_output["override"]   = True
        overridden = True
    elif any(k in text_lower for k in HIGH_KEYWORDS):
        if ai_output.get("severity") in ("low", "medium"):
            ai_output["severity"]   = "high"
            ai_output["confidence"] = max(ai_output.get("confidence", 50), 85)
            ai_output["override"]   = True
            overridden = True

    detected_type = _detect_crime_type(text_lower)
    if detected_type and ai_output.get("crime_type") in (None, "other", ""):
        ai_output["crime_type"] = detected_type

    ai_output["rule_override"] = overridden
    return ai_output


def _detect_crime_type(text_lower):
    for crime_type, keywords in CRIME_TYPE_KEYWORDS.items():
        if any(k in text_lower for k in keywords):
            return crime_type
    return None


# ══════════════════════════════════════════════════════════════
# SAFETY SCORE ENGINE
# ══════════════════════════════════════════════════════════════

def compute_safety_score(ward_name, crime_type):
    if not ward_name:
        return 5.0
    try:
        from home.models import CrimeRecord   # ← change 'home'
        cutoff = timezone.now().date() - datetime.timedelta(days=30)
        total = CrimeRecord.objects.filter(
            ward__lgd_name=ward_name, date_reported__gte=cutoff
        ).count()
        if total == 0:
            return 3.0
        type_count = CrimeRecord.objects.filter(
            ward__lgd_name=ward_name,
            crime_type__iexact=crime_type,
            date_reported__gte=cutoff,
        ).count()
        volume_score = min(5.0, (total / 20) * 5)
        type_score   = min(5.0, (type_count / max(total, 1)) * 10)
        return min(10.0, round(volume_score + type_score, 2))
    except Exception as e:
        print(f"[Safety Score Error] {e}")
        return 5.0


def compute_time_risk_factor():
    hour = timezone.now().hour
    if 22 <= hour or hour < 5:
        return 1.4, "night"
    elif 5 <= hour < 8:
        return 1.1, "early_morning"
    elif 18 <= hour < 22:
        return 1.2, "evening"
    return 1.0, "day"


# ══════════════════════════════════════════════════════════════
# LOCATION RESOLUTION
# ══════════════════════════════════════════════════════════════

def resolve_location(latitude, longitude, landmark=None):
    if latitude and longitude:
        ward_name, ward_ctx = _get_ward_from_coords(float(latitude), float(longitude))
        return float(latitude), float(longitude), ward_name, ward_ctx, 'gps'
    if landmark:
        ward_name = _ward_from_landmark(landmark)
        return None, None, ward_name, f"Near {landmark}, Thane", 'landmark'
    return None, None, None, '', 'unknown'


def _ward_from_landmark(landmark):
    lm = landmark.lower()
    for key, ward in LANDMARK_MAP.items():
        if key in lm:
            return ward
    return None


def _get_ward_from_coords(lat, lon):
    try:
        from home.models import Ward   # ← change 'home'
        wards = Ward.objects.exclude(centroid_latitude=None, centroid_longitude=None)
        closest, min_dist = None, float('inf')
        for w in wards:
            d = _haversine(lat, lon, float(w.centroid_latitude), float(w.centroid_longitude))
            if d < min_dist:
                min_dist, closest = d, w
        if closest:
            return closest.lgd_name, f"{closest.lgd_name}, {closest.townname}"
    except Exception:
        pass
    return None, ''


# ══════════════════════════════════════════════════════════════
# ESCALATION PREDICTION
# ══════════════════════════════════════════════════════════════

def predict_escalation(text, ward_name, crime_type, time_factor):
    score, reasons = 0, []
    crowd_words   = ["crowd", "gathering", "mob", "people watching", "group", "bystanders"]
    weapon_words  = ["knife", "gun", "rod", "weapon", "armed", "blade"]
    alcohol_words = ["drunk", "drinking", "alcohol", "intoxicated"]

    if any(w in text.lower() for w in crowd_words):
        score += 25; reasons.append("crowd present")
    if any(w in text.lower() for w in weapon_words):
        score += 35; reasons.append("weapon involved")
    if any(w in text.lower() for w in alcohol_words):
        score += 20; reasons.append("intoxication involved")
    if time_factor >= 1.3:
        score += 15; reasons.append("night-time incident")

    high_esc_types = {"assault": 20, "sexual": 25, "kidnapping": 30, "riot": 35}
    score += high_esc_types.get(crime_type, 5)
    if crime_type in high_esc_types:
        reasons.append(f"{crime_type} type")

    if ward_name:
        try:
            from home.models import CrimeRecord   # ← change 'home'
            cutoff = timezone.now().date() - datetime.timedelta(days=30)
            recent = CrimeRecord.objects.filter(
                ward__lgd_name=ward_name, date_reported__gte=cutoff
            ).count()
            if recent > 10:
                score += 10; reasons.append("high-crime ward")
        except Exception:
            pass

    probability = min(95, score)
    reason_str  = ", ".join(reasons) if reasons else "no major escalation indicators"
    return probability, reason_str


# ══════════════════════════════════════════════════════════════
# AI ANALYSIS
# ══════════════════════════════════════════════════════════════

def analyze_with_groq(text, role, location_str, pattern_context,
                      safety_score, time_label, escalation_prob):
    from groq import Groq

    role_inst = {
        'citizen': "You are a calm emergency assistant for Thane Police. Use simple, reassuring language.",
        'police':  "You are a tactical AI for Thane Police officers. Use precise operational language.",
        'sho':     "You are a command AI for the Station Head Officer. Focus on resource allocation.",
    }.get(role, "You are an emergency assistant for Thane Police.")

    prompt = f"""
{role_inst}

Location: {location_str or "Thane, Maharashtra"}
Area safety score: {safety_score}/10 (higher = more dangerous)
Time of day: {time_label}
Escalation probability: {escalation_prob}%
{f"Recent crime patterns: {pattern_context}" if pattern_context else ""}

Incident reported:
"{text}"

Respond ONLY in this exact JSON (no markdown, no extra text):
{{
  "crime_type": "assault/theft/fire/medical/kidnapping/sexual/accident/narcotics/fraud/other",
  "severity": "low/medium/high/critical",
  "severity_score": 1-10,
  "confidence": 0-100,
  "summary": "one sentence factual summary",
  "immediate_actions": ["action 1", "action 2", "action 3"],
  "dispatch_recommendation": "specific units/resources needed",
  "escalation_prediction": "yes/no",
  "escalation_probability": 0-100,
  "escalation_reason": "specific reason based on incident details",
  "safety_tip": "one practical safety tip",
  "estimated_response_time": "X-Y minutes",
  "emergency_numbers": ["112", "1091"]
}}
""".strip()

    try:
        client   = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[Groq Error] {e}")
        return _fallback_analysis(text)


def _fallback_analysis(text):
    return {
        "crime_type":              _detect_crime_type(text.lower()) or "other",
        "severity":                "high",
        "severity_score":          7,
        "confidence":              60,
        "summary":                 "Incident requires immediate attention. Manual review recommended.",
        "immediate_actions":       ["Call 112 immediately", "Stay in a safe location", "Do not confront the situation alone"],
        "dispatch_recommendation": "Send nearest patrol unit immediately",
        "escalation_prediction":   "yes",
        "escalation_probability":  70,
        "escalation_reason":       "AI analysis unavailable — defaulting to high alert",
        "safety_tip":              "Stay calm and keep a safe distance",
        "estimated_response_time": "10-15 minutes",
        "emergency_numbers":       ["112", "1091"],
    }


# ══════════════════════════════════════════════════════════════
# PATTERN CONTEXT + HAVERSINE
# ══════════════════════════════════════════════════════════════

def _get_pattern_context(ward_name):
    if not ward_name:
        return ''
    try:
        from home.models import CrimeRecord   # ← change 'home'
        from django.db.models import Count
        cutoff = timezone.now().date() - datetime.timedelta(days=30)
        top = (CrimeRecord.objects
               .filter(ward__lgd_name=ward_name, date_reported__gte=cutoff)
               .values('crime_type').annotate(c=Count('id')).order_by('-c')[:3])
        if top:
            return ', '.join(f"{r['crime_type']}({r['c']})" for r in top)
    except Exception:
        pass
    return ''


def _haversine(lat1, lon1, lat2, lon2):
    R  = 6371
    d1 = math.radians(lat2 - lat1)
    d2 = math.radians(lon2 - lon1)
    a  = (math.sin(d1 / 2) ** 2 +
          math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
          math.sin(d2 / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ══════════════════════════════════════════════════════════════
# VIEW 1 — CITIZEN INCIDENT PAGE
# ══════════════════════════════════════════════════════════════

class CitizenIncidentView(TemplateView):
    """
    GET /incident/
    Serves the citizen reporting page. No login required.
    After submit, JS calls /api/incident/analyze/ and redirects to /incident/track/<id>/
    """
    template_name = 'citizen_incident.html'


# ══════════════════════════════════════════════════════════════
# VIEW 2 — CITIZEN TRACK PAGE
# ══════════════════════════════════════════════════════════════

class CitizenTrackView(TemplateView):
    """
    GET /incident/track/<alert_id>/
    Citizen live-tracking page — polls /api/incident/live/ every 5s.
    """
    template_name = 'citizen_track.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        alert_id = self.kwargs.get('alert_id')
        try:
            alert = IncidentAlert.objects.select_related(
                'assigned_officer__user', 'assigned_officer__station', 'station'
            ).get(id=alert_id)
            ctx['alert']      = alert
            ctx['alert_json'] = json.dumps(alert.to_dict())
        except IncidentAlert.DoesNotExist:
            ctx['alert'] = None
        return ctx


# ══════════════════════════════════════════════════════════════
# VIEW 3 — OFFICER DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════

class OfficerDashboardView(TemplateView):
    """
    GET /officer/dashboard/
    Officer incident management panel — polls /api/incident/officer-alerts/ every 5s.
    """
    template_name = 'officer_dashboard.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            profile = userProfile.objects.select_related('station').get(user=self.request.user)
            ctx['officer'] = profile
        except userProfile.DoesNotExist:
            ctx['officer'] = None
        return ctx


# ══════════════════════════════════════════════════════════════
# VIEW 4 — INCIDENT ANALYZE (AI + dispatch)
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class IncidentAnalyzeView(View):
    """
    POST /api/incident/analyze/
    Core endpoint: AI analysis → safety override → station dispatch → alert creation.
    Returns alert_id so citizen JS can redirect to tracking page.
    """

    def post(self, request):
        try:
            data      = json.loads(request.body)
            text      = data.get('text', '').strip()
            latitude  = data.get('latitude')
            longitude = data.get('longitude')
            landmark  = data.get('landmark', '').strip()
            is_panic  = data.get('panic', False)

            if not text:
                if is_panic:
                    text = "Emergency — need immediate help"
                else:
                    return JsonResponse({'error': 'Incident description required'}, status=400)

            # Role detection
            role, user_name = 'citizen', 'Anonymous'
            if request.user.is_authenticated:
                try:
                    p         = userProfile.objects.get(user=request.user)
                    role      = p.role or 'citizen'
                    user_name = request.user.get_full_name() or request.user.username
                except Exception:
                    pass

            # Location
            lat, lon, ward_name, location_str, loc_method = resolve_location(
                latitude, longitude, landmark
            )

            # Time risk
            time_factor, time_label = compute_time_risk_factor()

            # Pattern context from DB
            pattern_context = _get_pattern_context(ward_name)

            # Pre-compute escalation (heuristic — no LLM needed)
            detected_type = _detect_crime_type(text.lower())
            esc_prob, _   = predict_escalation(text, ward_name, detected_type or 'other', time_factor)

            # Pre-compute safety score
            safety_score = compute_safety_score(ward_name, detected_type or 'other')

            # AI analysis
            analysis = analyze_with_groq(
                text, role, location_str, pattern_context,
                safety_score, time_label, esc_prob
            )

            # Safety rules override — always runs last, non-negotiable
            analysis = apply_safety_rules(text, analysis)

            # Inject real data scores
            analysis['area_risk_score']        = safety_score
            analysis['time_risk']              = time_label
            analysis['time_factor']            = time_factor
            analysis['location_method']        = loc_method
            analysis['escalation_probability'] = max(
                analysis.get('escalation_probability', 0), esc_prob
            )

            # Station-based dispatch
            station = resolve_station(ward_name, landmark)
            officer = pick_officer(
                station=station,
                crime_type=analysis.get('crime_type', 'other')
            )

            # Create DB alert + send SMS
            alert_id, alert_sent = create_real_alert(
                request, text, analysis, lat, lon,
                ward_name, landmark, station, officer, user_name
            )

            # Officer info for frontend
            officer_info = []
            if officer:
                officer_info = [{
                    'id':          officer.id,
                    'name':        officer.user.get_full_name() or officer.user.username,
                    'specialty':   officer.specialty or 'General',
                    'experience':  getattr(officer, 'experience_level', 'Junior') or 'Junior',
                    'station':     station.name if station else 'Unknown',
                    'phone':       officer.phone or getattr(officer, 'contact', '') or '',
                    'distance_km': 'N/A',
                    'rank_score':  'Assigned by station',
                }]

            nearest_station = {
                'name':    station.name    if station else 'Unknown',
                'address': station.address if station else '',
            } if station else None

            return JsonResponse({
                'status':           'success',
                'analysis':         analysis,
                'alert_id':         alert_id,           # ← JS uses this to redirect
                'ward':             ward_name,
                'station':          station.name if station else None,
                'location_method':  loc_method,
                'nearest_officers': officer_info,
                'nearest_station':  nearest_station,
                'alert_sent':       alert_sent,
                'officer_assigned': (officer.user.get_full_name() if officer else None),
                'timestamp':        timezone.now().strftime('%H:%M:%S'),
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 5 — OFFICER ACKNOWLEDGE (accept / reject from notification widget)
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class IncidentAcknowledgeView(View):
    """POST /api/incident/acknowledge/"""

    def post(self, request):
        try:
            data     = json.loads(request.body)
            alert_id = data.get('alert_id')
            action   = data.get('action')

            if action not in ('accept', 'reject'):
                return JsonResponse({'error': 'action must be accept or reject'}, status=400)

            alert = IncidentAlert.objects.get(id=alert_id)

            if alert.status != IncidentStatus.PENDING:
                return JsonResponse({'message': 'Alert already handled', 'status': alert.status})

            if action == 'accept':
                alert.status       = IncidentStatus.ACCEPTED
                alert.accepted_at  = timezone.now()
                alert.responded_at = timezone.now()
                alert.save()
                _log_timeline(alert, IncidentStatus.ACCEPTED, note='Officer accepted via notification.')
                _notify_citizen_status(alert, IncidentStatus.ACCEPTED)
                return JsonResponse({
                    'status':   'accepted',
                    'message':  'You are now assigned to this incident. Navigate to location.',
                    'maps_url': alert.maps_url,
                })
            else:
                alert.status       = IncidentStatus.REJECTED
                alert.responded_at = timezone.now()
                alert.save()
                _log_timeline(alert, IncidentStatus.REJECTED, note='Officer rejected via notification.')
                reassigned = reassign_alert(alert)
                return JsonResponse({
                    'status':     'rejected',
                    'message':    'Alert rejected.',
                    'reassigned': reassigned,
                })

        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 6 — PENDING ALERTS (polled by officer notification widget)
# ══════════════════════════════════════════════════════════════

class PendingAlertsView(View):
    """GET /api/incident/pending/"""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        try:
            profile = userProfile.objects.select_related('station').get(user=request.user)

            alerts = IncidentAlert.objects.filter(
                assigned_officer=profile,
                status__in=[IncidentStatus.PENDING, IncidentStatus.ACCEPTED],
            ).order_by('-created_at')[:10]

            result = []
            for a in alerts:
                if a.status == IncidentStatus.PENDING and a.is_expired():
                    a.status = IncidentStatus.REJECTED
                    a.save(update_fields=['status'])
                    _log_timeline(a, IncidentStatus.REJECTED,
                                  note='Auto-expired: no response within 30 seconds')
                    reassign_alert(a)
                    continue
                result.append({
                    **a.to_dict(),
                    'seconds_ago':    a.elapsed_seconds,
                    'sho_escalated':  a.status == IncidentStatus.ESCALATED,
                    'station':        (a.assigned_officer.station.name
                                       if a.assigned_officer and a.assigned_officer.station
                                       else 'Unknown'),
                })

            return JsonResponse({'alerts': result, 'count': len(result)})

        except userProfile.DoesNotExist:
            return JsonResponse({'alerts': [], 'count': 0})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 7 — RESOLVE + OFFICER FEEDBACK
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class ResolveAlertView(View):
    """POST /api/incident/resolve/"""

    def post(self, request):
        try:
            data     = json.loads(request.body)
            alert_id = data.get('alert_id')
            alert    = IncidentAlert.objects.get(id=alert_id)

            alert.status               = IncidentStatus.RESOLVED
            alert.resolved_at          = timezone.now()
            alert.ai_correct           = data.get('ai_correct')
            alert.actual_severity      = data.get('actual_severity', '')
            alert.actual_response_time = data.get('response_time_minutes')
            alert.compute_metrics()

            if alert.assigned_officer:
                alert.assigned_officer.active_case_count = max(
                    0, alert.assigned_officer.active_case_count - 1
                )
                alert.assigned_officer.save(update_fields=['active_case_count'])

            alert.save()
            _log_timeline(alert, IncidentStatus.RESOLVED,
                          actor=request.user if request.user.is_authenticated else None,
                          note=data.get('note', 'Incident resolved.'))
            _notify_citizen_status(alert, IncidentStatus.RESOLVED)

            return JsonResponse({'status': 'resolved', 'message': 'Incident resolved. Feedback recorded.'})

        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 8 — UPDATE STATUS (officer dashboard action buttons)
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class UpdateStatusView(View):
    """POST /api/incident/update-status/"""

    def post(self, request):
        try:
            data       = json.loads(request.body)
            alert_id   = data.get('alert_id')
            new_status = data.get('status', '').strip()
            note       = data.get('note', '').strip()

            if not alert_id or not new_status:
                return JsonResponse({'error': 'alert_id and status are required'}, status=400)

            if new_status not in dict(IncidentStatus.CHOICES):
                return JsonResponse({'error': f'Invalid status: {new_status}'}, status=400)

            alert = IncidentAlert.objects.select_related(
                'assigned_officer__user', 'station'
            ).get(id=alert_id)

            # Auth check
            if request.user.is_authenticated:
                try:
                    profile = userProfile.objects.get(user=request.user)
                    if alert.assigned_officer and alert.assigned_officer.id != profile.id:
                        if not (profile.role == 'sho' and alert.is_escalated):
                            return JsonResponse({'error': 'Not authorised'}, status=403)
                except userProfile.DoesNotExist:
                    return JsonResponse({'error': 'Officer profile not found'}, status=403)

            # Transition validation
            current = alert.status
            if not IncidentStatus.can_transition(current, new_status):
                return JsonResponse({
                    'error':   f'Invalid transition: {current} → {new_status}',
                    'allowed': IncidentStatus.VALID_TRANSITIONS.get(current, []),
                }, status=400)

            alert.status = new_status
            alert.set_status_timestamp(new_status)

            if new_status == IncidentStatus.RESOLVED:
                alert.compute_metrics()
                if alert.assigned_officer:
                    alert.assigned_officer.active_case_count = max(
                        0, alert.assigned_officer.active_case_count - 1
                    )
                    alert.assigned_officer.save(update_fields=['active_case_count'])

            alert.save()

            default_notes = {
                IncidentStatus.ACCEPTED: 'Officer accepted the incident.',
                IncidentStatus.ENROUTE:  'Officer is en route to the location.',
                IncidentStatus.ARRIVED:  'Officer has arrived at the scene.',
                IncidentStatus.RESOLVED: 'Incident has been resolved.',
                IncidentStatus.REJECTED: 'Officer rejected the incident.',
            }
            actor = request.user if request.user.is_authenticated else None
            _log_timeline(alert, new_status, actor=actor,
                          note=note or default_notes.get(new_status, ''))

            if new_status == IncidentStatus.REJECTED:
                reassign_alert(alert)

            _notify_citizen_status(alert, new_status)

            return JsonResponse({
                'status':       'ok',
                'alert':        alert.to_dict(),
                'transitioned': f'{current} → {new_status}',
            })

        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 9 — LIVE STATUS (citizen tracking page polls this)
# ══════════════════════════════════════════════════════════════

class LiveStatusView(View):
    """GET /api/incident/live/<alert_id>/"""

    def get(self, request, alert_id):
        try:
            alert = IncidentAlert.objects.select_related(
                'assigned_officer__user', 'assigned_officer__station', 'station'
            ).get(id=alert_id)
            return JsonResponse({'ok': True, 'alert': alert.to_dict()})
        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 10 — TIMELINE (citizen tracking page polls this)
# ══════════════════════════════════════════════════════════════

class TimelineView(View):
    """GET /api/incident/timeline/<alert_id>/"""

    def get(self, request, alert_id):
        try:
            alert   = IncidentAlert.objects.get(id=alert_id)
            entries = IncidentTimeline.objects.filter(alert=alert).select_related('actor')
            return JsonResponse({
                'alert_id': alert_id,
                'status':   alert.status,
                'timeline': [e.to_dict() for e in entries],
            })
        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 11 — OFFICER ALERTS (officer dashboard polls this)
# ══════════════════════════════════════════════════════════════

class OfficerAlertsView(View):
    """GET /api/incident/officer-alerts/"""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)

        try:
            profile = userProfile.objects.select_related('station').get(user=request.user)

            alerts = IncidentAlert.objects.filter(
                assigned_officer=profile,
                status__in=[
                    IncidentStatus.PENDING,
                    IncidentStatus.ACCEPTED,
                    IncidentStatus.ENROUTE,
                    IncidentStatus.ARRIVED,
                ],
            ).select_related('station').order_by('-created_at')[:20]

            result = []
            for a in alerts:
                if a.status == IncidentStatus.PENDING and a.is_expired():
                    a.status = IncidentStatus.REJECTED
                    a.save(update_fields=['status'])
                    _log_timeline(a, IncidentStatus.REJECTED,
                                  note='Auto-expired: no officer response within 30 seconds')
                    reassign_alert(a)
                    continue

                result.append({
                    **a.to_dict(),
                    'seconds_ago':           a.elapsed_seconds,
                    'is_expired':            a.is_expired(),
                    'allowed_transitions':   IncidentStatus.VALID_TRANSITIONS.get(a.status, []),
                })

            return JsonResponse({'alerts': result, 'count': len(result)})

        except userProfile.DoesNotExist:
            return JsonResponse({'alerts': [], 'count': 0})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# VIEW 12 — CITIZEN FEEDBACK
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class CitizenFeedbackView(View):
    """POST /api/incident/feedback/"""

    def post(self, request):
        try:
            data     = json.loads(request.body)
            alert_id = data.get('alert_id')
            alert    = IncidentAlert.objects.get(id=alert_id)

            if data.get('rating'):
                alert.citizen_rating = min(5, max(1, int(data['rating'])))
            if data.get('feedback_text'):
                alert.citizen_feedback = data['feedback_text'][:500]
            if 'ai_correct' in data:
                alert.ai_correct = bool(data['ai_correct'])
            if data.get('actual_severity'):
                alert.actual_severity = data['actual_severity']

            alert.save()
            return JsonResponse({'status': 'ok', 'message': 'Feedback recorded. Thank you.'})

        except IncidentAlert.DoesNotExist:
            return JsonResponse({'error': 'Alert not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════

def _notify_citizen_status(alert, new_status):
    """SMS citizen on key lifecycle transitions."""
    try:
        if not alert.reported_by:
            return
        profile = userProfile.objects.filter(user=alert.reported_by).first()
        phone   = profile.phone if profile else ''
        if not phone:
            return
        if not phone.startswith('+'):
            phone = '+91' + phone.lstrip('0')

        messages = {
            IncidentStatus.ACCEPTED: (
                f"[CrimeCast] Officer {alert.assigned_officer.full_name if alert.assigned_officer else ''} "
                f"has accepted your report #{alert.id}."
            ),
            IncidentStatus.ENROUTE: (
                f"[CrimeCast] Officer is on the way. Stay safe. Report #{alert.id}."
            ),
            IncidentStatus.ARRIVED: (
                f"[CrimeCast] Officer has arrived at the scene. Report #{alert.id}."
            ),
            IncidentStatus.RESOLVED: (
                f"[CrimeCast] Incident #{alert.id} resolved. "
                f"Please rate your experience at your tracking page."
            ),
        }
        msg = messages.get(new_status)
        if not msg:
            return

        from home.sos_utils import send_sms   # ← change 'home'
        send_sms(phone, msg)
    except Exception as e:
        print(f"[_notify_citizen_status] {e}")