# home/ml_utils.py
import joblib
import pandas as pd
import re
import numpy as np
import logging
from django.core.exceptions import ObjectDoesNotExist
from .models import CrimeReport   # <-- Make sure you have this model

logger = logging.getLogger(__name__)

# Load the trained model and TF-IDF vectorizer
try:
    model = joblib.load("home/severity_model.pkl")
    tfidf_vectorizer = joblib.load("home/tfidf_vectorizer.pkl")
    expected_columns = joblib.load("home/expected_columns.pkl")
except Exception as e:
    logger.error(f"Error loading ML artifacts: {e}")
    model, tfidf_vectorizer, expected_columns = None, None, None


def preprocess_report(crime_type: str, description: str, address: str):
    """
    Preprocess crime report for severity prediction.
    Cleans text, applies TF-IDF, one-hot encodes categorical features.
    """
    crime_type_clean = crime_type.lower().strip()
    description_clean = description.lower().strip()
    description_clean = re.sub(r'[^\w\s]', '', description_clean)
    address_clean = address.strip()

    # DataFrame for vectorization
    data = pd.DataFrame({
        "crime_type": [crime_type_clean],
        "description": [description_clean],
        "address": [address_clean]
    })

    # TF-IDF features
    tfidf_features = tfidf_vectorizer.transform(data["description"]).toarray()

    # One-hot encode crime_type
    crime_type_encoded = pd.get_dummies(data["crime_type"])
    crime_type_encoded = crime_type_encoded.reindex(columns=expected_columns, fill_value=0)

    # Combine features
    combined_features = np.hstack((tfidf_features, crime_type_encoded.values))
    return combined_features


def predict_severity(crime_type: str, description: str, address: str) -> int:
    """
    Predict severity score using trained ML model.
    Returns a numeric severity score.
    """
    if not model:
        logger.error("ML model is not loaded.")
        return -1  # fallback

    try:
        features = preprocess_report(crime_type, description, address)
        severity_score = model.predict(features)
        return int(severity_score[0])
    except Exception as e:
        logger.error(f"Error in severity prediction: {e}")
        return -1  # fallback


def process_crime_report(crime_report_id: int) -> int:
    """
    High-level pipeline to fetch a crime report from DB,
    run severity prediction, and update the record.
    Designed for Celery tasks.
    """
    try:
        report = CrimeReport.objects.get(id=crime_report_id)
    except ObjectDoesNotExist:
        logger.error(f"CrimeReport with ID {crime_report_id} not found.")
        return -1

    # Run severity prediction
    severity = predict_severity(report.crime_type, report.description, report.address)

    if severity != -1:
        report.severity_score = severity
        report.save(update_fields=["severity_score"])
        logger.info(f"Updated CrimeReport {crime_report_id} with severity {severity}")
    else:
        logger.warning(f"Failed to update severity for CrimeReport {crime_report_id}")

    return severity
