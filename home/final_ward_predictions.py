import pandas as pd
import json
from prophet import Prophet

# --- Load Data ---
crime_df = pd.read_csv('thane_crime_data.csv')

# Ensure 'Date & Time' is datetime
crime_df['Date & Time'] = pd.to_datetime(crime_df['Date & Time'], errors='coerce')
crime_df = crime_df.dropna(subset=['Date & Time'])  # drop invalid dates

# Strip spaces and lowercase for matching
crime_df['Area_clean'] = crime_df['Area'].astype(str).str.strip().str.lower()

with open('../static/data/ward_crime_counts.json') as f:
    ward_scores = json.load(f)

final_data = []

for ward in ward_scores:
    ward_name = ward['lgd_name']
    ward_name_clean = ward_name.strip().lower()
    ward_safety = ward['safety_score']
    ward_crime_count = ward['crime_count']

    # Filter crimes for this ward
    df = crime_df[crime_df['Area_clean'] == ward_name_clean].copy()

    if df.empty:
        print(f"No crime data found for {ward_name}")
        trend = []
        predicted_types = {}
    else:
        # --- Trend for VS Line Chart ---
        df['YearMonth'] = df['Date & Time'].dt.to_period('M').astype(str)
        monthly_counts = df.groupby('YearMonth').size().reset_index(name='actual')

        # Prepare for Prophet
        monthly_counts.rename(columns={'YearMonth':'ds', 'actual':'y'}, inplace=True)
        monthly_counts['ds'] = pd.to_datetime(monthly_counts['ds'])

        # Fit Prophet model
        m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        m.fit(monthly_counts)

        future = m.make_future_dataframe(periods=3, freq='M')  # predict next 3 months
        forecast = m.predict(future)

        # Build trend array
        trend = []
        actual_map = dict(zip(monthly_counts['ds'].dt.to_period('M').astype(str), monthly_counts['y']))
        for i, row in forecast.iterrows():
            date_str = row['ds'].strftime('%Y-%m')
            trend.append({
                'date': date_str,
                'actual': int(actual_map[date_str]) if date_str in actual_map else None,
                'predicted': int(row['yhat'])
            })

        # --- Predicted Crime Types Pie Chart ---
        type_counts = df['Crime Type'].value_counts()
        total = type_counts.sum()
        # Use proportion of past crimes to predict counts
        predicted_types = {ct: int((count/total)*monthly_counts['y'].sum()) for ct, count in type_counts.items()}

    # Append ward info
    final_data.append({
        'lgd_name': ward_name,
        'crime_count': ward_crime_count,
        'safety_score': ward_safety,
        'trend': trend,
        'predicted_types': predicted_types
    })

# --- Save to JSON ---
with open('final_ward_data.json', 'w') as f:
    json.dump(final_data, f, indent=4)

print("✅ Final JSON created: final_ward_data.json")
