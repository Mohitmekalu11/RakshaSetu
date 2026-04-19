from django.core.management.base import BaseCommand
import pandas as pd
from shapely.geometry import Point, shape
import json
import os
from django.conf import settings

class Command(BaseCommand):
    help = "Populate ward crime counts JSON from CSV"

    def handle(self, *args, **options):
        # File paths
        geojson_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'thane_wards.json')
        csv_path = os.path.join(settings.BASE_DIR, 'home', 'thane_crime_data.csv')
        output_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'ward_crime_counts.json')

        # Load wards GeoJSON
        try:
            with open(geojson_path) as f:
                wards_geojson = json.load(f)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"GeoJSON file not found at: {geojson_path}"))
            return

        # Load crime CSV
        try:
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"CSV file not found at: {csv_path}"))
            return

        # Parse ward polygons
        ward_polygons = []
        for feature in wards_geojson['features']:
            props = feature.get('properties', {})
            lgd_name = props.get('lgd_name') or props.get('ward_name') or props.get('name')
            if not lgd_name:
                self.stdout.write(self.style.WARNING(f"Skipping feature with missing ward name: {props}"))
                continue

            ward_polygons.append({
                'lgd_name': lgd_name,
                'polygon': shape(feature['geometry'])
            })

        if not ward_polygons:
            self.stderr.write(self.style.ERROR("No valid ward polygons found."))
            return

        # Initialize crime count dictionary
        crime_count_per_ward = {wp['lgd_name']: 0 for wp in ward_polygons}

        # Assign each crime to a ward
        for _, row in df.iterrows():
            try:
                point = Point(row['Longitude'], row['Latitude'])
            except KeyError:
                self.stderr.write(self.style.ERROR("CSV must have 'Longitude' and 'Latitude' columns"))
                return

            for wp in ward_polygons:
                if wp['polygon'].contains(point):
                    crime_count_per_ward[wp['lgd_name']] += 1
                    break

        # Compute safety score
        max_crimes = max(crime_count_per_ward.values()) or 1
        ward_scores = []
        for ward_name, count in crime_count_per_ward.items():
            safety_score = max(0, 100 - (count / max_crimes) * 100)
            ward_scores.append({
                'lgd_name': ward_name,
                'crime_count': count,
                'safety_score': safety_score
            })

        # Save JSON
        with open(output_path, 'w') as f:
            json.dump(ward_scores, f, indent=2)

        self.stdout.write(self.style.SUCCESS("Ward crime counts JSON generated successfully!"))
