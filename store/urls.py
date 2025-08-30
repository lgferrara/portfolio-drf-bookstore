from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter(trailing_slash=False)
router.register(r'genres', viewset=GenreViewSet, basename='genre')
router.register(r'stocks', viewset=StockViewSet, basename='stock')
router.register(r'book-formats', viewset=BookFormatViewSet, basename='bookformat')
router.register(r'order-statuses', viewset=OrderStatusViewSet, basename='orderstatus')
router.register(r'countries', viewset=CountryViewSet, basename='country')
router.register(r'books', viewset=BookViewSet, basename='book')
router.register(r'addresses', viewset=AddressViewSet, basename='address')
router.register(r'orders', viewset=OrderViewSet, basename='order')



urlpatterns = [
    path('groups/manager/users', handle_group_users, {'group_name': 'manager'}),
    
    path('groups/delivery/users', handle_group_users, {'group_name': 'delivery'}),

    path('', include(router.urls)),
    
    path('cart/items', view=CartViewSet.as_view({
        'get': 'list',
        'post': 'create',
        'delete': 'flush_cart'}),
        name='cart-list'),
    path('cart/items/<int:pk>', view=CartViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'}),
        name='cart-detail'),

    path('orders/<int:order_id>/items', view=OrderItemViewSet.as_view({'get': 'list'}), name='orderitems-by-order'),


    path('orders/<int:order_id>/history', view=OrderHistoryViewSet.as_view({'get': 'list'}), name='orderhistory-by-order'),


]
