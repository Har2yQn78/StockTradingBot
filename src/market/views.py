from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import StockQuote, Company
from .services import get_stock_indicators
from datetime import datetime, timedelta
from django.utils import timezone

@api_view(['GET'])
def analyze_stock(request, ticker):
    try:
        company = Company.objects.filter(ticker=ticker).first()
        if not company:
            return Response({"error": f"Ticker {ticker} not found"}, status=status.HTTP_404_NOT_FOUND)

        # Fetch stock indicators
        analysis_result = get_stock_indicators(ticker=ticker)
        return Response(analysis_result, status=status.HTTP_200_OK)
    except Exception as e:
        # Handle other errors
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def historical_stock_data(request, ticker):
    """
    API endpoint to fetch historical stock data for the last 90 days.
    """
    try:
        company = Company.objects.filter(ticker=ticker).first()
        if not company:
            return Response({"error": f"Ticker {ticker} not found"}, status=status.HTTP_404_NOT_FOUND)

        end_date = timezone.now()
        start_date = end_date - timedelta(days=90)

        historical_data = StockQuote.objects.filter(
            company=company,
            time__range=(start_date, end_date)
        ).order_by('time').values(
            'time', 'open_price', 'close_price', 'high_price', 'low_price', 'raw_timestamp', 'number_of_trades',
            'volume', 'volume_weighted_average'
        )
        return Response(list(historical_data), status=status.HTTP_200_OK)
    except Exception as e:
        # Handle other errors
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)