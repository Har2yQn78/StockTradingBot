from django.contrib import admin
from .models import StockQuote, Company

# Register your models here.
admin.site.register(Company)

class StockQuoteAdmin(admin.ModelAdmin):
    list_display = ['get_company_ticker', 'close_price', 'time']  # Use a method for related field
    list_filter = ['company__ticker', 'time']  # Corrected syntax for list_filter

    def get_company_ticker(self, obj):
        return obj.company.ticker  # Access the related field
    get_company_ticker.short_description = 'Company Ticker'  # Optional: Set column header

admin.site.register(StockQuote, StockQuoteAdmin)
