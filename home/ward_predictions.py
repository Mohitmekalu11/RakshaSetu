import pandas as pd
from prophet import Prophet
import json
import os

# --------------------------
# 1️⃣ Load your CSV
# --------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to the CSV inside your 'home' app
CSV_PATH = os.path.join(BASE_DIR, 'home', 'thane_crime_data.csv')
df = pd.read_csv(CSV_PATH)

# Ensure date column is in datetime format
df["Date & Time"] = pd.to_datetime(df["Date & Time"], errors="coerce")

# Keep only necessary columns
df = df[["Area", "Crime Type", "Date & Time"]]

# Extract year
df['Year'] = df['Date & Time'].dt.year

# --------------------------
# 2️⃣ Prepare ward-wise yearly counts
# --------------------------
ward_list = df['Area'].unique()
ward_forecasts = {}

for ward in ward_list:
    ward_df = df[df['Area'] == ward]
    
    # Count crimes per year
    yearly_counts = ward_df.groupby('Year')['Crime Type'].count().sort_index()
    
    # If there are missing years, fill with 0
    all_years = list(range(yearly_counts.index.min(), yearly_counts.index.max()+1))
    yearly_counts = yearly_counts.reindex(all_years, fill_value=0)
    
    # Prepare DataFrame for Prophet
    prophet_df = pd.DataFrame({
        'ds': pd.to_datetime(yearly_counts.index, format='%Y'),
        'y': yearly_counts.values
    })
    
    # --------------------------
    # 3️⃣ Fit Prophet model
    # --------------------------
    model = Prophet(yearly_seasonality=False, daily_seasonality=False, weekly_seasonality=False)
    model.fit(prophet_df)
    
    # --------------------------
    # 4️⃣ Forecast for future years
    # --------------------------
    future_years = [2026, 2027, 2028]
    future_df = pd.DataFrame({'ds': pd.to_datetime(future_years, format='%Y')})
    forecast = model.predict(future_df)
    
    # --------------------------
    # 5️⃣ Save predictions in dict
    # --------------------------
    trend_dict = yearly_counts.to_dict()
    for y, pred in zip(future_years, forecast['yhat']):
        trend_dict[y] = int(round(pred))
    
    ward_forecasts[ward] = {
        "trend": {str(k): v for k, v in trend_dict.items()},
        "predicted": int(round(forecast['yhat'].iloc[-1]))
    }

# --------------------------
# 6️⃣ Save to JSON
# --------------------------
OUTPUT_PATH = os.path.join(BASE_DIR, 'home', 'ward_predictions_2026_2028.json')

with open(OUTPUT_PATH, "w") as f:
    json.dump(ward_forecasts, f, indent=4)

print(f"✅ Forecast saved to {OUTPUT_PATH}")
