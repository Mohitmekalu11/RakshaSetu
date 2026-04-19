# import joblib
# import pandas as pd
# import re
# import numpy as np

# # Load the trained model and the TF-IDF vectorizer.
# # Adjust the paths to where you've stored 'severity_model.pkl' and 'tfidf_vectorizer.pkl'
# model = joblib.load("home/severity_model.pkl")
# tfidf_vectorizer = joblib.load("home/tfidf_vectorizer.pkl")
# expected_columns = joblib.load("home/expected_columns.pkl")

# print(expected_columns)

# print("Model was trained with:", model.n_features_in_, "features")

# def preprocess_report(crime_type, description, address):
#     # Clean and standardize the inputs
#     crime_type_clean = crime_type.lower().strip()
#     description_clean = description.lower().strip()
#     description_clean = re.sub(r'[^\w\s]', '', description_clean)
#     address_clean = address.strip()

#     # Create DataFrame for vectorization
#     data = pd.DataFrame({
#         "crime_type": [crime_type_clean],
#         "description": [description_clean],
#         "address": [address_clean]
#     })

#     # Transform description with TF-IDF
#     tfidf_features = tfidf_vectorizer.transform(data["description"]).toarray()

#     # One-hot encode crime_type
#     crime_type_encoded = pd.get_dummies(data["crime_type"])

#     # Reindex to ensure that the DataFrame has exactly the expected columns
#     crime_type_encoded = crime_type_encoded.reindex(columns=expected_columns, fill_value=0)

#     # Combine TF-IDF and one-hot encoded features
#     combined_features = np.hstack((tfidf_features, crime_type_encoded.values))
#     features = np.hstack((tfidf_features, crime_type_encoded.values))
#     print("Feature shape:", features.shape)
#     return combined_features

# def predict_severity(crime_type, description, address):
#     features = preprocess_report(crime_type, description, address)
#     severity_score = model.predict(features)
#     return severity_score[0]