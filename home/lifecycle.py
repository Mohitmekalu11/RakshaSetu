# ============================================================
# home/lifecycle.py  — Incident lifecycle business logic
# ============================================================
# All status transitions, timeline logging, escalation, metrics
# Live here — NOT in views.py.

from django.utils import timezone
from django.db import transaction


# ── Status → timestamp field mapping ──────────────────────────
TIMESTAMP_MAP = {
    'accepted': 'accepted_at',
    'enroute':  'enroute_at',
    'arrived':  'arrived_at',
    'resolved': 'resolved_at',
}

# ── Human-readable notes auto-generated per transition ────────
TRANSITION_NOTES = {
    'accepted':  'Officer accepted the alert and is preparing to respond.',
    'enroute':   'Officer is now en route to the incident location.',
    'arrived':   'Officer has arrived at the incident location.',
    'resolved':  'Incident has been resolved by the assigned officer.',
    'rejected':  'Officer rejected the alert. Reassigning.',
    'escalated': 'No officer responded. Alert escalated to Station Head Officer.',
}


def transition_status(alert, new_status, actor=None, note=''):
    """
    Core lifecycle function. Validates → transitions → logs → computes metrics.

    Returns:
        (success: bool, error_message: str | None)
    """
    from home.models import IncidentTimeline  # ← change 'home'

    # 1. Validate transition
    if not alert.can_transition_to(new_status):
        return False, (
            f"Invalid transition: {alert.status} → {new_status}. "
            f"Allowed: {alert.VALID_TRANSITIONS.get(alert.status, [])}"
        )

    with transaction.atomic():
        now = timezone.now()

        # 2. Update status
        alert.status = new_status

        # 3. Set timestamp
        ts_field = TIMESTAMP_MAP.get(new_status)
        if ts_field:
            setattr(alert, ts_field, now)

        # 4. Compute metrics
        if new_status == 'accepted' and alert.created_at:
            alert.response_time = int((now - alert.created_at).total_seconds())

        if new_status == 'resolved' and alert.created_at:
            alert.resolution_time = int((now - alert.created_at).total_seconds())

        alert.save()

        # 5. Log timeline entry
        IncidentTimeline.objects.create(
            alert     = alert,
            status    = new_status,
            actor     = actor,
            note      = note or TRANSITION_NOTES.get(new_status, ''),
        )

    return True, None


def get_next_valid_status(current_status):
    """Returns list of allowed next statuses from current."""
    from home.models import IncidentAlert  # ← change 'home'
    return IncidentAlert.VALID_TRANSITIONS.get(current_status, [])


def get_alert_live_data(alert):
    """
    Returns a dict of everything needed for real-time citizen tracking.
    Used by /api/incident/live/<id>/
    """
    officer = alert.assigned_officer
    station = alert.station

    officer_info = None
    if officer:
        officer_info = {
            'name':      officer.user.get_full_name() or officer.user.username,
            'phone':     officer.phone or officer.contact or '',
            'specialty': officer.specialty or 'General',
            'station':   station.name if station else '',
        }

    # Compute elapsed seconds for each stage
    def elapsed(ts):
        if not ts:
            return None
        return int((timezone.now() - ts).total_seconds())

    return {
        'id':           alert.id,
        'status':       alert.status,
        'severity':     alert.severity,
        'crime_type':   alert.crime_type,
        'summary':      alert.summary,
        'ward':         alert.ward,
        'landmark':     alert.landmark,
        'maps_url':     alert.maps_url(),
        'station':      station.name if station else None,
        'officer':      officer_info,
        'is_escalated': alert.is_escalated,
        'timestamps': {
            'created':  alert.created_at.strftime('%d %b, %H:%M:%S')  if alert.created_at  else None,
            'accepted': alert.accepted_at.strftime('%d %b, %H:%M:%S') if alert.accepted_at else None,
            'enroute':  alert.enroute_at.strftime('%d %b, %H:%M:%S')  if alert.enroute_at  else None,
            'arrived':  alert.arrived_at.strftime('%d %b, %H:%M:%S')  if alert.arrived_at  else None,
            'resolved': alert.resolved_at.strftime('%d %b, %H:%M:%S') if alert.resolved_at else None,
        },
        'metrics': {
            'response_time':   _fmt_seconds(alert.response_time),
            'resolution_time': _fmt_seconds(alert.resolution_time),
        },
        'escalation_probability': alert.escalation_probability,
        'area_risk_score':        alert.area_risk_score,
    }


def get_timeline_data(alert):
    """Returns serialized timeline for an alert."""
    return [
        {
            'status':    t.status,
            'note':      t.note,
            'actor':     t.actor.get_full_name() if t.actor else 'System',
            'timestamp': t.timestamp.strftime('%d %b, %H:%M:%S'),
            'ts_raw':    t.timestamp.isoformat(),
        }
        for t in alert.timeline.all()
    ]


def _fmt_seconds(seconds):
    if seconds is None:
        return None
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs    = seconds % 60
    return f"{minutes}m {secs}s"