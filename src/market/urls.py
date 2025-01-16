from django.urls import path
from .views import analyze_stock, historical_stock_data, sync_data

urlpatterns = [
    path('analyze/<str:ticker>/', analyze_stock, name='analyze_stock'),
    path('historical/<str:ticker>/', historical_stock_data, name='historical_stock_data'),
    path('sync/<str:ticker>/', sync_data, name='sync_data'),
]