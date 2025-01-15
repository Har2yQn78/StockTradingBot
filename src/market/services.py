from django.db.models import (
    Avg,
    F,
    RowRange,
    Window,
    Max,
    Min,
    ExpressionWrapper,
    DecimalField,
    Case,
    When,
    Value,
    StdDev
)
from django.db.models.functions import TruncDate, FirstValue, Lag, Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from market.models import StockQuote
import pandas as pd


def get_daily_stock_quotes_queryset(ticker, days=28, use_bucket=False):
    now = timezone.now()
    start_date = now - timedelta(days=days)
    end_date = now
    lastest_daily_timestamps = (
        StockQuote.objects.filter(company__ticker=ticker, time__range=(start_date - timedelta(days=40), end_date))
        .annotate(date=TruncDate('time'))
        .values('company', 'date')
        .annotate(latest_time=Max('time'))
        .values('company', 'date', 'latest_time')
        .order_by('date')
    )
    acutal_timestamps = [x['latest_time'] for x in lastest_daily_timestamps]
    qs = StockQuote.timescale.filter(
        company__ticker=ticker,
        time__range=(start_date, end_date),
        time__in=acutal_timestamps
    )
    if use_bucket:
        return qs.time_bucket('time', '1 day')
    return qs


def get_daily_moving_averages(ticker, days=28, queryset=None):
    if queryset is None:
        queryset = get_daily_stock_quotes_queryset(ticker=ticker, days=days)
    obj = queryset.annotate(
        ma_5=Window(
            expression=Avg('close_price'),
            order_by=F('time').asc(),
            frame=RowRange(start=-4, end=0),
        ),
        ma_20=Window(
            expression=Avg('close_price'),
            order_by=F('time').asc(),
            frame=RowRange(start=-19, end=0),
        )
    ).order_by('-time').first()
    if not obj:
        return None
    ma_5 = obj.ma_5
    ma_20 = obj.ma_20
    if ma_5 is None or ma_20 is None:
        return None
    if ma_5 <= 0 or ma_20 <= 0:
        return None
    return {
        "ma_5": float(round(ma_5, 4)),
        "ma_20": float(round(ma_20, 4))
    }


def get_price_target(ticker, days=28, queryset=None):
    """
    Simplified price target calculation
    """
    if queryset is None:
        queryset = get_daily_stock_quotes_queryset(ticker, days=days)
    daily_data = (
        queryset
        .annotate(
            latest_price=Window(
                expression=FirstValue('close_price'),
                order_by=F('time').desc()
            )
        )
        .aggregate(
            current_price=Max('latest_price'),
            avg_price=Avg('close_price'),
            highest=Max('high_price'),
            lowest=Min('low_price')
        )
    )

    if not daily_data:
        return None
    current_price = float(daily_data['current_price'])
    avg_price = float(daily_data['avg_price'])
    price_range = float(daily_data['highest']) - float(daily_data['lowest'])

    # Simple target based on average price and recent range
    conservative_target = current_price + (price_range * 0.382)  # 38.2% Fibonacci
    aggressive_target = current_price + (price_range * 0.618)  # 61.8% Fibonacci

    return {
        'current_price': round(current_price, 4),
        'conservative_target': round(conservative_target, 4),
        'aggressive_target': round(aggressive_target, 4),
        'average_price': round(avg_price, 4)
    }


def get_volume_trend(ticker, days=28, queryset=None):
    """
    Analyze recent volume trends
    """
    if queryset is None:
        queryset = get_daily_stock_quotes_queryset(ticker=ticker, days=days)
    start = -(days - 1)
    data = queryset.annotate(
        avg_volume=Window(
            expression=Avg('volume'),
            order_by=F('time').asc(),
            frame=RowRange(start=start, end=0)
        )
    ).order_by('-time').first()

    if not data:
        return None
    vol = data.volume
    avg_vol = data.avg_volume
    volume_change = 0
    if vol is None or avg_vol is None:
        return None
    if vol > 0 and avg_vol > 0:
        volume_change = ((vol - avg_vol) / avg_vol) * 100
    return {
        'avg_volume': float(avg_vol),
        'latest_volume': int(vol),
        'volume_change_percent': float(volume_change)
    }


