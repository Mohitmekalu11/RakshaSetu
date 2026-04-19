import csv
from django.core.management.base import BaseCommand
from home.models import CrimeReport  # Adjust the import path if needed

class Command(BaseCommand):
    help = 'Exports crime report data to a CSV file'

    def handle(self, *args, **kwargs):
        # Define the output CSV file path
        output_file = "crime_report_data.csv"
        
        # Open the file in write mode
        with open(output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Write header row (adjust the field names as per your model)
            writer.writerow(['id', 'crime_type', 'address', 'description', 'reported_at','latitude','longitude'])
            # Query the CrimeReport model for all records
            reports = CrimeReport.objects.all()
            for report in reports:
                writer.writerow([
                    report.id,
                    report.crime_type,
                    report.address,
                    report.description,
                    report.reported_at,
                    report.latitude,
                    report.longitude,
                ])
        
        self.stdout.write(self.style.SUCCESS(f"Data exported successfully to {output_file}"))
