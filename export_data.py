import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skillsphere.settings')
django.setup()

from home.models import PoliceStation, Ward
import json

# Export Police Stations
stations = list(PoliceStation.objects.values())
with open('fixtures/police_stations.json', 'w', encoding='utf-8') as f:
    json.dump(stations, f, indent=2, default=str)
print(f"Exported {len(stations)} police stations")

# Export Wards
wards = list(Ward.objects.values())
with open('fixtures/wards.json', 'w', encoding='utf-8') as f:
    json.dump(wards, f, indent=2, default=str)
print(f"Exported {len(wards)} wards")