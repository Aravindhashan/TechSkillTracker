import logging
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go


SUPPORTED_ENGINES = (
    "auto",
    "sarimax",
    "prophet",
    "linear",
    "exponential_smoothing",
    "gradient_boosting",
    "lightgbm",
    "croston",
)

# Trained global models, keyed by a hash of the training data.
_GB_CACHE: dict = {}


def _has_statsmodels():
    try:
        import statsmodels  # noqa: F401
        return True
    except ImportError:
        return False


def _has_prophet():
    try:
        import prophet  # noqa: F401
        return True
    except ImportError:
        return False


def _has_gradient_boosting():
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: F401
        return True
    except ImportError:
        return False


def _has_lightgbm():
    try:
        import lightgbm  # noqa: F401
        return True
    except ImportError:
        return False


def _future_dates(monthly_data, months_ahead):
    return pd.date_range(
        start=monthly_data['Date'].iloc[-1],
        periods=months_ahead + 1,
        freq='MS'
    )[1:]


def _assemble_forecast(monthly_data, future_dates, forecast_values, lower=None, upper=None):
    forecast_values = np.clip(np.asarray(forecast_values, dtype=float), 0, None)

    result_df = pd.DataFrame({
        'Date': list(monthly_data['Date']) + list(future_dates),
        'Actual': list(monthly_data['Count']) + [None] * len(future_dates),
        'Forecast': [None] * len(monthly_data) + list(forecast_values)
    })

    if lower is not None:
        lower = np.clip(np.asarray(lower, dtype=float), 0, None)
        result_df['Lower_Bound'] = [None] * len(monthly_data) + list(lower)

    if upper is not None:
        upper = np.clip(np.asarray(upper, dtype=float), 0, None)
        result_df['Upper_Bound'] = [None] * len(monthly_data) + list(upper)

    return result_df


def _mape(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = actual != 0
    if mask.sum() == 0:
        return float("inf")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def _forecast_values(forecast_df):
    """Extract the predicted values from an assembled forecast frame."""
    return forecast_df[forecast_df['Forecast'].notna()]['Forecast'].values


# ---------------------------------------------------------------------------
# Per-skill monthly series
# ---------------------------------------------------------------------------


def _monthly_series(df, skill_name):
    skill_data = df[df['Tech Skill'] == skill_name].copy()
    skill_data['Date Posted'] = pd.to_datetime(skill_data['Date Posted'])
    monthly_data = skill_data.groupby(
        skill_data['Date Posted'].dt.to_period('M')
    ).size().reset_index()
    monthly_data['Date Posted'] = monthly_data['Date Posted'].dt.to_timestamp()
    monthly_data.columns = ['Date', 'Count']
    return monthly_data


# ---------------------------------------------------------------------------
# Per-skill engines
# ---------------------------------------------------------------------------


def _linear_forecast(monthly_data, months_ahead):
    x = np.arange(len(monthly_data))
    y = monthly_data['Count'].values.astype(float)
    if len(monthly_data) < 2:
        slope, intercept = 0.0, float(y[-1]) if len(y) else 0.0
    else:
        slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(len(monthly_data), len(monthly_data) + months_ahead)
    future_y = slope * future_x + intercept

    result_df = _assemble_forecast(
        monthly_data, _future_dates(monthly_data, months_ahead), future_y
    )
    result_df.attrs['engine'] = 'Linear Regression'
    return result_df


def _sarimax_forecast(monthly_data, months_ahead):
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    model = SARIMAX(
        monthly_data['Count'],
        order=(1, 1, 1),
        seasonal_order=(0, 0, 0, 0),
        enforce_stationarity=False,
        enforce_invertibility=False
    )
    fitted_model = model.fit(disp=False)
    forecast_result = fitted_model.get_forecast(steps=months_ahead)
    confidence = forecast_result.conf_int()

    result_df = _assemble_forecast(
        monthly_data,
        _future_dates(monthly_data, months_ahead),
        forecast_result.predicted_mean,
        confidence.iloc[:, 0],
        confidence.iloc[:, 1]
    )
    result_df.attrs['engine'] = 'SARIMAX'
    return result_df


def _exponential_smoothing_forecast(monthly_data, months_ahead):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    model = ExponentialSmoothing(monthly_data['Count'], trend='add', seasonal=None)
    fitted_model = model.fit()
    values = fitted_model.forecast(steps=months_ahead)

    result_df = _assemble_forecast(
        monthly_data, _future_dates(monthly_data, months_ahead), values
    )
    result_df.attrs['engine'] = 'Exponential Smoothing'
    return result_df


def _prophet_forecast(monthly_data, months_ahead):
    from prophet import Prophet

    logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

    prophet_df = monthly_data.rename(columns={'Date': 'ds', 'Count': 'y'})[['ds', 'y']]

    model = Prophet(
        yearly_seasonality='auto',
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.95
    )
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=months_ahead, freq='MS')
    forecast = model.predict(future).tail(months_ahead)

    result_df = _assemble_forecast(
        monthly_data,
        forecast['ds'].tolist(),
        forecast['yhat'].values,
        forecast['yhat_lower'].values,
        forecast['yhat_upper'].values
    )
    result_df.attrs['engine'] = 'Prophet'
    return result_df


