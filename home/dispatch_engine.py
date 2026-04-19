"""
dispatch_engine.py — Station-based dispatch logic
Place in your app directory: home/dispatch_engine.py
All functions referenced by views.py
"""

from math import radians, sin, cos, sqrt, atan2
from .models import IncidentStatus, IncidentAlert, IncidentTimeline
from django.utils import timezone


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))


def resolve_station(ward_name=None, landmark=None, lat=None, lon=None):
    from .models import PoliceStation

    # 🚨 HARD REQUIREMENT
    if lat is None or lon is None:
        print("[resolve_station] Missing lat/lon → cannot resolve station")
        return None

    stations = PoliceStation.objects.exclude(latitude=None).exclude(longitude=None)

    nearest = None
    min_dist = float('inf')

    for s in stations:
        dist = haversine(lat, lon, s.latitude, s.longitude)

        if dist < min_dist:
            min_dist = dist
            nearest = s

    print(f"[resolve_station] Nearest: {nearest.name if nearest else None} ({min_dist:.2f} km)")
    return nearest

def pick_nearest_officer(lat, lon, crime_type):
    from .models import userProfile
    from django.utils import timezone
    from datetime import timedelta

    STALE_LIMIT = timezone.now() - timedelta(seconds=30)

    candidates = userProfile.objects.filter(
        role='police',
        is_on_duty=True,
        is_approved=True,
        active_case_count__lt=5,
        last_location_update__gte=STALE_LIMIT
    )

    

    preferred = SPECIALTY_MAP.get(crime_type, ["General", "Patrol"])

    best = None
    best_score = -999

    for officer in candidates:
        o_lat = float(officer.current_latitude)
        o_lon = float(officer.current_longitude)

        dist = haversine(lat, lon, o_lat, o_lon)

        # 🔥 SCORING MODEL
        score = 0

        # Distance (closer = higher score)
        score += max(0, 10 - dist)  # within ~10km range

        # Specialty
        if officer.specialty and any(s.lower() in officer.specialty.lower() for s in preferred[:2]):
            score += 5
        elif officer.specialty and any(s.lower() in officer.specialty.lower() for s in preferred):
            score += 2

        # Workload
        score += max(0, 3 - officer.active_case_count)

        # Seniority
        score += SENIORITY_SCORE.get(officer.seniority, 0) * 0.3

        if score > best_score:
            best_score = score
            best = officer

    print(f"[pick_nearest_officer] Selected: {best.full_name if best else None}")
    return best

# ── Officer selection ─────────────────────────────────────────────────────────

SPECIALTY_MAP = {
    "assault":   ["Assault", "Crime", "Patrol", "General"],
    "theft":     ["Theft",   "Crime", "Patrol", "General"],
    "fire":      ["General", "Patrol"],
    "medical":   ["General", "Patrol"],
    "kidnapping":["Crime",   "Assault", "General"],
    "sexual":    ["Crime",   "Assault", "General"],
    "accident":  ["General", "Patrol",  "Crime"],
    "narcotics": ["Narcotics","Crime",  "General"],
    "cyber":     ["Cyber Crime","Crime","General"],
    "fraud":     ["Fraud",   "Crime",   "General"],
}

SENIORITY_SCORE = {
    'constable':      1,
    'head_constable': 2,
    'asi':            3,
    'si':             4,
    'inspector':      5,
    'dsp':            6,
}


