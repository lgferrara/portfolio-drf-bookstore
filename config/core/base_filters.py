from django_filters.rest_framework import FilterSet
from django_filters import DateFilter, NumberFilter


class BaseDateRangeFilterSet(FilterSet):
    """
    A reusable base class for date range filtering on a given list or tuple of date fields.
    The iterable is to be delared as 'date_fields'.
    """
    date_fields = []
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'Meta') or not hasattr(cls.Meta, 'model'):
            raise TypeError(f"{cls.__name__} must define a Meta.model")
        for field in getattr(cls, 'date_fields', []):
            cls.base_filters[f"{field}_gte"] = DateFilter(
                field_name=field,
                lookup_expr='gte',
                label=f"{field.replace('_', ' ').title()} From"
            )
            cls.base_filters[f"{field}_lte"] = DateFilter(
                field_name=field,
                lookup_expr='lte',
                label=f"{field.replace('_', ' ').title()} To"
            )



class BaseRangeFilterSet(FilterSet):
    """
    A reusable base class for numeric range filtering on a given list or tuple of numeric fields.
    The iterable is to be delared as 'range_fields'.
    """
    range_fields = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'Meta') or not hasattr(cls.Meta, 'model'):
            raise TypeError(f"{cls.__name__} must define a Meta.model")
        for field in getattr(cls, 'range_fields', []):
            label = field.replace('_', ' ').title()
            cls.base_filters[f"{field}_gte"] = NumberFilter(
                field_name=field,
                lookup_expr='gte',
                label=f"Min {label}"
            )
            cls.base_filters[f"{field}_lte"] = NumberFilter(
                field_name=field,
                lookup_expr='lte',
                label=f"Max {label}"
            )