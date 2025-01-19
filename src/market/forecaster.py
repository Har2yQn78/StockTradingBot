import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
from copy import deepcopy as dc
from datetime import datetime, timedelta


class LSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_stacked_layers):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_stacked_layers = num_stacked_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_stacked_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        batch_size = x.size(0)
        h0 = torch.zeros(self.num_stacked_layers, batch_size, self.hidden_size).to(device)
        c0 = torch.zeros(self.num_stacked_layers, batch_size, self.hidden_size).to(device)

        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out


def prepare_data(historical_data, lookback=7):
    # Convert QuerySet or list to DataFrame
    if isinstance(historical_data, (list, pd.DataFrame)):
        df = pd.DataFrame(historical_data)
    else:
        # Convert QuerySet to list of dicts, then to DataFrame
        df = pd.DataFrame(list(historical_data))

    if len(df) < lookback + 1:
        raise ValueError(f"Not enough historical data. Need at least {lookback + 1} days of data.")

    # Prepare time series data
    data = df[['time', 'close_price']].copy()
    data['time'] = pd.to_datetime(data['time']).dt.date

    # Create lookback features
    for i in range(1, lookback + 1):
        data[f'close_price(t-{i})'] = data['close_price'].shift(i)

    data.dropna(inplace=True)

    # Scale the data
    scaler = MinMaxScaler(feature_range=(-1, 1))
    values = data.drop('time', axis=1).values
    scaled_values = scaler.fit_transform(values)

    # Prepare X and y
    X = scaled_values[:, 1:]
    y = scaled_values[:, 0]

    # Flip X to get correct temporal order and ensure contiguous memory
    X = np.ascontiguousarray(np.flip(X, axis=1).copy())

    # Reshape for LSTM
    X = X.reshape((-1, lookback, 1))

    return X, y, scaler, data['time'].iloc[-1]


def train_model(X, y, epochs=45, batch_size=16):
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

    # Convert to PyTorch tensors
    X = torch.tensor(X).float().to(device)
    y = torch.tensor(y).reshape(-1, 1).float().to(device)

    # Create and configure model
    model = LSTM(1, 4, 1).to(device)
    loss_function = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    # Train the model
    model.train()
    for _ in range(epochs):
        for i in range(0, len(X), batch_size):
            batch_X = X[i:i + batch_size]
            batch_y = y[i:i + batch_size]

            output = model(batch_X)
            loss = loss_function(output, batch_y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    return model


def forecast_future(model, last_sequence, scaler, n_days=10, lookback=7):
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

    # Prepare last sequence
    last_sequence = torch.tensor(last_sequence).float().to(device)

    # Generate predictions
    predictions = []
    current_sequence = last_sequence[-1:]

    for _ in range(n_days):
        with torch.no_grad():
            next_day = model(current_sequence).cpu().numpy()[0][0]
        predictions.append(next_day)

        # Update sequence for next prediction
        new_sequence = current_sequence.cpu().numpy()[0][1:]
        new_sequence = np.append(new_sequence, next_day)
        current_sequence = torch.tensor(new_sequence.reshape(1, lookback, 1)).float().to(device)

    # Inverse transform predictions
    dummy_array = np.zeros((len(predictions), lookback + 1))
    dummy_array[:, 0] = predictions
    predictions = scaler.inverse_transform(dummy_array)[:, 0]

    return predictions


def get_stock_forecast(historical_data, forecast_days=10, lookback=7):
    """
    Main function to generate stock price forecasts
    """
    try:
        # Prepare data
        X, y, scaler, last_date = prepare_data(historical_data, lookback)

        # Train model
        model = train_model(X, y)

        # Generate forecast
        forecast_values = forecast_future(model, X, scaler, forecast_days, lookback)

        # Generate forecast dates
        forecast_dates = [(datetime.strptime(str(last_date), '%Y-%m-%d') + timedelta(days=i + 1)).strftime('%Y-%m-%d')
                          for i in range(forecast_days)]

        # Prepare response
        forecast_data = [
            {
                'date': date,
                'forecasted_price': float(price)
            }
            for date, price in zip(forecast_dates, forecast_values)
        ]

        return {
            'status': 'success',
            'forecast': forecast_data
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }