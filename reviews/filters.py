from config.core.base_filters import BaseRangeFilterSet, BaseDateRangeFilterSet
from .models import Review

class ReviewFilter(BaseRangeFilterSet, BaseDateRangeFilterSet):
    """
    Allows filtering review entries by rating and date ranges.
    Supports:
    - Min/max rating
    - Review creation or update date range
    Also allows filtering by user (if permitted).
    """
    range_fields = ['rating']
    date_fields = ['created_at', 'updated_at']

    class Meta:
        model = Review
        fields = ['user']