def _croston_forecast(monthly_data, months_ahead, alpha=0.1):
    """Croston / SBA for intermittent (zero-heavy) demand series."""
    y = monthly_data['Count'].values.astype(float)

    demand_size = None  # smoothed non-zero demand size
    interval = None     # smoothed inter-arrival interval
    periods_since = 0
    for val in y:
        periods_since += 1
        if val > 0:
            if demand_size is None:
                demand_size = val
                interval = periods_since
            else:
                demand_size = demand_size + alpha * (val - demand_size)
                interval = interval + alpha * (periods_since - interval)
            periods_since = 0

    if demand_size is None or interval is None or interval == 0:
        forecast_value = 0.0
    else:
        # Syntetos-Boylan Approximation reduces the positive bias of plain Croston.
        forecast_value = (demand_size / interval) * (1 - alpha / 2.0)

    forecast = [max(0.0, forecast_value)] * months_ahead
    result_df = _assemble_forecast(
        monthly_data, _future_dates(monthly_data, months_ahead), forecast
    )
    result_df.attrs['engine'] = 'Croston (SBA)'
    return result_df


# ---------------------------------------------------------------------------
# Global gradient-boosting forecaster (one model across all skills)
# ---------------------------------------------------------------------------


def _build_panel(df):
    work = df.copy()
    work['Date Posted'] = pd.to_datetime(work['Date Posted'])
    work['month'] = work['Date Posted'].dt.to_period('M').dt.to_timestamp()

    counts = work.groupby(['Tech Skill', 'month']).size().reset_index(name='count')

    skills = sorted(work['Tech Skill'].dropna().unique().tolist())
    months = pd.date_range(work['month'].min(), work['month'].max(), freq='MS')
    grid = pd.MultiIndex.from_product(
        [skills, months], names=['Tech Skill', 'month']
    ).to_frame(index=False)
    panel = grid.merge(counts, on=['Tech Skill', 'month'], how='left').fillna(0)
    panel['count'] = panel['count'].astype(int)

    panel = panel.sort_values(['Tech Skill', 'month']).reset_index(drop=True)
    for lag in (1, 2, 3, 6, 12):
        panel[f'lag_{lag}'] = panel.groupby('Tech Skill')['count'].shift(lag)

    panel['month_num'] = panel['month'].dt.month
    panel['quarter'] = panel['month'].dt.quarter

    skill_dummies = pd.get_dummies(panel['Tech Skill'], prefix='skill', dtype=int)
    panel = pd.concat([panel, skill_dummies], axis=1)

    return panel, skills, months, list(skill_dummies.columns)


