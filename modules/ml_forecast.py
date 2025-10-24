import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import timedelta


@st.cache_resource
def forecast_skill_demand(df, skill_name, months_ahead=12):
    """
    Forecast skill demand using Prophet for time-series forecasting
    Falls back to linear regression if Prophet is not available
    """
    try:
        from prophet import Prophet
        use_prophet = True
    except ImportError:
        use_prophet = False
        st.warning("Prophet not available, using linear regression for forecasting")
    
    # Filter data for specific skill
    skill_data = df[df['Tech Skill'] == skill_name].copy()
    
    if len(skill_data) < 3:
        return None, "Insufficient data for forecasting (need at least 3 data points)"
    
    # Group by month
    skill_data['Date Posted'] = pd.to_datetime(skill_data['Date Posted'])
    monthly_data = skill_data.groupby(
        skill_data['Date Posted'].dt.to_period('M')
    ).size().reset_index()
    monthly_data['Date Posted'] = monthly_data['Date Posted'].dt.to_timestamp()
    monthly_data.columns = ['Date', 'Count']
    
    if len(monthly_data) < 2:
        return None, "Need at least 2 months of data for forecasting"
    
    if use_prophet:
        # Use Prophet for forecasting
        prophet_df = monthly_data.rename(columns={'Date': 'ds', 'Count': 'y'})
        
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.95
        )
        
        model.fit(prophet_df)
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=months_ahead, freq='MS')
        forecast = model.predict(future)
        
        # Combine historical and forecast
        result_df = pd.DataFrame({
            'Date': forecast['ds'],
            'Actual': None,
            'Forecast': forecast['yhat'],
            'Lower_Bound': forecast['yhat_lower'],
            'Upper_Bound': forecast['yhat_upper']
        })
        
        # Fill actual values
        for idx, row in prophet_df.iterrows():
            result_df.loc[result_df['Date'] == row['ds'], 'Actual'] = row['y']
        
        return result_df, "success"
    
    else:
        # Fallback to linear regression
        x = np.arange(len(monthly_data))
        y = monthly_data['Count'].values
        
        # Fit linear model
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs
        
        # Create future months
        last_date = monthly_data['Date'].iloc[-1]
        future_months = [last_date + timedelta(days=30*i) for i in range(1, months_ahead + 1)]
        
        # Predict
        future_x = np.arange(len(monthly_data), len(monthly_data) + months_ahead)
        future_y = slope * future_x + intercept
        future_y = np.maximum(future_y, 0)  # Ensure non-negative
        
        # Combine historical and forecast
        all_dates = list(monthly_data['Date']) + future_months
        all_actual = list(monthly_data['Count']) + [None] * months_ahead
        all_forecast = [None] * len(monthly_data) + list(future_y)
        
        result_df = pd.DataFrame({
            'Date': all_dates,
            'Actual': all_actual,
            'Forecast': all_forecast
        })
        
        return result_df, "success"


def create_forecast_chart(forecast_df, skill_name):
    """
    Create interactive Plotly chart for forecast visualization
    """
    fig = go.Figure()
    
    # Historical data
    historical = forecast_df[forecast_df['Actual'].notna()]
    if not historical.empty:
        fig.add_trace(go.Scatter(
            x=historical['Date'],
            y=historical['Actual'],
            mode='lines+markers',
            name='Historical',
            line=dict(color='blue', width=2),
            marker=dict(size=8)
        ))
    
    # Forecast data
    forecast = forecast_df[forecast_df['Forecast'].notna()]
    if not forecast.empty:
        fig.add_trace(go.Scatter(
            x=forecast['Date'],
            y=forecast['Forecast'],
            mode='lines+markers',
            name='Forecast',
            line=dict(color='orange', width=2, dash='dash'),
            marker=dict(size=8, symbol='diamond')
        ))
    
    # Confidence interval (if available)
    if 'Upper_Bound' in forecast_df.columns and forecast_df['Upper_Bound'].notna().any():
        fig.add_trace(go.Scatter(
            x=forecast['Date'],
            y=forecast['Upper_Bound'],
            mode='lines',
            name='Upper Bound',
            line=dict(width=0),
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=forecast['Date'],
            y=forecast['Lower_Bound'],
            mode='lines',
            name='Confidence Interval',
            line=dict(width=0),
            fillcolor='rgba(255, 165, 0, 0.2)',
            fill='tonexty'
        ))
    
    fig.update_layout(
        title=f'Demand Forecast for {skill_name}',
        xaxis_title='Date',
        yaxis_title='Job Openings',
        hovermode='x unified',
        height=500
    )
    
    return fig


def get_forecast_insights(forecast_df, skill_name):
    """
    Generate insights from forecast data
    """
    insights = []
    
    # Get last historical value and last forecast value
    historical = forecast_df[forecast_df['Actual'].notna()]
    forecast_only = forecast_df[forecast_df['Forecast'].notna() & forecast_df['Actual'].isna()]
    
    if not historical.empty and not forecast_only.empty:
        last_historical = historical['Actual'].iloc[-1]
        last_forecast = forecast_only['Forecast'].iloc[-1]
        
        growth = ((last_forecast - last_historical) / last_historical) * 100
        
        if growth > 10:
            insights.append(f"📈 **Growing Demand**: {skill_name} is projected to grow by {growth:.1f}% over the next 12 months")
        elif growth < -10:
            insights.append(f"📉 **Declining Demand**: {skill_name} is projected to decline by {abs(growth):.1f}% over the next 12 months")
        else:
            insights.append(f"📊 **Stable Demand**: {skill_name} is projected to remain stable with {abs(growth):.1f}% change")
        
        # Average forecast
        avg_forecast = forecast_only['Forecast'].mean()
        insights.append(f"💼 **Average Monthly Openings**: Expected ~{int(avg_forecast)} job postings per month")
    
    return insights
