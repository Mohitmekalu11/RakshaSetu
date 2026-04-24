# home/tasks.py
import os
import logging
# from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import CrimeReport, CrimePhoto
from .ml_utils import predict_severity
# from .utils_pkg.deepfake_detector import is_fake_image, is_fake_video

logger = logging.getLogger(__name__)

# Temp folder for processing uploaded media
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


# @shared_task
def analyze_crime_report(report_id):
    """
    Celery task to:
    1️⃣ Predict NLP severity
    2️⃣ Update report's AI status
    """
    try:
        report = CrimeReport.objects.get(id=report_id)
        
        # Predict severity
        severity_score = predict_severity(report.crime_type, report.description, report.address)
        report.severity_score = severity_score
        report.ai_status = "Processing"
        send_progress(report.id, 20, "NLP Analysis Started")
        report.save()
        logger.info(f"Report {report.id}: NLP severity predicted.")

    except Exception as e:
        logger.error(f"[analyze_crime_report] Error processing report {report_id}: {str(e)}")
        if 'report' in locals():
            report.ai_status = "Error"
            report.save()


# @shared_task
def verify_media_ai(report_id):
    """
    Celery task to:
    1️⃣ Check photos and video for AI-generated content
    2️⃣ Update report's AI status
    3️⃣ Send live progress + alerts via Django Channels
    """
    try:
        report = CrimeReport.objects.get(id=report_id)

        # ✅ Now safe to call
        send_progress(report.id, 50, "NLP Analysis Completed")

        fake_detected = False
        fake_files = []

        # -----------------------------
        # Check photos
        # -----------------------------
        photos = CrimePhoto.objects.filter(crime_report=report)
        send_progress(report.id, 70, "Media Verification Started")

        for photo in photos:
            temp_path = os.path.join(TEMP_DIR, f"{photo.id}_{photo.photos.name}")
            with open(temp_path, "wb+") as f:
                for chunk in photo.photos.chunks():
                    f.write(chunk)
            try:
                if is_fake_image(temp_path):
                    fake_detected = True
                    fake_files.append(photo.photos.name)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # -----------------------------
        # Check video
        # -----------------------------
        if report.video:
            temp_video_path = os.path.join(TEMP_DIR, f"{report.id}_{report.video.name}")
            with open(temp_video_path, "wb+") as f:
                for chunk in report.video.chunks():
                    f.write(chunk)
            try:
                if is_fake_video(temp_video_path):
                    fake_detected = True
                    fake_files.append(report.video.name)
            finally:
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)

        # -----------------------------
        # Update report status
        # -----------------------------
        if fake_detected:
            report.ai_status = "Fake Detected"
            logger.warning(f"Report {report.id}: AI-generated media found: {', '.join(fake_files)}")
            send_progress(report.id, 100, "Fake Media Detected")
        else:
            report.ai_status = "Verified"
            logger.info(f"Report {report.id}: Media verified successfully.")
            send_progress(report.id, 100, "Report Verified")

        report.save()

        # -----------------------------
        # Final WebSocket alert
        # -----------------------------
        channel_layer = get_channel_layer()
        message = (f"⚠️ Report {report.id} contains AI-generated media: {', '.join(fake_files)}"
                   if fake_detected else f"✅ Report {report.id} verified successfully.")
        async_to_sync(channel_layer.group_send)(
            "crime_alerts",
            {
                "type": "crime_message",
                "message": message
            }
        )

    except Exception as e:
        logger.error(f"[verify_media_ai] Error processing report {report_id}: {str(e)}")
        if 'report' in locals():
            report.ai_status = "Error"
            report.save()
            send_progress(report.id, 100, "Error during AI verification")
            
# tasks.py
def send_progress(report_id: int, progress: int, message: str):
    """
    Updates report progress in DB (no websockets for now).
    """
    try:
        report = CrimeReport.objects.get(id=report_id)
        report.ai_progress = progress
        report.ai_status = message
        report.save(update_fields=["ai_progress", "ai_status"])
    except CrimeReport.DoesNotExist:
        pass
