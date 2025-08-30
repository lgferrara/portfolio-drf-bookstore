import django_filters
from config.core.base_filters import BaseRangeFilterSet, BaseDateRangeFilterSet
from .models import Book, Cart, Order, OrderHistory
from .services.queryset_annotators import annotate_price, annotate_avg_rating


class BookFilter(BaseRangeFilterSet, BaseDateRangeFilterSet):
    """
    Filter class for querying books based on publication year, discount range,
    price range (via annotation), format, and availability.
    """
    range_fields = ['discount']
    date_fields = ['first_publication_year']
    is_bc = django_filters.BooleanFilter(field_name='is_bc', label='BCE')
    price_min = django_filters.NumberFilter(method='filter_price_min', label='Min Selling Price')
    price_max = django_filters.NumberFilter(method='filter_price_max', label='Max Selling Price')
    rating_min = django_filters.NumberFilter(method='filter_rating_min', label='Min Rating')
    rating_max = django_filters.NumberFilter(method='filter_rating_max', label='Max Rating')
    
    def filter_price_min(self, queryset, name, value):
        """
        Filters books whose discounted price is greater than the specified value.
        """
        return annotate_price(queryset).filter(price__gte=value)

    def filter_price_max(self, queryset, name, value):
        """
        Filters books whose discounted price is less than the specified value.
        """
        return annotate_price(queryset).filter(price__lte=value)


    def filter_rating_min(self, queryset, name, value):
        return annotate_avg_rating(queryset).filter(average_rating__gte=value)    


    def filter_rating_max(self, queryset, name, value):
        return annotate_avg_rating(queryset).filter(average_rating__lte=value)


    class Meta:
        model = Book
        fields = [
            'genre', 
            'book_format', 
            'language', 
            'is_new', 
            'stock',
        ]


class CartFilter(BaseRangeFilterSet):
    """
    Allows filtering cart entries by quantity and price ranges.
    Supports:
    - Min/max quantity
    - Min/max unit price
    - Min/max total price
    Also allows filtering by user (if permitted).
    """
    range_fields = ['quantity', 'unit_price', 'price']

    class Meta:
        model = Cart
        fields = ['user']


class OrderFilter(BaseRangeFilterSet, BaseDateRangeFilterSet):
    """
    Enables filtering orders by:
    - Total value (min/max)
    - Placement or order update date range
    - Assigned deliverer
    - Order status
    Also allows filtering by user ownership.
    """
    range_fields = ['total']
    date_fields = ['when_placed', 'when_last_update']


    class Meta:
        model = Order
        fields = ['user', 'deliverer', 'status']


class OrderHistoryFilter(BaseDateRangeFilterSet):
    """
    Filters order history records by the timestamp of the update,
    and optionally by related order or action description.
    Supports:
    - Start and end date filtering on the timestamp field
    - Exact matches on order and action fields
    """
    date_fields = ['timestamp']

    class Meta:
        model = OrderHistory
        fields = ['order', 'action']