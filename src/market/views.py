from django.shortcuts import render
from decouple import config
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import StockQuote, Company
from .services import get_stock_indicators, get_daily_stock_quotes_queryset
from datetime import datetime, timedelta
from django.utils import timezone
from .tasks import sync_company_stock_quotes, sync_historical_stock_data
from .forecasting import forecast_stock_prices, prepare_historical_data


@api_view(['GET'])
def sync_data(request, ticker):
    """
    API endpoint to sync historical stock data for a ticker.
    """
    try:
        years_ago = int(request.query_params.get('years_ago', 1))
        api_key = config("POLOGYON_API_KEY", default=None, cast=str)
        if not api_key:
            return Response({
                "error": "Polygon API key is not configured"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        import urllib3
        http = urllib3.PoolManager()
        try:
            response = http.request('GET', 'https://api.polygon.io/v2/aggs/ticker/AAPL/prev?apiKey=' + api_key)
            if response.status != 200:
                return Response({
                    "error": f"Unable to connect to Polygon API. Status: {response.status}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except urllib3.exceptions.MaxRetryError as e:
            return Response({
                "error": f"Connection to Polygon API failed. Please check your internet connection and DNS settings. Details: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        company = Company.objects.filter(ticker=ticker).first()
        if not company:
            company = Company.objects.create(ticker=ticker.upper())

        sync_historical_stock_data(
            years_ago=years_ago,
            company_ids=[company.id],
            use_celery=False,
            verbose=True
        )

        return Response({
            "status": "success",
            "message": f"Data synced for {ticker}"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "error": f"Unexpected error: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def analyze_stock(request, ticker):
    try:
        # Check if sync is requested
        should_sync = request.query_params.get('sync', 'false').lower() == 'true'

        company = Company.objects.filter(ticker=ticker).first()
        if not company:
            return Response({"error": f"Ticker {ticker} not found"}, status=status.HTTP_404_NOT_FOUND)

        if should_sync:
            # Sync data before analysis
            sync_historical_stock_data(
                years_ago=1,
                company_ids=[company.id],
                use_celery=False,
                verbose=False
            )

        # Fetch stock indicators
        analysis_result = get_stock_indicators(ticker=ticker)
        return Response(analysis_result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def historical_stock_data(request, ticker):
    """
    API endpoint to fetch daily historical stock data.
    """
    try:
        days = int(request.query_params.get('days', 365))
        should_sync = request.query_params.get('sync', 'false').lower() == 'true'

        company = Company.objects.filter(ticker=ticker).first()
        if not company:
            return Response({"error": f"Ticker {ticker} not found"}, status=status.HTTP_404_NOT_FOUND)

        if should_sync:
            sync_historical_stock_data(
                years_ago=1,
                company_ids=[company.id],
                use_celery=False,
                verbose=False
            )

        historical_data = get_daily_stock_quotes_queryset(
            ticker,
            days=days
        ).order_by('time').values(
            'time', 'open_price', 'close_price', 'high_price', 'low_price',
            'raw_timestamp', 'number_of_trades', 'volume', 'volume_weighted_average'
        )

        return Response(list(historical_data), status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {"error": f"Invalid parameter: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def forecast_stock(request, ticker):
    """
    API endpoint to forecast stock prices using DeepAR model.
    """
    try:
        forecast_days = int(request.query_params.get('days', 14))
        historical_days = int(request.query_params.get('historical_days', 365))

        if forecast_days <= 0 or forecast_days > 30:
            return Response(
                {"error": "Forecast days must be between 1 and 30"},
                status=status.HTTP_400_BAD_REQUEST
            )

        company = Company.objects.filter(ticker=ticker).first()
        if not company:
            return Response(
                {"error": f"Ticker {ticker} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        historical_data_list = get_daily_stock_quotes_queryset(
            ticker,
            days=historical_days
        ).values(
            'time', 'close_price'
        )

        if not historical_data_list:
            return Response(
                {"error": "No historical data available"},
                status=status.HTTP_404_NOT_FOUND
            )

        historical_df = prepare_historical_data(historical_data_list)
        forecast_result = forecast_stock_prices(
            historical_df,
            forecast_days=forecast_days
        )

        return Response(forecast_result, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {"error": f"Invalid parameter: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Forecasting failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
