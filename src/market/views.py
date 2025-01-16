from django.shortcuts import render
from decouple import config
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import StockQuote, Company
from .services import get_stock_indicators
from datetime import datetime, timedelta
from django.utils import timezone
from .tasks import sync_company_stock_quotes, sync_historical_stock_data



@api_view(['GET'])
def sync_data(request, ticker):
    """
    API endpoint to sync historical stock data for a ticker.
    """
    try:
        # Verify API key is configured
        api_key = config("POLOGYON_API_KEY", default=None, cast=str)
        if not api_key:
            return Response({
                "error": "Polygon API key is not configured"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Basic connectivity test
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

        # Get or create company
        company = Company.objects.filter(ticker=ticker).first()
        if not company:
            company = Company.objects.create(ticker=ticker.upper())

        # Directly call sync_historical_stock_data
        sync_historical_stock_data(
            years_ago=1,  # Fetch data for the last year
            company_ids=[company.id],
            use_celery=False,
            verbose=True  # Enable verbose output for debugging
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
    API endpoint to fetch historical stock data for the last 90 days.
    """
    try:
        # Get query parameters
        days = int(request.query_params.get('days', 90))
        should_sync = request.query_params.get('sync', 'false').lower() == 'true'

        company = Company.objects.filter(ticker=ticker).first()
        if not company:
            return Response({"error": f"Ticker {ticker} not found"}, status=status.HTTP_404_NOT_FOUND)

        if should_sync:
            # Sync data before fetching
            sync_historical_stock_data(
                years_ago=1,
                company_ids=[company.id],
                use_celery=False,
                verbose=False
            )

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        historical_data = StockQuote.objects.filter(
            company=company,
            time__range=(start_date, end_date)
        ).order_by('time').values(
            'time', 'open_price', 'close_price', 'high_price', 'low_price',
            'raw_timestamp', 'number_of_trades', 'volume', 'volume_weighted_average'
        )
        return Response(list(historical_data), status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)