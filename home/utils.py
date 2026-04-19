from django.core.mail import send_mail
from django.conf import settings

def send_email_to_client(email, token):
    subject = 'Reset Your Password'
    message = f'Please click on the following link to reset your password: http://127.0.0.1:8000/changepg/{token}/'
    email_from = settings.DEFAULT_FROM_EMAIL  # Using DEFAULT_FROM_EMAIL is better practice
    recipient_list = [email]
    
    try:
        send_mail(subject, message, email_from, recipient_list)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
def send_email_to_client_contact():
   pass
    
from .models import CrimeReport, userProfile

def officer_score(officer, crime_type):
    score = 0
    if officer.specialty == crime_type:
        score += 30
    if officer.experience_level == "Inspector":
        score += 20
    elif officer.experience_level == "Senior":
        score += 10
    # workload:
    open_cases = CrimeReport.objects.filter(
        assigned_officer=officer,
        resolution_status__in=["Pending","Under Investigation"]
    ).count()
    score += max(0, 20 - open_cases)
    return score

import pandas as pd

def get_thane_areas():
    df = pd.read_csv("home/thane_crime_data.csv")
    areas = sorted(df["Area"].dropna().unique().tolist())
    return areas
