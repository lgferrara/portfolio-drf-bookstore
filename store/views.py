from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import ProtectedError
from django.contrib.auth.models import User, Group
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, throttle_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from config.core.roles import get_role, is_role
from config.core.throttling import get_role_throttle, ManagerThrottle
from .models import *
from .serializers import *
from .permissions import HandleEmployeeGroupPermission, ReadOnlyOrIsAdminOrManager, CartPermission, AddressPermission
from .filters import *
from .services.queryset_annotators import annotate_price, annotate_avg_rating

@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([HandleEmployeeGroupPermission])
@throttle_classes([ManagerThrottle])
def handle_group_users(request, group_name):
    """
    GET: List all users in a group.
    POST: Add a user (by username) to the group.
    DELETE: Remove a user (by username) from the group.
    """
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return Response({'message': f'{group_name} group does not exist'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if request.method == 'GET':
        group_users = group.user_set.all()
        serialized = GroupUserSerializer(group_users, many=True)
        return Response(serialized.data, status=status.HTTP_200_OK)

    else: #POST or DELETE
        username = request.data.get('username')
        if not username:
            return Response({'message': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, username=username)        
        if request.method == 'POST':
            group.user_set.add(user)
            return Response({'message': f'{username} is now a {group_name}'})

        if request.method == 'DELETE':
            group.user_set.remove(user)
            return Response({'message': f'{user.username} is no longer a {group_name}'}, status=status.HTTP_204_NO_CONTENT)

def get_orders(user):
    """
    Helper function. Returns the queryset of orders accessible by the user depending on their role.
    - Admin/Manager: all orders
    - Delivery: orders assigned to them
    - Customer: their own orders
    """
    base_qs = Order.objects.select_related('user', 'deliverer', 'delivery_address', 'status')
    role = get_role(user)
    if role in ('admin', 'manager'):
        return base_qs
    if role == 'delivery':
        return base_qs.filter(deliverer=user)
    return base_qs.filter(user=user)


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    def get_throttles(self):
        return get_role_throttle(self.request.user)


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    def get_throttles(self):
        return get_role_throttle(self.request.user)


class BookFormatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BookFormat.objects.all()
    serializer_class = BookFormatSerializer
    def get_throttles(self):
        return get_role_throttle(self.request.user)


class OrderStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    def get_throttles(self):
        return get_role_throttle(self.request.user)


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    def get_throttles(self):
        return get_role_throttle(self.request.user)


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    permission_classes = [ReadOnlyOrIsAdminOrManager]
    ordering_fields = ['author', 'title', 'edition', 'price', 'discount']
    search_fields = ['title', 'author', 'genre__title', 'publisher']
    filterset_class = BookFilter
    
    def get_queryset(self):
        """
        Returns books annotated with computed discounted price.
        Includes prefetches for genre, stock, and format.
        """
        baseqs = Book.objects.select_related('genre', 'book_format', 'stock')
        return annotate_avg_rating(annotate_price(baseqs))

    def get_throttles(self):
        return get_role_throttle(self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """
        Attempts to delete a book.
        Fails gracefully if the book is referenced by orders (ProtectedError).
        """
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            raise ValidationError({
                'detail': 'Cannot delete this book because it is referenced by one or more orders.'
            })
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [CartPermission]
    ordering_fields = ['unit_price', 'price', 'quantity']
    search_fields = ['user__username', 'book__title', 'book__author']
    filterset_class =  CartFilter
    def list(self, request, *args, **kwargs):
        """
        Extends list response to include:
        - Computed cart total
        - Info about placing an order (URL, method, required body).
        """
        response = super().list(request, *args, **kwargs)
        cart_total = round(sum(float(item['price']) for item in response.data['results']), 2)
        place_order_url = reverse('order-list', request=request)
        customer_address_ids = [address.id for address in Address.objects.filter(user=request.user)]
        response.data['other_info'] = {
            'cart_total': cart_total,
            'place_order_info': {
                'url': place_order_url,
                'method': 'POST',
                'body': {
                    'delivery_address_id': ' or '.join([str(id) for id in customer_address_ids])
                    }
                }
            }
        return response

    def get_queryset(self):
        """
        Returns user-specific cart data.
        Admins and managers see all carts, customers see their own.
        """
        user = self.request.user
        role = get_role(user)
        base_qs = Cart.objects.select_related('user', 'book')
        if role in ('admin', 'manager'):
            return base_qs
        return base_qs.filter(user=user)
    
    def get_throttles(self):
        return get_role_throttle(self.request.user)

    @action(detail=False, methods=['delete'], url_path='', url_name='flush_cart')
    def flush_cart(self, request):
        """
        It bulk deletes all cart items for the current user (like a 'flush' cart action)
        """
        queryset = Cart.objects.filter(user=request.user)   #only cart owners can perform flushing
        count = queryset.count()
        queryset.delete()
        response_message = {'message': f'Cart flushed successfully. {count} item(s) deleted.'} if count != 0 else {'mesasge': 'Your cart is empty.'}
        response_status = status.HTTP_204_NO_CONTENT if count != 0 else status.HTTP_400_BAD_REQUEST

        return Response(response_message, status=response_status)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [AddressPermission]
    ordering_fields = ['user', 'recipient', 'country', 'city_town']
    search_fields = ['user__username', 'recipient', 'country__title', 'city_town', 'street_name']
    filterset_fields = ['user', 'country']

    def get_queryset(self):
        """
        Admins see all addresses.
        Regular users see only their own.
        """
        user = self.request.user
        base_qs = Address.objects.select_related('user', 'country')
        if is_role(user, 'admin'):
            return base_qs
        return base_qs.filter(user=user)
    
    def get_throttles(self):
        return get_role_throttle(self.request.user)
    

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['total', 'when_placed', 'status']
    search_fields = ['user__username']
    filterset_class = OrderFilter
    def get_queryset(self):
        user = self.request.user
        return get_orders(user)

    def get_throttles(self):
        return get_role_throttle(self.request.user)        

    def create(self, request):
        """
        Create method overridden.
        1.  It retrieves the queryset of items in the Cart of the user sending the request in 'cart_queryset'
        2.  It computes the total price of items in 'cart_queryset' via sum of their .price attrs
        3.  It creates a new Order record and stores the corresponding obj in 'new_order'
        4.  It instantiates a new queryset ('order_items') by iterating items in 'cart_queryset' and using its original attr execpt for '.user' which is now replaced with 'order'
        5.  It feeds the 'order_items' queryset to OrderItem via 'bulk_create' for better performance
        6.  It creates a new OrderHistory object
        7.  It finally 'flushes' the user's cart by deleting 'cart_queryset'    
        """
        user = request.user
        serializer = OrderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        delivery_address = serializer.validated_data['delivery_address']

        cart_queryset = Cart.objects.filter(user=user)
        if not cart_queryset.exists():
            return Response({'message': 'No item was found in your cart'}, status=status.HTTP_400_BAD_REQUEST)
        total = sum(cartobj.price for cartobj in cart_queryset)
        new_order = Order.objects.create(
            user=user,
            delivery_address=delivery_address,
            total=total,
            #when_placed=timezone.localtime(),
            #when_last_update=timezone.localtime()
            )

        order_items = [OrderItem(
            order=new_order,
            book=item.book,
            quantity=item.quantity,
            unit_price=item.unit_price,
            price=item.price,
            ) for item in cart_queryset]

        OrderItem.objects.bulk_create(order_items)

        OrderHistory.objects.create(
            order=new_order,
            #timestamp=timezone.localtime(),
            performed_by=user,
            action='Order created'
            )

        cart_queryset.delete()
        return Response({'message': 'Your order has been placed successfully',
                            'order_id': new_order.id}, 
                            status=status.HTTP_201_CREATED)
      

class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes=[IsAuthenticated]
    ordering_fields = ['price', 'quantity']
    search_fields = ['book__title', 'order__user__username']
    filterset_fields = ['order', 'book']
    def get_queryset(self):
        """
        Restricts visible OrderItems based on role:
        - Admin/Manager: all
        - Customer: only their orders
        - Delivery: denied access
        Supports filtering by order_id from URL.
        """
        user = self.request.user
        role = get_role(user)
        base_qs = OrderItem.objects.select_related('order', 'book')
        if role == 'delivery':
            raise PermissionDenied('You don\'t have access to the content of this order')
        order_id = self.kwargs.get('order_id')
        if order_id:
            orders = get_orders(user)
            try:
                order = orders.get(id=order_id)
                return base_qs.filter(order=order)
            except Order.DoesNotExist:
                raise NotFound('Order not found or not accessible')
        
        if role in ('admin', 'manager'):
            return base_qs
        return base_qs.none()

    def get_throttles(self):
        return get_role_throttle(self.request.user)
    

class OrderHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = OrderHistorySerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['timestamp']
    search_fields = ['order__user__username', 'performed_by__username', 'action']
    filterset_class = OrderHistoryFilter
    def get_queryset(self):
        """
        Restricts visible OrderHistory records similarly to OrderItemViewSet.
        """
        user = self.request.user
        role = get_role(user)
        base_qs = OrderHistory.objects.select_related('order', 'performed_by')
        order_id = self.kwargs.get('order_id')
        if order_id:
            orders = get_orders(user)
            try:
                order = orders.get(id=order_id)
                return base_qs.filter(order=order)
            except Order.DoesNotExist:
                raise NotFound('Order not found or not accessible')
        
        if role in ('admin', 'manager'):
            return base_qs
        return base_qs.none()

    def get_throttles(self):
        return get_role_throttle(self.request.user)
