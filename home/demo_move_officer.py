# demo_move_officer.py
# Simulates officer driving from Kopri toward Thane Station
# Run with: python manage.py shell < demo_move_officer.py

from home.models import userProfile
from django.utils import timezone
import time

OFFICER_USERNAME = "officer1"   # ← same as above

# 6 waypoints — Kopri → Thane Station (real road path approx)
ROUTE = [
    (19.2100, 72.9920),   # Start: Kopri
    (19.2050, 72.9880),   # Moving south-west
    (19.2000, 72.9840),   # Passing Kalwa bridge area
    (19.1960, 72.9810),   # Near Thane Creek
    (19.1910, 72.9780),   # Approaching station
    (19.1863, 72.9751),   # Arrived: Thane Station
]

try:
    profile = userProfile.objects.get(user__username=OFFICER_USERNAME)
    print(f"\n🚔 Moving officer '{OFFICER_USERNAME}' toward incident...\n")

    for i, (lat, lon) in enumerate(ROUTE):
        profile.current_latitude     = lat
        profile.current_longitude    = lon
        profile.last_location_update = timezone.now()
        profile.save(update_fields=['current_latitude', 'current_longitude', 'last_location_update'])

        remaining = len(ROUTE) - i - 1
        print(f"   Step {i+1}/{len(ROUTE)}: ({lat}, {lon})  —  {remaining} steps remaining")

        if remaining > 0:
            time.sleep(4)   # matches the 4s poll interval on the map

    print("\n✅ Officer has arrived at incident location!")
    print("   Mark status as 'Arrived' on the officer track page.\n")

except userProfile.DoesNotExist:
    print(f"❌ Officer '{OFFICER_USERNAME}' not found")
except Exception as e:
    print(f"❌ Error: {e}")