"""
setup_thane_stations.py
Management command to populate real Thane police stations.

Save to: home/management/commands/setup_thane_stations.py
Run with: python manage.py setup_thane_stations

Run this ONCE before testing the dispatch feature.
"""

from django.core.management.base import BaseCommand


THANE_STATIONS = [
    {"name": "Thane City Police Station",     "address": "Station Road, Thane West, 400601"},
    {"name": "Naupada Police Station",        "address": "Naupada, Thane West, 400602"},
    {"name": "Hindustan Naka Police Station", "address": "Hindustan Naka, Thane West, 400615"},
    {"name": "Vartak Nagar Police Station",   "address": "Vartak Nagar, Thane West, 400606"},
    {"name": "Wagle Estate Police Station",   "address": "Wagle Industrial Estate, Thane, 400604"},
    {"name": "Kopri Police Station",          "address": "Kopri Colony, Thane East, 400603"},
    {"name": "Rabodi Police Station",         "address": "Rabodi, Thane East, 400601"},
    {"name": "Mumbra Police Station",         "address": "Mumbra, Thane District, 400612"},
    {"name": "Kalwa Police Station",          "address": "Kalwa, Thane, 400605"},
    {"name": "Kolshet Police Station",        "address": "Kolshet Road, Thane West, 400607"},
    {"name": "Ghodbunder Police Station",     "address": "Ghodbunder Road, Thane West, 400615"},
    {"name": "Kasarwadavali Police Station",  "address": "Kasarwadavali, Ghodbunder Road, 400615"},
    {"name": "Majiwada Police Station",       "address": "Majiwada, Thane West, 400601"},
    {"name": "Manpada Police Station",        "address": "Manpada Road, Thane West, 400610"},
]


class Command(BaseCommand):
    help = 'Creates all 14 Thane police stations in the database'

    def handle(self, *args, **kwargs):
        from home.models import PoliceStation  # ← change 'home' if needed

        created = 0
        skipped = 0

        for s in THANE_STATIONS:
            obj, was_created = PoliceStation.objects.get_or_create(
                name=s['name'],
                defaults={'address': s['address']}
            )
            if was_created:
                created += 1
                self.stdout.write(f"  ✓ Created: {s['name']}")
            else:
                skipped += 1
                self.stdout.write(f"  — Exists:  {s['name']}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created} | Already existed: {skipped}"
        ))
        self.stdout.write("")
        self.stdout.write(
            "Next step: Go to admin and assign police officers to their stations.\n"
            "Each officer's 'station' field should be set to one of these 14 stations."
        )