def _gradient_boosting_forecast(df, skill_name, months_ahead, cutoff_date=None):
    work = df.copy()
    work['Date Posted'] = pd.to_datetime(work['Date Posted'])
    if cutoff_date is not None:
        work = work[work['Date Posted'] <= pd.Timestamp(cutoff_date)]

    if work.empty or skill_name not in set(work['Tech Skill'].dropna()):
        raise ValueError("skill not present in training data")

    cache_key = (
        int(work.shape[0]),
        tuple(sorted(work['Tech Skill'].dropna().unique().tolist())),
        str(work['Date Posted'].min()),
        str(work['Date Posted'].max()),
    )
    cached = _GB_CACHE.get(cache_key)
    if cached is None:
        panel, skills, months, skill_cols = _build_panel(work)
        feature_cols = (
            ['lag_1', 'lag_2', 'lag_3', 'lag_6', 'lag_12', 'month_num', 'quarter']
            + skill_cols
        )
        train = panel.dropna(subset=['lag_1', 'lag_2', 'lag_3'])
        if len(train) < 20:
            raise ValueError("insufficient training rows for gradient boosting")

        X = train[feature_cols].fillna(0)
        y = train['count'].values.astype(float)

        if _has_lightgbm():
            from lightgbm import LGBMRegressor
            model = LGBMRegressor(
                n_estimators=300, learning_rate=0.05, reg_lambda=1.0,
                random_state=42, verbose=-1
            )
            engine_name = 'Gradient Boosting (LightGBM)'
        else:
            from sklearn.ensemble import HistGradientBoostingRegressor
            model = HistGradientBoostingRegressor(
                max_iter=300, learning_rate=0.05, l2_regularization=1.0, random_state=42
            )
            engine_name = 'Gradient Boosting (sklearn HGBR)'

        model.fit(X, y)
        cached = (model, feature_cols, panel, skills, skill_cols, months, engine_name)
        _GB_CACHE[cache_key] = cached

    model, feature_cols, panel, skills, skill_cols, months, engine_name = cached

    if skill_name not in skills:
        raise ValueError("skill not present in panel")

    skill_panel = panel[panel['Tech Skill'] == skill_name].sort_values('month')
    series = [float(v) for v in skill_panel['count'].values]
    last_month = skill_panel['month'].iloc[-1]

    preds = []
    for i in range(months_ahead):
        target_month = last_month + pd.DateOffset(months=i + 1)
        lag1 = series[-1] if len(series) >= 1 else 0.0
        lag2 = series[-2] if len(series) >= 2 else 0.0
        lag3 = series[-3] if len(series) >= 3 else 0.0
        lag6 = series[-6] if len(series) >= 6 else (series[0] if series else 0.0)
        lag12 = series[-12] if len(series) >= 12 else (series[0] if series else 0.0)

        row = {
            'lag_1': lag1, 'lag_2': lag2, 'lag_3': lag3,
            'lag_6': lag6, 'lag_12': lag12,
            'month_num': target_month.month,
            'quarter': target_month.quarter,
        }
        for sc in skill_cols:
            row[sc] = 1 if sc == f'skill_{skill_name}' else 0
        X_row = pd.DataFrame([row])[feature_cols].fillna(0)
        pred = float(model.predict(X_row)[0])
        pred = max(0.0, pred)
        preds.append(pred)
        series.append(pred)

    future_dates = pd.date_range(start=last_month, periods=months_ahead + 1, freq='MS')[1:]
    monthly_skill = pd.DataFrame({
        'Date': skill_panel['month'].values,
        'Count': skill_panel['count'].values,
    })
    result_df = _assemble_forecast(monthly_skill, future_dates, preds)
    result_df.attrs['engine'] = engine_name
    return result_df


# ---------------------------------------------------------------------------
# Backtesting
# ---------------------------------------------------------------------------


def backtest_engines(df, skill_name, holdout=3):
    monthly = _monthly_series(df, skill_name)
    if len(monthly) < holdout + 3:
        return {}

    train = monthly.iloc[:-holdout].reset_index(drop=True)
    test = monthly.iloc[-holdout:].reset_index(drop=True)
    test_counts = test['Count'].values

    results = {}

    def _record(name, forecast_fn, *args, **kwargs):
        try:
            fc = forecast_fn(*args, **kwargs)
            pred = _forecast_values(fc)
            if len(pred) != len(test_counts):
                return
            results[name] = _mape(test_counts, pred)
        except Exception:
            pass

    _record('linear', _linear_forecast, train, holdout)
    _record('croston', _croston_forecast, train, holdout)

    if _has_statsmodels() and len(train) >= 4:
        _record('sarimax', _sarimax_forecast, train, holdout)
    if _has_prophet():
        _record('prophet', _prophet_forecast, train, holdout)
    if _has_gradient_boosting():
        try:
            cutoff = train['Date'].iloc[-1]
            fc = _gradient_boosting_forecast(df, skill_name, holdout, cutoff_date=cutoff)
            pred = _forecast_values(fc)
            if len(pred) == len(test_counts):
                results['gradient_boosting'] = _mape(test_counts, pred)
        except Exception:
            pass

    return results


def _select_engine(mape_results, available):
    if mape_results:
        candidates = {k: v for k, v in mape_results.items()
                      if k in available and np.isfinite(v)}
        if candidates:
            return min(candidates, key=candidates.get)
    for name in ('gradient_boosting', 'sarimax', 'prophet', 'croston',
                 'exponential_smoothing', 'linear'):
        if name in available:
            return name
    return 'linear'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@st.cache_resource
