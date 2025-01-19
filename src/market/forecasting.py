from merlion.models.forecast.deep_ar import DeepARForecaster, DeepARConfig
from merlion.utils import TimeSeries
import pandas as pd
from typing import Tuple, Dict, Any
from datetime import datetime
from sklearn.metrics import mean_absolute_error
import numpy as np


def prepare_historical_data(data_list: list) -> pd.DataFrame:
    """Convert historical data list to DataFrame and prepare it for forecasting."""
    df = pd.DataFrame.from_records(data_list)
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df = df[['close_price']]

    df.index = df.index.tz_localize(None)

    df.fillna(method="ffill", inplace=True)
    df.fillna(method="bfill", inplace=True)
    df.dropna(inplace=True)

    return df


def create_deep_ar_model(n_past: int = 7, forecast_days: int = 14) -> DeepARForecaster:
    """Create and configure DeepAR model."""
    config = DeepARConfig(
        n_past=n_past,
        max_forecast_steps=forecast_days,
        target_seq_index=0,
        hidden_size=100,
        num_layers=2,
        learning_rate=0.0001,
        batch_size=16,
        num_epochs=11
    )
    return DeepARForecaster(config=config)


def forecast_stock_prices(historical_data: pd.DataFrame, forecast_days: int = 14) -> Dict[str, Any]:
    """
    Forecast stock prices using DeepAR model.

    Args:
        historical_data: DataFrame with historical stock prices
        forecast_days: Number of days to forecast

    Returns:
        Dictionary containing forecast results and metrics
    """
    try:
        time_series = TimeSeries.from_pd(historical_data)
        model = create_deep_ar_model(forecast_days=forecast_days)
        model.train(time_series)
        last_timestamp = historical_data.index[-1]
        future_timestamps = pd.date_range(
            start=last_timestamp,
            periods=forecast_days + 1,
            freq="D"
        )[1:]

        forecast, stderr = model.forecast(time_stamps=future_timestamps)
        forecast_df = forecast.to_pd()

        last_actual_values = historical_data["close_price"].iloc[-7:]
        last_forecasted_values = forecast_df["close_price"].iloc[:7]

        mae = None
        adjusted_forecast = forecast_df.copy()

        if len(last_actual_values) == len(last_forecasted_values):
            mae = mean_absolute_error(last_actual_values, last_forecasted_values)
            adjusted_forecast["adjusted_close_price"] = adjusted_forecast["close_price"] + np.sqrt(mae)

        forecast_data = []
        for timestamp, row in adjusted_forecast.iterrows():
            forecast_data.append({
                "date": timestamp.strftime("%Y-%m-%d"),
                "predicted_price": float(row["close_price"]),
                "adjusted_price": float(row.get("adjusted_close_price", row["close_price"]))
            })

        return {
            "forecast_data": forecast_data,
            "metrics": {
                "mean_absolute_error": float(mae) if mae is not None else None,
                "forecast_start_date": future_timestamps[0].strftime("%Y-%m-%d"),
                "forecast_end_date": future_timestamps[-1].strftime("%Y-%m-%d")
            }
        }

    except Exception as e:
        raise Exception(f"Forecasting failed: {str(e)}")