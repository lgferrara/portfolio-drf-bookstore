from django.contrib import admin
from .models import Genre, Stock, BookFormat, OrderStatus, Country
# Register your models here.

admin.site.register([Genre, Stock, BookFormat, OrderStatus, Country])