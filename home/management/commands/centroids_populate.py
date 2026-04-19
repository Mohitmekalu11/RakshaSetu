from django.core.management.base import BaseCommand
import json
import os
 
 
class Command(BaseCommand):
    help = 'Creates or updates all 47 Ward objects from thane_wards.json'
 
    def handle(self, *args, **kwargs):
        from home.models import Ward  # ← your app is 'home' based on the traceback
 
        json_path = os.path.join(os.getcwd(), 'static/data/thane_wards.json')
 
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(
                f"File not found: {json_path}\n"
                "Place thane_wards.json in the same folder as manage.py."
            ))
            return
 
        with open(json_path, 'r') as f:
            data = json.load(f)
 
        created_count = 0
        updated_count = 0
 
        for feature in data['features']:
            props  = feature['properties']
            coords = feature['geometry']['coordinates'][0]
 
            avg_lon = sum(c[0] for c in coords) / len(coords)
            avg_lat = sum(c[1] for c in coords) / len(coords)
 
            # Ward No.46 is missing lgd_name in the JSON — fallback to sourcewardcode
            lgd_name = props.get('lgd_name') or f"Ward No.{props['sourcewardcode']}"
 
            ward, created = Ward.objects.update_or_create(
                lgd_name=lgd_name,        # match on name (the only true unique field)
                defaults={
                    # lgd_code is NOT unique — store it but don't match on it
                    'lgd_code':           props.get('lgd_code'),
                    'townname':           props.get('townname', 'Thane'),
                    'state':              props.get('state', 'Maharashtra'),
                    'st_area':            props.get('st_area(shape)'),
                    'st_length':          props.get('st_length(shape)'),
                    'centroid_latitude':  round(avg_lat, 7),
                    'centroid_longitude': round(avg_lon, 7),
                }
            )
 
            label = "CREATED" if created else "UPDATED"
            if created:
                created_count += 1
            else:
                updated_count += 1
 
            self.stdout.write(
                f"  ✓  [{label}]  {lgd_name:<15}  {avg_lat:.6f},  {avg_lon:.6f}"
            )
 
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done.  Created: {created_count}  |  Updated: {updated_count}  |  Total: {created_count + updated_count}"
        ))
 