def calculate_rsi(ticker, days=28, queryset=None, period=14):
    """
    Calculate Relative Strength Index (RSI) using Django ORM.

    Args:
        ticker (str): Stock ticker symbol
        days (int): Days in the price data (default: 28)
        queryset (list): Stock Quote querset
        period (int): RSI period (default: 14)

    Returns:
        dict: RSI value and component calculations
    """
    # Get daily price data
    if period is None:
        period = int(days / 4)
    if queryset is None:
        queryset = get_daily_stock_quotes_queryset(ticker, days=days, use_bucket=True)

    # Calculate price changes and gains/losses with explicit decimal conversion
    movement = queryset.annotate(
        closing_price=ExpressionWrapper(
            F('close_price'),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        ),
        prev_close=Window(
            expression=Lag('close_price'),
            order_by=F('bucket').asc(),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        )
    ).annotate(
        price_change=ExpressionWrapper(
            F('close_price') - F('prev_close'),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        ),
        gain=Case(
            When(price_change__gt=0,
                 then=ExpressionWrapper(
                     F('price_change'),
                     output_field=DecimalField(max_digits=10, decimal_places=4)
                 )),
            default=Value(0, output_field=DecimalField(max_digits=10, decimal_places=4)),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        ),
        loss=Case(
            When(price_change__lt=0,
                 then=ExpressionWrapper(
                     -F('price_change'),
                     output_field=DecimalField(max_digits=10, decimal_places=4)
                 )),
            default=Value(0, output_field=DecimalField(max_digits=10, decimal_places=4)),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        )
    )

    # Calculate initial averages for the first period
    initial_avg = movement.exclude(prev_close__isnull=True)[:period].aggregate(
        avg_gain=Coalesce(
            ExpressionWrapper(
                Avg('gain'),
                output_field=DecimalField(max_digits=10, decimal_places=4)
            ),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=4))
        ),
        avg_loss=Coalesce(
            ExpressionWrapper(
                Avg('loss'),
                output_field=DecimalField(max_digits=10, decimal_places=4)
            ),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=4))
        )
    )

    # Get subsequent data points for EMA calculation
    subsequent_data = list(movement.exclude(prev_close__isnull=True)[period:].values('gain', 'loss'))

    # Calculate EMA-based RSI
    avg_gain = initial_avg['avg_gain']
    avg_loss = initial_avg['avg_loss']
    alpha = Decimal(1 / period)  # Smoothing factor

    # Update moving averages using EMA formula
    for data in subsequent_data:
        avg_gain = (avg_gain * (1 - alpha) + data['gain'] * alpha)
        avg_loss = (avg_loss * (1 - alpha) + data['loss'] * alpha)

    # Prevent division by zero
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    return {
        'rsi': round(float(rsi), 4),
        'avg_gain': round(float(avg_gain), 4),
        'avg_loss': round(float(avg_loss), 4),
        'period': period,
        'days': days,
    }