def pick_officer(station, crime_type):
    """
    Returns the best available userProfile from the given station.
    Scoring: specialty match (+5), seniority (+0-3), low workload (+0-3).
    """
    if not station:
        return None

    try:
        from .models import userProfile
        candidates = userProfile.objects.filter(
            station=station,
            role='police',
            is_on_duty=True,
            is_approved=True,
        ).select_related('user')

        preferred = SPECIALTY_MAP.get(crime_type, ["General", "Patrol"])
        best, best_score = None, -999

        for officer in candidates:
            if not officer.is_available:
                continue

            score = 0.0
            # Specialty match
            if officer.specialty and any(s.lower() in officer.specialty.lower() for s in preferred[:2]):
                score += 5.0
            elif officer.specialty and any(s.lower() in officer.specialty.lower() for s in preferred):
                score += 2.0
            # Seniority
            score += SENIORITY_SCORE.get(officer.seniority, 0) * 0.5
            # Workload (fewer active cases = better)
            score += max(0, 3.0 - officer.active_case_count)

            if score > best_score:
                best_score = score
                best = officer

        return best

    except Exception as e:
        print(f"[pick_officer] {e}")
        return None


def get_sho_for_station(station):
    """Returns the SHO (Station Head Officer) for the given station."""
    if not station:
        return None
    try:
        from .models import userProfile
        return userProfile.objects.filter(
            station=station, role='sho', is_approved=True
        ).select_related('user').first()
    except Exception as e:
        print(f"[get_sho_for_station] {e}")
        return None


# ── Alert creation ────────────────────────────────────────────────────────────

def create_real_alert(request, text, analysis, lat, lon,
                      ward_name, landmark, station, officer, user_name):
    """
    Creates IncidentAlert + first timeline entry + sends SMS to officer.
    Returns (alert_id, alert_sent).

    """
    
    if officer and officer.role == 'sho':
        status = IncidentStatus.ESCALATED
    elif officer:
        status = IncidentStatus.PENDING
    else:
        status = IncidentStatus.ESCALATED
        
    try:
        alert = IncidentAlert.objects.create(
            reported_by             = request.user if request.user.is_authenticated else None,
            reporter_name           = user_name,
            incident_text           = text,
            crime_type              = analysis.get('crime_type', ''),
            severity                = analysis.get('severity', 'medium'),
            severity_score          = analysis.get('severity_score', 5),
            summary                 = analysis.get('summary', ''),
            dispatch_recommendation = analysis.get('dispatch_recommendation', ''),
            ai_confidence           = analysis.get('confidence', 0),
            escalation_probability  = analysis.get('escalation_probability', 0),
            escalation_reason       = analysis.get('escalation_reason', ''),
            area_risk_score         = analysis.get('area_risk_score', 5),
            latitude                = lat,
            longitude               = lon,
            ward                    = ward_name or '',
            landmark                = landmark or '',
            station                 = station,
            assigned_officer        = officer,
            status                  = status,
        )

        if station:
            sho = get_sho_for_station(station)
            if sho:
                alert.escalated_to = sho
                if status == IncidentStatus.ESCALATED:
                    alert.is_escalated = True
                alert.save(update_fields=['escalated_to', 'is_escalated'])
        
        # Log creation in timeline
        _log_timeline(alert, IncidentStatus.PENDING, actor=None,
                      note=f"Incident reported by {user_name}. Assigned to "
                           f"{officer.full_name if officer else 'unassigned'}.")

        # Increment officer workload
        if officer:
            officer.active_case_count = max(0, officer.active_case_count) + 1
            officer.save(update_fields=['active_case_count'])

        # Send SMS for high/critical
        alert_sent = False
        if analysis.get('severity') in ('high', 'critical') and officer:
            alert_sent = _send_officer_sms(officer, alert, text, analysis)
        
        print("==== ALERT DEBUG ====")
        print("Station:", station.name if station else None)
        print("Officer:", officer.user.username if officer else None)
        print("Officer Role:", officer.role if officer else None)
        print("Status:", status)
        print("=====================")

        return alert.id, alert_sent

    except Exception as e:
        print(f"[create_real_alert] {e}")
        return None, False


# ── Reassignment ──────────────────────────────────────────────────────────────

def reassign_alert(alert):
    """
    Tries to assign the next best available officer from the same station.
    If no officer available, escalates to SHO.
    Returns True if reassigned, False if escalated/failed.
    """
    try:
        station = alert.station
        if not station:
            return False

        # Exclude current officer
        current_id = alert.assigned_officer.id if alert.assigned_officer else None

        from .models import userProfile
        candidates = userProfile.objects.filter(
            station=station, role='police',
            is_on_duty=True, is_approved=True,
        ).exclude(id=current_id).select_related('user')

        preferred = SPECIALTY_MAP.get(alert.crime_type, ["General", "Patrol"])
        best, best_score = None, -999

        for officer in candidates:
            if not officer.is_available:
                continue
            score = 0.0
            if officer.specialty and any(s.lower() in officer.specialty.lower() for s in preferred):
                score += 5.0
            score += max(0, 3.0 - officer.active_case_count)
            if score > best_score:
                best_score = score
                best = officer

        if best:
            # Decrement old officer workload
            if alert.assigned_officer:
                alert.assigned_officer.active_case_count = max(0, alert.assigned_officer.active_case_count - 1)
                alert.assigned_officer.save(update_fields=['active_case_count'])

            alert.assigned_officer = best
            alert.status = IncidentStatus.PENDING
            alert.save(update_fields=['assigned_officer', 'status'])

            _log_timeline(alert, IncidentStatus.PENDING, note=f"Reassigned to {best.full_name}")
            _send_officer_sms(best, alert, alert.incident_text, {
                'severity': alert.severity,
                'crime_type': alert.crime_type,
                'dispatch_recommendation': alert.dispatch_recommendation,
                'escalation_probability': alert.escalation_probability,
            })
            return True

        # No officer available → escalate to SHO
        return _escalate_to_sho(alert)

    except Exception as e:
        print(f"[reassign_alert] {e}")
        return False


def _escalate_to_sho(alert):
    """Escalates alert to Station Head Officer."""
    try:
        sho = get_sho_for_station(alert.station)
        if not sho:
            return False

        alert.is_escalated = True
        alert.escalated_to = sho
        alert.escalated_at = timezone.now()
        alert.status       = IncidentStatus.ESCALATED
        alert.save(update_fields=['is_escalated', 'escalated_to', 'escalated_at', 'status'])

        _log_timeline(alert, IncidentStatus.ESCALATED,
                      note=f"No available officer. Escalated to SHO: {sho.full_name}")

        # SMS SHO
        _send_officer_sms(sho, alert, alert.incident_text, {
            'severity': alert.severity,
            'crime_type': alert.crime_type,
            'dispatch_recommendation': alert.dispatch_recommendation,
            'escalation_probability': alert.escalation_probability,
        })
        return True

    except Exception as e:
        print(f"[_escalate_to_sho] {e}")
        return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log_timeline(alert, status, actor=None, note=''):
    """Creates one IncidentTimeline row."""
    try:
        IncidentTimeline.objects.create(
            alert=alert, status=status, actor=actor, note=note
        )
    except Exception as e:
        print(f"[_log_timeline] {e}")


def _send_officer_sms(officer, alert, text, analysis):
    """Sends SMS alert to officer. Wire to your SMS provider."""
    try:
        from home.sos_utils import send_sms   # ← change 'home'
        phone = officer.phone or ''
        if not phone:
            return False
        if not phone.startswith('+'):
            phone = '+91' + phone.lstrip('0')

        sev   = analysis.get('severity', 'UNKNOWN').upper()
        crime = analysis.get('crime_type', 'incident').title()
        esc   = analysis.get('escalation_probability', 0)
        maps  = alert.maps_url or 'GPS unavailable'

        msg = (
            f"[{sev}] {crime} — Alert #{alert.id}. "
            f"Escalation risk: {esc}%. "
            f"Location: {maps}. "
            f"Details: {text[:80]}. "
            f"Action: {analysis.get('dispatch_recommendation','Respond now')}."
        )
        send_sms(phone, msg)
        return True
    except Exception as e:
        print(f"[_send_officer_sms] {e}")
        return False