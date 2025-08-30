from django.db.models import Avg, F, ExpressionWrapper, DecimalField

def annotate_price(queryset):
    """
    Annotates a queryset with a computed 'price' field based on each object's
    baseprice and discount fields.

    The price is calculated as:
        price = baseprice * (1 - discount / 100)

    This allows filtering or ordering by effective selling price using the
    annotated 'price' field in querysets.

    Args:
        queryset (QuerySet): A Django queryset with 'baseprice' and 'discount' fields.

    Returns:
        QuerySet: The same queryset, annotated with a Decimal 'price' field.
    """
    return queryset.annotate(
        price=ExpressionWrapper(
            F('baseprice') * (100 - F('discount')) / 100,
            output_field=DecimalField(max_digits=6, decimal_places=2)
        )
    )

def annotate_avg_rating(queryset):
    return queryset.annotate(
        average_rating=Avg('reviews__rating')
    )