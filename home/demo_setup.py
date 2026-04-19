# demo_setup.py
# Run with: python manage.py shell < demo_setup.py
# Or paste into: python manage.py shell

from home.models import userProfile, IncidentAlert, IncidentStatus
from django.utils import timezone
import time

print("\n🎬 CRIMECAST DEMO SETUP")
print("=" * 40)

# ── CONFIG — change these to your actual usernames ──────────────
OFFICER_USERNAME = "officer1"   # ← your officer's login
CITIZEN_USERNAME = "citizen1"   # ← your citizen's login (optional)

# ── DEMO LOCATIONS (Thane area — spread apart realistically) ────
# Incident reported near Thane Station
INCIDENT_LAT = 19.1863
INCIDENT_LON = 72.9751

# Citizen is at incident location
CITIZEN_LAT  = 19.1863
CITIZEN_LON  = 72.9751

# Officer starts ~3km away at Kopri
OFFICER_LAT  = 19.2100
OFFICER_LON  = 72.9920

# ── STEP 1: Place officer far from incident ──────────────────────
try:
    officer_profile = userProfile.objects.get(user__username=OFFICER_USERNAME)
    officer_profile.current_latitude    = OFFICER_LAT
    officer_profile.current_longitude   = OFFICER_LON
    officer_profile.last_location_update = timezone.now()
    officer_profile.is_on_duty          = True
    officer_profile.save()
    print(f"✅ Officer '{OFFICER_USERNAME}' placed at Kopri ({OFFICER_LAT}, {OFFICER_LON})")
except userProfile.DoesNotExist:
    print(f"❌ Officer '{OFFICER_USERNAME}' not found — update OFFICER_USERNAME above")

# ── STEP 2: Set citizen live GPS on the most recent alert ────────
try:
    latest_alert = IncidentAlert.objects.order_by('-created_at').first()
    if latest_alert:
        latest_alert.citizen_latitude  = CITIZEN_LAT
        latest_alert.citizen_longitude = CITIZEN_LON
        latest_alert.latitude          = INCIDENT_LAT
        latest_alert.longitude         = INCIDENT_LON
        latest_alert.save(update_fields=[
            'citizen_latitude', 'citizen_longitude',
            'latitude', 'longitude'
        ])
        print(f"✅ Alert #{latest_alert.id} incident pinned at Thane Station")
        print(f"   Citizen GPS set at same point (realistic)")
        print(f"   Status: {latest_alert.status}")
        print(f"   Officer assigned: {latest_alert.assigned_officer}")
    else:
        print("❌ No alerts found — submit a test incident first")
except Exception as e:
    print(f"❌ Alert update failed: {e}")

print("\n" + "=" * 40)
print("📍 MAP PREVIEW:")
print(f"   🚨 Incident  → {INCIDENT_LAT}, {INCIDENT_LON}  (Thane Station)")
print(f"   🙋 Citizen   → {CITIZEN_LAT}, {CITIZEN_LON}   (same spot)")
print(f"   🚔 Officer   → {OFFICER_LAT}, {OFFICER_LON}  (Kopri, ~3km away)")
print("=" * 40)
print("\n✅ Demo ready. Now:")
print("   1. Log in as officer → go to dashboard → click 'En Route'")
print("   2. Open officer/track/<alert_id>/ — officer pin will be at Kopri")
print("   3. Route draws from Kopri → Thane Station\n")