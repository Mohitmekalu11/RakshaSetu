import json
import webbrowser
import os
import pandas as pd
from datetime import datetime
from prophet import Prophet

def prepare_state_data(df):
    """Prepare data for each state & crime type."""
    state_data = {}
    states = df['State'].unique().tolist()
    crime_types = df['Crime Type'].unique().tolist()
    
    for state in states:
        print(f"Processing state {state}...")
        state_data[state] = {}
        df_state = df[df['State'] == state]
        
        for crime_type in crime_types:
            print(f"  → Processing crime type {crime_type}...")
            subset = df_state[df_state['Crime Type'] == crime_type]
            if subset.empty:
                continue
            
            # daily counts
            daily = (
                subset
                .groupby('Date & Time')
                .size()
                .reset_index(name='crimes')
                .rename(columns={'Date & Time':'ds', 'crimes':'y'})
            )
            
            # monthly historical
            monthly_hist = daily.set_index('ds').resample('M')['y'].mean()
            
            # fit Prophet
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=True,
                changepoint_prior_scale=0.05
            )
            model.fit(daily)
            
            # future + forecast
            future = model.make_future_dataframe(periods=365*4)
            forecast = model.predict(future)
            monthly_fore = forecast.set_index('ds').resample('M')['yhat'].mean()
            
            # split at cutoff
            cutoff = pd.Timestamp('2024-12-31')
            hist = monthly_hist[monthly_hist.index <= cutoff]
            fore = monthly_fore[monthly_fore.index > cutoff]
            
            # store
            state_data[state][crime_type] = {
                'historical': hist.round(0).tolist(),
                'forecast': [None]*len(hist) + fore.round(0).tolist(),
                'avg_monthly_crimes': float(hist.mean()),
                'latest_monthly_pred': float(fore.iloc[-1] if len(fore)>0 else 0),
                'monthly_change': float(((fore.iloc[-1] - hist.mean())/hist.mean()*100) if len(hist)>0 else 0)
            }
    return states, crime_types, state_data

def calculate_statistics(historical_data, forecast_data):
    """Unchanged from before."""
    avg = historical_data.mean()
    latest = forecast_data.iloc[-1]
    change = (latest-avg)/avg*100
    return {'avg_monthly_crimes':float(avg),
            'latest_monthly_pred':float(latest),
            'monthly_change':float(change)}

def generate_html_content(historical_data, forecast_data, stats, start_year, states, crime_types, state_data):
    """Add crime-type dropdown and expose crime_types to JS."""
    chart_data = {
        'labels': historical_data.index.strftime('%Y-%m').tolist() + forecast_data.index.strftime('%Y-%m').tolist(),
        'historical': historical_data.round(0).tolist(),
        'forecast': [None]*len(historical_data) + forecast_data.round(0).tolist(),
        'avg_monthly_crimes':stats['avg_monthly_crimes'],
        'latest_monthly_pred':stats['latest_monthly_pred'],
        'monthly_change':stats['monthly_change']
    }
    years_json = json.dumps(list(range(start_year,2029)))
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>…</head>
    <body>
      <div class="controls">
        <select id="stateSelect" onchange="updateChart()">
          <option value="">All States</option>
          {''.join(f'<option value="{s}">{s}</option>' for s in states)}
        </select>
        <select id="crimeSelect" onchange="updateChart()">
          <option value="">All Crime Types</option>
          {''.join(f'<option value="{c}">{c}</option>' for c in crime_types)}
        </select>
      </div>
      …
      <script>
        const chartData = {json.dumps(chart_data)};
        const stateData = {json.dumps(state_data)};
        const years = {years_json};
        const startYear = {start_year};
      </script>
    </body>
    </html>
    '''

def save_and_open_html(html):
    with open('monthly_crime_predictions.html','w',encoding='utf-8') as f:
        f.write(html)
    webbrowser.open('file://' + os.path.realpath('monthly_crime_predictions.html'))

def create_monthly_chart(daily_crimes, forecast):
    df = pd.read_csv('crime_data.csv')
    df['Date & Time'] = pd.to_datetime(df['Date & Time'])
    
    # 1) per‑state & crime‑type data
    states, crime_types, state_data = prepare_state_data(df)
    
    # 2) overall monthly series
    hist_m = daily_crimes.set_index('ds').resample('M')['y'].mean()
    fore_m = forecast.set_index('ds').resample('M')['yhat'].mean()
    cutoff = pd.Timestamp('2024-12-31')
    hist = hist_m[hist_m.index<=cutoff]
    fore = fore_m[fore_m.index>cutoff]
    
    stats = calculate_statistics(hist, fore)
    start_year = hist.index.min().year
    
    html = generate_html_content(hist, fore, stats, start_year, states, crime_types, state_data)
    save_and_open_html(html)

if __name__ == '__main__':
    df = pd.read_csv('crime_data.csv')
    df['Date & Time'] = pd.to_datetime(df['Date & Time'])
    # overall daily series
    daily = df.groupby('Date & Time').size().reset_index(name='y').rename(columns={'Date & Time':'ds'})
    model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=True)
    model.fit(daily)
    future = model.make_future_dataframe(periods=365*4)
    forecast = model.predict(future)
    create_monthly_chart(daily, forecast)
