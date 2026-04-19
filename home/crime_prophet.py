import pandas as pd
from prophet import Prophet
import json
import webbrowser
from visualization import create_monthly_chart

def load_and_preprocess_data():
    """Load and preprocess the crime data."""
    print("Loading and preprocessing data...")
    print("Reading crime_data.csv...")
    
    # Load the data
    df = pd.read_csv('thane_crime_data.csv')
    print(f"Loaded {len(df)} records")
    
    # Convert date column to datetime
    df['Date & Time'] = pd.to_datetime(df['Date & Time'])
    print(f"Date range: {df['Date & Time'].min()} to {df['Date & Time'].max()}")
    
    # Group by date and count crimes
    daily_crimes = df.groupby(df['Date & Time'].dt.date).size().reset_index(name='crimes')
    daily_crimes.columns = ['ds', 'y']  # Prophet requires these column names
    
    # Convert date to datetime for Prophet
    daily_crimes['ds'] = pd.to_datetime(daily_crimes['ds'])
    
    # Sort by date
    daily_crimes = daily_crimes.sort_values('ds')
    
    print(f"Daily crimes range: {daily_crimes['y'].min()} to {daily_crimes['y'].max()}")
    
    return daily_crimes

def train_model(daily_crimes):
    """Train the Prophet model."""
    print("Training Prophet model...")
    print("Creating Prophet model...")
    
    # Create and fit the model
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=True,
        changepoint_prior_scale=0.05
    )
    
    print("Fitting model to data...")
    model.fit(daily_crimes)
    print("Model fitting complete")
    
    return model

def make_predictions(model, daily_crimes):
    """Make predictions using the trained model."""
    print("Making predictions...")
    
    # Create future dates for prediction
    future_dates = model.make_future_dataframe(periods=365*4)  # 4 years of predictions
    print("Creating future dates for prediction...")
    
    # Make predictions
    forecast = model.predict(future_dates)
    print("Predictions complete")
    
    return forecast

def main():
    """Main function to run the crime prediction pipeline."""
    try:
        # Load and preprocess data
        daily_crimes = load_and_preprocess_data()
        
        # Train model
        model = train_model(daily_crimes)
        
        # Make predictions
        forecast = make_predictions(model, daily_crimes)
        
        # Create visualization
        print("Creating monthly visualization...")
        create_monthly_chart(daily_crimes, forecast)
        
        print("\nPrediction complete! Results have been saved to 'monthly_crime_predictions.html'")
        
        # Print summary statistics
        print(f"\nPredicted average daily crimes: {forecast['yhat'].mean():.2f}")
        print(f"\nLatest prediction for {forecast['ds'].max().strftime('%Y-%m-%d')}:")
        print(f"Predicted crimes: {forecast['yhat'].iloc[-1]:.2f}")
        print(f"Prediction interval: {forecast['yhat_lower'].iloc[-1]:.2f} - {forecast['yhat_upper'].iloc[-1]:.2f}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 