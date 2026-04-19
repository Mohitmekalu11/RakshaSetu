import pandas as pd
from django.core.management.base import BaseCommand
from home.models import CrimeRecord
from datetime import datetime

class Command(BaseCommand):
    help = "Import crime data from CSV into the CrimeRecord model"

    def handle(self, *args, **kwargs):
        csv_path = "home/crime_data.csv"  # ✅ Adjust path if needed

        try:
            df = pd.read_csv(csv_path)

            # Convert "Date & Time" column
            df["Date & Time"] = pd.to_datetime(df["Date & Time"], errors='coerce')

            # Iterate through the DataFrame and insert data
            crime_records = []
            for _, row in df.iterrows():
                crime_records.append(CrimeRecord(
                    date_time=row["Date & Time"],
                    year=row["Date & Time"].year if pd.notna(row["Date & Time"]) else None,
                    state=row["State"],
                    district=row["District"],
                    city=row["City"] if pd.notna(row["City"]) else None,
                    crime_type=row["Crime Type"],
                    latitude=row["Latitude"] if pd.notna(row["Latitude"]) else None,
                    longitude=row["Longitude"] if pd.notna(row["Longitude"]) else None,
                    status=row["Status"] if "Status" in df.columns else "Unsolved",
                ))

            # Bulk insert data for efficiency
            CrimeRecord.objects.bulk_create(crime_records)

            self.stdout.write(self.style.SUCCESS("✅ Crime data imported successfully!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error importing data: {e}"))
