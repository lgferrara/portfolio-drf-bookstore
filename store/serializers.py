from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator
from stdnum import isbn as stdnum_isbn
from datetime import date
from config.core import serializer_utils
from config.core.roles import get_role
from .models import *
from .services.order_updater import OrderUpdater
import bleach


class GroupUserSerializer(serializers.ModelSerializer):
    """
    Serializer for listing basic user details (id, username, email, etc.).
    Used when managing group membership.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class SluggedTitleSerializer(serializers.HyperlinkedModelSerializer):
    """
    Abstract serializer for models with 'title' and 'slug' fields.
    Includes basic sanitization of user input.
    """
    def validate(self, attrs):
        attrs['title'] = bleach.clean(attrs['title'])
        return super().validate(attrs)
        
    class Meta:
        abstract = True


class GenreSerializer(SluggedTitleSerializer):
    title = serializers.CharField(
        max_length=255,
        validators=[UniqueValidator(queryset=Genre.objects.all())]
    )
        
    class Meta:
        model = Genre
        fields = ['id', 'url', 'title', 'slug']


class StockSerializer(SluggedTitleSerializer):
    title = serializers.CharField(
        max_length=255,
        validators=[UniqueValidator(queryset=Stock.objects.all())]
    )
        
    class Meta:
        model = Stock
        fields = ['id', 'title', 'slug']


class CountrySerializer(SluggedTitleSerializer):
    title = serializers.CharField(
        max_length=255,
        validators=[UniqueValidator(queryset=Country.objects.all())]
    )
        
    class Meta:
        model = Country
        fields = ['id', 'title', 'slug', 'iso_3166']


class BookFormatSerializer(SluggedTitleSerializer):
    title = serializers.CharField(
        max_length=255,
        validators=[UniqueValidator(queryset=BookFormat.objects.all())]
    )
        
    class Meta:
        model = BookFormat
        fields = ['id', 'title', 'slug']


class OrderStatusSerializer(SluggedTitleSerializer):
    title = serializers.CharField(
        max_length=255,
        validators=[UniqueValidator(queryset=OrderStatus.objects.all())]
    )
        
    class Meta:
        model = OrderStatus
        fields = ['id', 'title', 'slug']


class ISBNField(serializers.CharField):
    """
    A custom serializer field for validating and normalizing ISBN-10 or ISBN-13 input.

    This field:
    - Accepts hyphenated or spaced ISBN strings from user input.
    - Strips all hyphens and spaces using stdnum.isbn.compact.
    - Validates the cleaned ISBN using stdnum.isbn.is_valid.
    - Returns the cleaned ISBN to ensure consistency across storage and uniqueness checks.

    Raises:
        serializers.ValidationError: If the cleaned ISBN is not valid.
    """
    def to_internal_value(self, data):
        try:
            cleaned = stdnum_isbn.compact(data)
        except Exception:
            raise serializers.ValidationError("Could not parse ISBN")
        
        if not stdnum_isbn.is_valid(cleaned):
            raise serializers.ValidationError("Enter a valid ISBN-10 or ISBN-13")
        
        return cleaned
    

class BookSerializer(serializers.HyperlinkedModelSerializer):
    genre = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(),
        write_only=True
        )   
    genre_display = serializers.StringRelatedField(
        source='genre',
        read_only=True
        )
    genre_url = serializers.HyperlinkedRelatedField(
        source='genre',
        view_name='genre-detail',
        read_only=True
        )

    book_format = serializers.PrimaryKeyRelatedField(
        queryset=BookFormat.objects.all(),
        write_only=True,
        )
    book_format_display = serializers.StringRelatedField(
        source='book_format',
        read_only=True
        )
    book_format_url = serializers.HyperlinkedRelatedField(
        source='book_format',
        view_name='bookformat-detail',
        read_only=True
        )

    stock = serializers.PrimaryKeyRelatedField(
        queryset=Stock.objects.all(),
        default=1,
        label='Stock status',
        write_only=True,
        )
    stock_display = serializers.StringRelatedField(
        source='stock',
        read_only=True
        )
    stock_url = serializers.HyperlinkedRelatedField(
        source='stock',
        view_name='stock-detail',
        read_only=True
        )
    
    isbn = ISBNField(
        max_length=13,
        validators=[UniqueValidator(queryset=Book.objects.all())]
        )
    
    first_publication_year = serializers.IntegerField(validators=[MinValueValidator(1)], write_only=True)
    is_bc = serializers.BooleanField(default=False, write_only=True)
    publication_year = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_url = serializers.SerializerMethodField()
    list_url = serializers.SerializerMethodField()
    add_to_cart_info = serializers.SerializerMethodField()
        
    def validate(self, attrs):
        # Strict sanitization for CharFields (No HTML tags at all)
        for field in ['title', 'author', 'publisher', 'language']:
            if field in attrs:
                attrs[field] = bleach.clean(attrs.get(field), tags=[], attributes={}, strip=True)
        # Default sanitization for TextFields (allowing rich formatting)
        if 'blurb' in attrs:
            attrs['blurb'] = bleach.clean(attrs.get('blurb', ''))

        # Validate publication_year
        if 'first_publication_year' in attrs:
            year, is_bc = attrs.get('first_publication_year'), attrs.get('is_bc', False)
            if year <= 0:
                raise serializers.ValidationError({'first_publication_year': 'Year must be greater than 0'})
            if not is_bc and year > date.today().year:
                raise serializers.ValidationError({'first_publication_year': 'Year cannot be in the future for AD dates.'})

        # Ensure edition is positive and makes sense
        if 'edition' in attrs:
            edition = attrs.get('edition')
            if edition is not None and edition < 1:
                raise serializers.ValidationError({'edition': "Edition must be at least 1."})

        return attrs

    def to_representation(self, instance):
        data =  super().to_representation(instance)
        list_representation_fields = ['id', 'title', 'author', 'genre_display', 'edition', 'book_format_display', 'price', 'average_rating', 'url']
        return serializer_utils.handle_representation(self, data=data, list_fields=list_representation_fields)

    def get_reviews_url(self, bookobj):
        request = self.context.get('request')
        return reverse('reviews:reviews-by-book', kwargs={'book_id': bookobj.pk}, request=request)
    

    def get_list_url(self, bookobj):
        return serializer_utils.obtain_list_url(self, basename='book')

    def get_add_to_cart_info(self, bookobj):
        request = self.context.get('request')
        url  = reverse('cart-list', request=request,)
        return {
            'url': url,
            'method': 'POST',
            'body': {
                'book': bookobj.id,
                'quantity': '<integer>'
            }
        }
   
    def get_price(self, bookobj):
        return round(bookobj.baseprice * (100-bookobj.discount) / 100, 2)
    
    def get_average_rating(self, bookobj):
        avg = getattr(bookobj, 'average_rating', None)
        return None if avg is None else round(avg, 2)

    def get_publication_year(self, bookobj):
        if bookobj.is_bc:
            return str(bookobj.first_publication_year) + ' BC'
        return str(bookobj.first_publication_year)
    
    class Meta:
        model = Book
        fields = ['id','title', 'author', 'genre_display', 'genre_url','genre', 'first_publication_year', 'is_bc', 'publication_year', 'blurb', 'publisher', 'edition', 'language', 'book_format_display', 'book_format_url', 'book_format', 'isbn', 'is_new', 'stock_display', 'stock_url', 'stock', 'baseprice', 'price', 'average_rating', 'url', 'discount', 'list_url', 'add_to_cart_info', 'reviews_url']
        validators = [UniqueTogetherValidator(
            queryset=Book.objects.all(),
            fields=['title', 'author', 'publisher', 'edition', 'language', 'book_format']
        )]        
    

class CartSerializer(serializers.HyperlinkedModelSerializer):
    """
    Create a cart entry. Auto-calculates unit and total price based on book price and quantity.
    """
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    customer = serializers.StringRelatedField(source='user', read_only=True)    
    
    book = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
        write_only=True
        )    
    book_display = serializers.StringRelatedField(
        source='book',
        read_only=True
        )
    book_url = serializers.HyperlinkedRelatedField(
        source='book',
        view_name='book-detail',
        read_only=True
        )

    quantity = serializers.IntegerField()

    unit_price = serializers.DecimalField(max_digits=6, decimal_places=2,read_only=True)

    price = serializers.DecimalField(max_digits=6, decimal_places=2,read_only=True)

    list_url = serializers.SerializerMethodField()

    def validate(self, attrs):
        if attrs.get('quantity') < 1:
            raise serializers.ValidationError({'quantity': 'Quantity cannot be less than 1'})
        
        book = attrs.get('book', None)
        if book:
            if book.stock.slug == 'out-of-stock':
                raise serializers.ValidationError({'book': 'This book is currently out of stock.'})
            if book.stock.slug == 'discontinued':
                raise serializers.ValidationError({'book': 'This book has been discontinued and is no longer available.'})

        return super().validate(attrs)

    def create(self, validated_data):
        """
        Creates a cart entry using the calculated unit price and total price,
        based on book discount and quantity.
        """
        book = validated_data['book']
        quantity = validated_data['quantity']
        unit_price = round(book.baseprice * (100 - book.discount) / 100, 2)
        price = unit_price * quantity
        return Cart.objects.create(
            user=self.context['request'].user,
            book=book,
            quantity=quantity,
            unit_price=unit_price,
            price=price
        )

    def update(self, instance, validated_data):
        """
        Allows only the quantity field to be updated. Recalculates total price accordingly.
        Raises error if other fields are touched.
        """
        uneditable_fields = set(validated_data.keys()) - {'quantity'}
        if uneditable_fields:
            raise serializers.ValidationError(f"Only 'quantity' can be updated. You are trying to update {uneditable_fields}")

        instance.quantity = validated_data['quantity']
        instance.price = instance.unit_price * instance.quantity
        instance.save()
        return instance
    
    def to_representation(self, instance):
        data =  super().to_representation(instance)
        list_representation_fields = ['id', 'customer', 'book_display', 'book_url', 'quantity', 'price', 'url']
        return serializer_utils.handle_representation(self, data=data, list_fields=list_representation_fields)

    def get_list_url(self, cartobj):
        return serializer_utils.obtain_list_url(self, basename='cart')
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'customer', 'book', 'book_display', 'book_url', 'quantity', 'unit_price', 'price', 'url', 'list_url']
        validators = [UniqueTogetherValidator(
            queryset=Cart.objects.all(),
            fields=['user', 'book'],
            message='This book is already in your cart')]


class AddressSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    customer = serializers.StringRelatedField(
        source='user',
        read_only=True
        )

    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        write_only=True
        )
    country_info = CountrySerializer(source='country', read_only=True)
    country_url = serializers.HyperlinkedRelatedField(
        source='country',
        view_name='country-detail',
        read_only=True
        )


    def validate(self, attrs):
        # Strict sanitization
        for field in ['recipient', 'state_province', 'city_town', 'zip_code', 'street_name', 'number', 'apartment_suite', 'notes']:
            if field in attrs:
                attrs[field] = bleach.clean(attrs.get(field), tags=[], attributes={}, strip=True)

        return attrs

    class Meta:
        model = Address
        fields = ['id', 'user', 'customer', 'recipient', 'country_info', 'country_url', 'country', 'state_province', 'city_town', 'zip_code', 'street_name', 'number', 'apartment_suite', 'notes']
        validators = [UniqueTogetherValidator(
            queryset=Address.objects.all(),
            fields=['user', 'recipient', 'country', 'zip_code', 'street_name', 'number'],
            message='This address is already associated to your account')]


class OrderSerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    customer = serializers.StringRelatedField(
        source='user',
        read_only=True
        )
    
    total = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    
    delivery_address = serializers.PrimaryKeyRelatedField(
        queryset = Address.objects.all(),
        write_only=True
        )
    delivery_address_display = serializers.StringRelatedField(
        source='delivery_address',
        read_only=True
        )
    delivery_address_url = serializers.HyperlinkedRelatedField(
        source='delivery_address',
        view_name='address-detail',
        read_only=True
        )
    

    status = serializers.PrimaryKeyRelatedField(
        queryset=OrderStatus.objects.all(),
        default=1,
        write_only=True,
        )
    status_display = serializers.StringRelatedField(
        source='status',
        read_only=True
        )
    status_url = serializers.HyperlinkedRelatedField(
        source='status',
        view_name='orderstatus-detail',
        read_only=True
        )

    deliverer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        write_only=True
        )
    deliverer_display = serializers.StringRelatedField(
        source='deliverer',
        read_only=True
        )

    when_placed = serializers.DateTimeField(read_only=True)
    when_last_update = serializers.DateTimeField(read_only=True)

    list_url = serializers.SerializerMethodField()
    orderitems_url = serializers.SerializerMethodField()
    orderhistory_url = serializers.SerializerMethodField()

    # Optional customer-provided intent field used to trigger review (e.g., refund/cancellation).
    intent = serializers.ChoiceField(
        choices=['cancellation', 'refund'],
        required=False
        )

    def __init__(self, instance=None, *args, **kwargs):
        """
        Customizes delivery_address queryset based on user role:
        - Admins/managers can assign any address.
        - Customers see only their own addresses.
        """
        super().__init__(instance, *args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            user_role = get_role(user)
            if user_role in ('admin', 'manager'):
                self.fields['delivery_address'].queryset = Address.objects.all()
            else:
                self.fields['delivery_address'].queryset = Address.objects.filter(user=user)

    def validate(self, attrs):
        deliverer = attrs.get('deliverer', None)
        if deliverer and not deliverer.groups.filter(name='delivery').exists():
            raise serializers.ValidationError({'deliverer': 'You can assign this order only to a Delivery Crew member'})
        return super().validate(attrs)

    def get_fields(self):
        """
        'get_fields' is extended in order to control what fields are readable and/or editable by which user
        """
        fields = super().get_fields()
        user_role = get_role(self.context['request'].user)
        if user_role not in ('admin', 'manager', 'delivery'):
            fields.pop('status', None)      # customer can still check the order's status by looking at 'status_display'
            fields.pop('deliverer', None)    # customer doesn't need to know to which deliverer the order gets assigned to
        return fields
    
    def update(self, instance, validated_data):
        """
        Delegates business logic to the OrderUpdater service class.
        This ensures separation of concerns between validation and business rules.
        """
        return OrderUpdater(
            order = instance,
            user = self.context['request'].user,
            data=validated_data
        ).run()

    def to_representation(self, instance):
        data =  super().to_representation(instance)
        if instance.when_placed:
            data['when_placed'] = timezone.localtime(instance.when_placed).isoformat()
        if instance.when_last_update:
            data['when_last_update'] = timezone.localtime(instance.when_last_update).isoformat()
        list_representation_fields = ['id', 'customer', 'status_display', 'total', 'delivery_address_display', 'when_placed', 'url']
        return serializer_utils.handle_representation(self, data=data, list_fields=list_representation_fields)

    def get_list_url(self, orderobj):
        return serializer_utils.obtain_list_url(self, basename='order')
    
    def get_orderitems_url(self, orderobj):
        request = self.context.get('request')
        return reverse('orderitems-by-order', kwargs={'order_id': orderobj.id}, request=request)
    
    def get_orderhistory_url(self, orderobj):
        request = self.context.get('request')
        return reverse('orderhistory-by-order', kwargs={'order_id': orderobj.id}, request=request)

    class Meta:
        model = Order
        fields = ['id', 'user', 'customer', 'status', 'status_display', 'status_url', 'intent', 
        'total', 'deliverer', 'deliverer_display', 'delivery_address', 'delivery_address_display', 'delivery_address_url', 'when_placed', 'when_last_update', 'url', 'list_url', 'orderitems_url', 'orderhistory_url']


class OrderItemSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(read_only=True)
    order_display = serializers.StringRelatedField(
        source='order', 
        read_only=True
        )
    order_url = serializers.HyperlinkedRelatedField(
        source='order',
        view_name='order-detail',
        read_only=True
    )
    book = serializers.PrimaryKeyRelatedField(read_only=True)
    book_display = serializers.StringRelatedField(
        source='book', 
        read_only=True
        )
    book_url = serializers.HyperlinkedRelatedField(
        source='book',
        view_name='book-detail',
        read_only=True
    )
    class Meta:
        model = OrderItem
        fields = ['order', 'order_display', 'order_url', 'book', 'book_display', 'book_url', 'quantity', 'unit_price', 'price']


class OrderHistorySerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(read_only=True)
    order_display = serializers.StringRelatedField(
        source='order', 
        read_only=True
        )
    order_url = serializers.HyperlinkedRelatedField(
        source='order',
        view_name='order-detail',
        read_only=True
    )
    status = serializers.PrimaryKeyRelatedField(read_only=True)
    status_display = serializers.StringRelatedField(
        source='status', 
        read_only=True
        )
    status_url = serializers.HyperlinkedRelatedField(
        source='status',
        view_name='orderstatus-detail',
        read_only=True
    )

    def to_representation(self, instance):
        data =  super().to_representation(instance)
        if instance.timestamp:
            data['timestamp'] = timezone.localtime(instance.timestamp).isoformat()
        return data
    
    class Meta:
        model = OrderHistory
        fields = ['order', 'order_display', 'order_url', 'status', 'status_display', 'status_url', 'timestamp', 'performed_by', 'action']


