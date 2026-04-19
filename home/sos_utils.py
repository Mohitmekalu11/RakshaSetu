"""
sos_utils.py  —  adapted to your actual models
"""

import math
import threading
from django.utils import timezone
from django.conf import settings
from twilio.rest import Client


# ──────────────────────────────────────────────────────────────
# 1. Find nearest on-duty officers
#    Uses userProfile (your actual model) not OfficerProfile
# ──────────────────────────────────────────────────────────────

def get_nearest_officers(latitude, longitude, ward, limit=3):
    """
    Returns up to `limit` on-duty police officers sorted by distance.
    Prefers officers in the same ward/location first, then expands.
    """
    from .models import userProfile

    # Primary pool: police officers, on duty, in same location as ward, not overloaded
    base_qs = userProfile.objects.filter(
        role='police',
        is_on_duty=True,
        is_approved=True,
    ).exclude(
        current_latitude=None,
        current_longitude=None,
    )

    # Try same location/ward first
    if ward:
        same_area = base_qs.filter(location__icontains=ward.townname)
        ranked = _rank_by_distance(same_area, latitude, longitude)
    else:
        ranked = []

    # Not enough? Pull from all on-duty officers
    if len(ranked) < limit:
        already_ids = [o.id for o in ranked]
        fallback = base_qs.exclude(id__in=already_ids)
        ranked += _rank_by_distance(fallback, latitude, longitude)

    return ranked[:limit]


def _rank_by_distance(queryset, lat, lon):
    officers = list(queryset)
    for officer in officers:
        officer.distance_km = _haversine(
            lat, lon,
            float(officer.current_latitude),
            float(officer.current_longitude),
        )
    return sorted(officers, key=lambda o: o.distance_km)


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ──────────────────────────────────────────────────────────────
# 2. Get Ward from coordinates
#    Your Ward model has no centroid yet — uses townname match as
#    fallback until you add centroid_latitude/longitude fields
# ──────────────────────────────────────────────────────────────

def get_ward_from_coordinates(latitude, longitude):
    """
    Returns the closest Ward using centroid distance.
    Falls back to first ward in Thane if centroids not populated yet.
    """
    from .models import Ward

    wards = Ward.objects.exclude(
        centroid_latitude=None,
        centroid_longitude=None
    )

    if not wards.exists():
        # Fallback until you populate centroid fields
        return Ward.objects.filter(townname="Thane").first()

    closest, min_dist = None, float('inf')
    for ward in wards:
        dist = _haversine(
            latitude, longitude,
            float(ward.centroid_latitude),
            float(ward.centroid_longitude),
        )
        if dist < min_dist:
            min_dist = dist
            closest = ward
    return closest


# ──────────────────────────────────────────────────────────────
# 3. Build enriched SMS message
# ──────────────────────────────────────────────────────────────

def build_alert_message(alert, citizen_user, ward):
    ward_name = ward.lgd_name if ward else "Unknown ward"   # your Ward uses lgd_name
    maps_link = f"https://maps.google.com/?q={alert.latitude},{alert.longitude}"
    time_str  = alert.triggered_at.strftime('%H:%M')
    name      = citizen_user.get_full_name() or citizen_user.username

    return (
        f"[SOS ALERT] {name} needs help. "
        f"Ward: {ward_name}. Time: {time_str}. "
        f"Location: {maps_link} "
        f"Alert ID: #{alert.id}. "
        f"Reply ACCEPT {alert.id} to acknowledge."
    )


def build_trusted_contact_message(alert, citizen_user):
    """Separate, friendlier message for TrustedContacts."""
    maps_link = f"https://maps.google.com/?q={alert.latitude},{alert.longitude}"
    name = citizen_user.get_full_name() or citizen_user.username
    return (
        f"EMERGENCY: {name} has triggered an SOS alert. "
        f"Last known location: {maps_link}. "
        f"Police have been notified. Please try to reach them."
    )


# ──────────────────────────────────────────────────────────────
# 4. Twilio SMS + WhatsApp
# ──────────────────────────────────────────────────────────────

def _twilio():
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_sms(to_number, message):
    """Returns True on success. to_number must be E.164 e.g. +919876543210"""
    try:
        _twilio().messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_number,
        )
        return True
    except Exception as e:
        print(f"[SMS FAIL] {to_number}: {e}")
        return False


def send_whatsapp(to_number, message):
    """WhatsApp fallback via Twilio sandbox."""
    try:
        _twilio().messages.create(
            body=message,
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
            to=f"whatsapp:{to_number}",
        )
        return True
    except Exception as e:
        print(f"[WHATSAPP FAIL] {to_number}: {e}")
        return False


def notify(phone_number, message):
    """Try SMS first, fall back to WhatsApp."""
    if not send_sms(phone_number, message):
        send_whatsapp(phone_number, message)


# ──────────────────────────────────────────────────────────────
# 5. Notify TrustedContacts (you already have this model)
# ──────────────────────────────────────────────────────────────

def notify_trusted_contacts(alert, citizen_user):
    from .models import TrustedContact
    contacts = TrustedContact.objects.filter(user=citizen_user)
    message  = build_trusted_contact_message(alert, citizen_user)

    for contact in contacts:
        # Normalize to E.164 for Indian numbers
        phone = contact.phone_number.strip()
        if not phone.startswith('+'):
            phone = '+91' + phone.lstrip('0')
        notify(phone, message)


# ──────────────────────────────────────────────────────────────
# 6. Escalation to SHO after 5 minutes
# ──────────────────────────────────────────────────────────────

def schedule_escalation(alert_id, delay_minutes=5):
    """
    Background thread — escalates to SHO if no officer acknowledges.
    Replace with Celery in production (see comment below).
    """
    def _run():
        import time
        time.sleep(delay_minutes * 60)
        try:
            from .models import SOSAlert
            alert = SOSAlert.objects.get(id=alert_id)
            if alert.status not in ('acknowledged', 'resolved', 'cancelled', 'escalated'):
                _escalate_to_sho(alert, "No officer acknowledged within 5 minutes")
        except Exception as e:
            print(f"[ESCALATION ERROR] Alert #{alert_id}: {e}")

    threading.Thread(target=_run, daemon=True).start()


def _escalate_to_sho(alert, reason):
    from .models import userProfile

    # Find SHO in same station/location as the ward
    sho = userProfile.objects.filter(
        role='sho',
        is_approved=True,
        is_on_duty=True,
        location__icontains=alert.ward.townname if alert.ward else '',
    ).first()

    if not sho:
        # Any SHO as last resort
        sho = userProfile.objects.filter(role='sho', is_approved=True).first()

    if sho and sho.phone:
        maps_link = f"https://maps.google.com/?q={alert.latitude},{alert.longitude}"
        message = (
            f"[ESCALATED SOS] Citizen {alert.citizen.get_full_name() or alert.citizen.username} "
            f"at {alert.ward.lgd_name if alert.ward else 'Unknown ward'}. "
            f"Location: {maps_link}. "
            f"Reason: {reason}. Alert ID: #{alert.id}."
        )
        phone = sho.phone if sho.phone.startswith('+') else '+91' + sho.phone
        notify(phone, message)

        alert.status       = 'escalated'
        alert.escalated_to = sho
        alert.escalated_at = timezone.now()
        alert.save()


