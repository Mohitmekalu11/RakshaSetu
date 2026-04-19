"""
thane_station_ward_map.py
Place this file at: home/thane_station_ward_map.py

This is the MISSING LINK:
  GPS/Landmark → Ward → PoliceStation → Officer → IncidentAlert
"""

THANE_STATION_WARD_MAP = {
    "Thane City Police Station":     ["Ward No.1",  "Ward No.2",  "Ward No.3",  "Ward No.5"],
    "Naupada Police Station":        ["Ward No.4",  "Ward No.6",  "Ward No.7"],
    "Hindustan Naka Police Station": ["Ward No.8",  "Ward No.9",  "Ward No.10", "Ward No.11"],
    "Vartak Nagar Police Station":   ["Ward No.12", "Ward No.13", "Ward No.15", "Ward No.16"],
    "Wagle Estate Police Station":   ["Ward No.14", "Ward No.17", "Ward No.18", "Ward No.19"],
    "Kopri Police Station":          ["Ward No.20", "Ward No.21", "Ward No.22"],
    "Rabodi Police Station":         ["Ward No.23", "Ward No.24", "Ward No.25"],
    "Mumbra Police Station":         ["Ward No.26", "Ward No.27", "Ward No.28"],
    "Kalwa Police Station":          ["Ward No.29", "Ward No.30", "Ward No.31"],
    "Kolshet Police Station":        ["Ward No.32", "Ward No.33", "Ward No.34"],
    "Ghodbunder Police Station":     ["Ward No.35", "Ward No.36", "Ward No.37", "Ward No.40"],
    "Kasarwadavali Police Station":  ["Ward No.38", "Ward No.39", "Ward No.41"],
    "Majiwada Police Station":       ["Ward No.42", "Ward No.43", "Ward No.44"],
    "Manpada Police Station":        ["Ward No.45", "Ward No.46", "Ward No.47"],
}

# Reverse: ward lgd_name → station name
WARD_TO_STATION = {
    ward: station
    for station, wards in THANE_STATION_WARD_MAP.items()
    for ward in wards
}

LANDMARK_TO_STATION = {
    "kopri":         "Kopri Police Station",
    "ghodbunder":    "Ghodbunder Police Station",
    "majiwada":      "Majiwada Police Station",
    "mumbra":        "Mumbra Police Station",
    "kalwa":         "Kalwa Police Station",
    "wagle":         "Wagle Estate Police Station",
    "vartak":        "Vartak Nagar Police Station",
    "naupada":       "Naupada Police Station",
    "kolshet":       "Kolshet Police Station",
    "manpada":       "Manpada Police Station",
    "kasarwadavali": "Kasarwadavali Police Station",
    "rabodi":        "Rabodi Police Station",
    "station road":  "Thane City Police Station",
    "thane station": "Thane City Police Station",
    "viviana":       "Vartak Nagar Police Station",
    "upvan":         "Vartak Nagar Police Station",
    "hiranandani":   "Ghodbunder Police Station",
    "korum":         "Naupada Police Station",
}


def get_station_for_ward(ward_name):
    """Ward lgd_name → PoliceStation object."""
    from home.models import PoliceStation
    if not ward_name:
        return PoliceStation.objects.first()
    station_name = WARD_TO_STATION.get(ward_name)
    if station_name:
        station = PoliceStation.objects.filter(name__iexact=station_name).first()
        if station:
            return station
        # fuzzy match on first keyword e.g. "Kopri"
        keyword = station_name.split()[0]
        return PoliceStation.objects.filter(name__icontains=keyword).first()
    return PoliceStation.objects.first()


def get_station_for_landmark(landmark):
    """Landmark text → PoliceStation object."""
    from home.models import PoliceStation
    if not landmark:
        return None
    lm = landmark.lower()
    for key, station_name in LANDMARK_TO_STATION.items():
        if key in lm:
            keyword = station_name.split()[0]
            return PoliceStation.objects.filter(name__icontains=keyword).first()
    return None