def calculate_macd(ticker, days=None, queryset=None, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate the Moving Average Convergence Divergence (MACD) for a given stock.

    Args:
        ticker (str): Stock ticker symbol
        days (int): Number of days to analyze
        queryset (QuerySet): Optional pre-filtered queryset
        fast_period (int): Period for fast EMA (default: 12)
        slow_period (int): Period for slow EMA (default: 26)
        signal_period (int): Period for signal line (default: 9)

    Returns:
        dict: MACD indicators including MACD line and signal line
    """

    if queryset is None:
        queryset = get_daily_stock_quotes_queryset(ticker, days=days)

    # Get the closing prices in ascending order
    prices_data = list(queryset.order_by('time').values('close_price'))

    if not prices_data:
        return None

    # Convert to pandas DataFrame for easier calculation
    df = pd.DataFrame(prices_data)

    # Calculate EMAs
    ema_fast = df['close_price'].ewm(span=fast_period, adjust=False).mean()
    ema_slow = df['close_price'].ewm(span=slow_period, adjust=False).mean()

    # Calculate MACD line
    macd_line = ema_fast - ema_slow

    # Calculate signal line
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    # Get the most recent values
    latest_macd = float(macd_line.iloc[-1])
    latest_signal = float(signal_line.iloc[-1])

    return {
        'macd_line': latest_macd,
        'signal_line': latest_signal,
        'histogram': latest_macd - latest_signal
    }


def calculate_bollinger_bands(ticker, days=28, period=20, num_std=2, queryset=None):
    """
    Calculate Bollinger Bands using Django ORM.
    """
    if queryset is None:
        queryset = get_daily_stock_quotes_queryset(ticker, days=days)

    bb_data = queryset.annotate(
        sma=Window(
            expression=Avg('close_price'),
            order_by=F('time').asc(),
            frame=RowRange(start=-(period-1), end=0),
        ),
        std_dev=Window(
            expression=StdDev('close_price'),
            order_by=F('time').asc(),
            frame=RowRange(start=-(period-1), end=0),
        )
    ).annotate(
        upper_band=ExpressionWrapper(
            F('sma') + (F('std_dev') * Value(num_std)),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        ),
        lower_band=ExpressionWrapper(
            F('sma') - (F('std_dev') * Value(num_std)),
            output_field=DecimalField(max_digits=10, decimal_places=4)
        )
    ).order_by('-time').first()

    if not bb_data:
        return None

    return {
        'middle_band': float(round(bb_data.sma, 4)),
        'upper_band': float(round(bb_data.upper_band, 4)),
        'lower_band': float(round(bb_data.lower_band, 4))
    }


def get_stock_indicators(ticker="AAPL", days=30):
    queryset = get_daily_stock_quotes_queryset(ticker, days=days)
    if queryset.count() == 0:
        raise Exception(f"Data for {ticker} not found")

    # Get all indicators
    averages = get_daily_moving_averages(ticker, days=days, queryset=queryset)
    price_target = get_price_target(ticker, days=days, queryset=queryset)
    volume_trend = get_volume_trend(ticker, days=days, queryset=queryset)
    rsi_data = calculate_rsi(ticker, days=days, period=14)
    macd_data = calculate_macd(ticker, days=days, queryset=queryset)
    bollinger_data = calculate_bollinger_bands(ticker, days=days, queryset=queryset)

    signals = []
    signal_weights = {
        'ma_crossover': 2.0,    # Moving average crossover is a strong signal
        'price_target': 1.5,    # Price targets are important but less reliable
        'volume': 1.0,          # Volume confirms other signals
        'rsi': 1.5,            # RSI is reliable for overbought/oversold
        'macd': 1.5,           # MACD helps confirm trends
        'bollinger': 1.0       # Bollinger helps with volatility
    }

    # Moving Average Signal
    if averages.get('ma_5') > averages.get('ma_20'):
        signals.append(1 * signal_weights['ma_crossover'])
    else:
        signals.append(-1 * signal_weights['ma_crossover'])

    # Price Target Signal
    if price_target.get('current_price') < price_target.get('conservative_target'):
        signals.append(1 * signal_weights['price_target'])
    else:
        signals.append(-1 * signal_weights['price_target'])

    # Volume Signal
    vol_change = volume_trend.get("volume_change_percent")
    if vol_change > 20:
        signals.append(1 * signal_weights['volume'])
    elif vol_change < -20:
        signals.append(-1 * signal_weights['volume'])
    else:
        signals.append(0)

    # RSI Signal
    rsi = rsi_data.get('rsi')
    if rsi > 70:
        signals.append(-1 * signal_weights['rsi'])
    elif rsi < 30:
        signals.append(1 * signal_weights['rsi'])
    else:
        signals.append(0)

    # MACD Signal
    if macd_data:
        if macd_data['macd_line'] > 0:
            signals.append(1 * signal_weights['macd'])
        else:
            signals.append(-1 * signal_weights['macd'])

    # Bollinger Bands Signal
    if bollinger_data:
        current_price = price_target.get('current_price')
        if current_price < bollinger_data['lower_band']:
            signals.append(1 * signal_weights['bollinger'])
        elif current_price > bollinger_data['upper_band']:
            signals.append(-1 * signal_weights['bollinger'])
        else:
            signals.append(0)

    # Calculate weighted score
    weighted_score = sum(signals)
    max_possible_score = sum(signal_weights.values())
    normalized_score = (weighted_score / max_possible_score) * 10  # Scale to -10 to 10

    return {
        "score": round(normalized_score, 2),
        "ticker": ticker,
        "indicators": {
            **averages,
            **price_target,
            **volume_trend,
            **rsi_data,
            "macd": macd_data,
            "bollinger": bollinger_data
        },
        "recommendation": "BUY" if normalized_score >= 3 else "SELL" if normalized_score <= -3 else "HOLD"
    }