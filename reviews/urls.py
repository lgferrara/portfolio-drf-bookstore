from django.urls import path
from .views import ReviewViewSet

app_name = 'reviews'
urlpatterns = [
    path('books/<int:book_id>/reviews', view=ReviewViewSet.as_view({
        'get': 'list',
        'post': 'create'
        }),
         name='reviews-by-book'),
    path('books/<int:book_id>/reviews/<int:pk>', view=ReviewViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
        }),
         name='review-detail'),
]