def forecast_skill_demand(df, skill_name, months_ahead=12, model_type="auto"):
    monthly_data = _monthly_series(df, skill_name)

    if len(monthly_data) < 2:
        return None, "Need at least 2 months of data for forecasting"

    skill_rows = df[df['Tech Skill'] == skill_name]
    if len(skill_rows) < 3:
        return None, "Insufficient data for forecasting (need at least 3 data points)"

    available = set()
    if _has_gradient_boosting():
        available.add('gradient_boosting')
    if _has_statsmodels():
        available.add('sarimax')
        available.add('exponential_smoothing')
    if _has_prophet():
        available.add('prophet')
    available.add('linear')
    available.add('croston')

    if model_type not in SUPPORTED_ENGINES:
        return None, f"Unknown forecasting engine '{model_type}'"

    mape_results = {}
    holdout = min(3, len(monthly_data) - 2)
    if holdout >= 1:
        mape_results = backtest_engines(df, skill_name, holdout=holdout)

    if model_type == "auto":
        available = available - {'exponential_smoothing'}
        chosen = _select_engine(mape_results, available)
        selected_by = 'mape' if mape_results else 'availability'
    else:
        chosen = model_type
        selected_by = 'manual'

    engine_impl = {
        'sarimax': 'sarimax',
        'prophet': 'prophet',
        'linear': 'linear',
        'exponential_smoothing': 'exponential_smoothing',
        'gradient_boosting': 'gradient_boosting',
        'lightgbm': 'gradient_boosting',
        'croston': 'croston',
    }.get(chosen, 'linear')

    # Auto must not pick exponential_smoothing (outside the spec's engine set).
    if model_type == "auto" and engine_impl == 'exponential_smoothing':
        engine_impl = 'linear'

    failures = []

    def _run(name):
        if name == 'sarimax':
            if not _has_statsmodels() or len(monthly_data) < 4:
                return None, "statsmodels unavailable or <4 months"
            return _sarimax_forecast(monthly_data, months_ahead), None
        if name == 'prophet':
            if not _has_prophet():
                return None, "prophet unavailable"
            return _prophet_forecast(monthly_data, months_ahead), None
        if name == 'exponential_smoothing':
            if not _has_statsmodels() or len(monthly_data) < 3:
                return None, "statsmodels unavailable or <3 months"
            return _exponential_smoothing_forecast(monthly_data, months_ahead), None
        if name == 'gradient_boosting':
            if not _has_gradient_boosting():
                return None, "gradient boosting unavailable"
            try:
                return _gradient_boosting_forecast(df, skill_name, months_ahead), None
            except Exception as exc:
                return None, str(exc)
        if name == 'croston':
            return _croston_forecast(monthly_data, months_ahead), None
        return _linear_forecast(monthly_data, months_ahead), None

    if model_type != "auto":
        result, err = _run(engine_impl)
        if result is not None:
            result.attrs['requested_engine'] = model_type
            result.attrs['mape_comparison'] = mape_results
            result.attrs['selected_by'] = selected_by
            return result, "success"
        failures.append(err or "unknown error")

    order = [engine_impl] + [
        n for n in ('gradient_boosting', 'sarimax', 'prophet', 'croston', 'linear')
        if n != engine_impl
    ]
    for name in order:
        result, err = _run(name)
        if result is not None:
            result.attrs['requested_engine'] = model_type
            result.attrs['mape_comparison'] = mape_results
            result.attrs['selected_by'] = selected_by
            return result, "success"
        if err:
            failures.append(f"{name}: {err}")

    if failures:
        st.info("Falling back to linear regression. " + " | ".join(failures))

    result = _linear_forecast(monthly_data, months_ahead)
    result.attrs['requested_engine'] = model_type
    result.attrs['mape_comparison'] = mape_results
    result.attrs['selected_by'] = selected_by
    return result, "success"


def create_forecast_chart(forecast_df, skill_name):
    fig = go.Figure()

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
    insights = []

    historical = forecast_df[forecast_df['Actual'].notna()]
    forecast_only = forecast_df[forecast_df['Forecast'].notna() & forecast_df['Actual'].isna()]

    if not historical.empty and not forecast_only.empty:
        last_historical = historical['Actual'].iloc[-1]
        last_forecast = forecast_only['Forecast'].iloc[-1]
        horizon = len(forecast_only)

        if last_historical and last_historical != 0:
            growth = ((last_forecast - last_historical) / last_historical) * 100
        else:
            growth = 0.0

        if growth > 10:
            insights.append(f"📈 **Growing Demand**: {skill_name} is projected to grow by {growth:.1f}% over the next {horizon} months")
        elif growth < -10:
            insights.append(f"📉 **Declining Demand**: {skill_name} is projected to decline by {abs(growth):.1f}% over the next {horizon} months")
        else:
            insights.append(f"📊 **Stable Demand**: {skill_name} is projected to remain stable with {abs(growth):.1f}% change")

        avg_forecast = forecast_only['Forecast'].mean()
        insights.append(f"💼 **Average Monthly Openings**: Expected ~{int(avg_forecast)} job postings per month")

        engine = forecast_df.attrs.get('engine', 'Unknown')
        insights.append(f"🔧 **Engine used**: {engine}")

        comparison = forecast_df.attrs.get('mape_comparison') or {}
        if comparison:
            insights.append("📏 **Backtest MAPE (lower is better):** " + ", ".join(
                f"{name}={value:.1f}%" for name, value in sorted(comparison.items())
            ))

        selected_by = forecast_df.attrs.get('selected_by')
        if selected_by:
            insights.append(f"🎯 **Selection**: {selected_by}")

    return insights
