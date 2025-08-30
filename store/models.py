from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from stdnum import isbn as stdnum_isbn


# Create your models here.

class SluggedTitleModel(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Genre(SluggedTitleModel):
    title = models.CharField(max_length=255, db_index=True)
    class Meta:
        ordering = ['title']   


class Stock(SluggedTitleModel):
    pass


class BookFormat(SluggedTitleModel):
    pass


class OrderStatus(SluggedTitleModel):
    pass


class Country(SluggedTitleModel):
    iso_3166 = models.CharField(max_length=3, unique=True, validators=[RegexValidator(r'^\d{3}$')])
    

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipient = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    state_province = models.CharField(max_length=255, blank=True, null=True)
    city_town = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=20)
    street_name = models.CharField(max_length=255)
    number = models.CharField(max_length=50)
    apartment_suite = models.CharField(max_length=50,blank=True, null=True)
    notes = models.TextField(max_length=2500, blank=True, null=True)
    class Meta:
        unique_together = ('user', 'recipient', 'country', 'zip_code', 'street_name', 'number')
        ordering = ['user', 'recipient']

    def __str__(self):
        return f'To {self.recipient} in {self.street_name}, {self.city_town} - uid {self.id}'


def validate_isbn_cleaned(value):
    if not stdnum_isbn.is_valid(value):
        raise ValidationError("Invalid ISBN")
    
class Book(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    author = models.CharField(max_length=255, db_index=True)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT)
    first_publication_year = models.IntegerField(validators=[MinValueValidator(1)])
    is_bc = models.BooleanField(default=False)
    blurb = models.TextField(max_length=1200, blank=True)
    publisher = models.CharField(max_length=255, db_index=True)
    edition = models.SmallIntegerField(validators=[MinValueValidator(1)])
    language = models.CharField(max_length=100)
    book_format  = models.ForeignKey(BookFormat, on_delete=models.PROTECT, default=1)
    isbn = models.CharField(max_length=13, unique=True, validators=[validate_isbn_cleaned])    
    is_new = models.BooleanField(default=True)
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT, default=1)
    baseprice = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    discount = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    def __str__(self):
        return f'{self.title}, by {self.author}'
    
    class Meta:
        unique_together = ['title', 'author', 'publisher', 'edition', 'language', 'book_format']
        ordering = ['title','author', 'stock', '-edition']
    

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.SmallIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        unique_together = ('user', 'book')
        ordering = ['user']
    
    def __str__(self):
        return f'{self.user} - {self.book}'


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    deliverer = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='deliveries', null=True)
    delivery_address = models.ForeignKey(Address, on_delete=models.PROTECT)
    status = models.ForeignKey(OrderStatus, on_delete=models.PROTECT, default=1)
    total = models.DecimalField(max_digits=6, decimal_places=2)
    when_placed = models.DateTimeField(db_index=True, auto_now_add=True)
    when_last_update = models.DateTimeField(db_index=True, auto_now=True)
    class Meta:
        ordering = ['status__title', 'user']



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    book = models.ForeignKey(Book, on_delete=models.PROTECT)
    quantity = models.SmallIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    class Meta:
        unique_together = ('order', 'book')
        ordering = ['order']


class OrderHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_histories')
    status = models.ForeignKey(OrderStatus, on_delete=models.PROTECT, default=1)
    timestamp = models.DateTimeField(db_index=True, auto_now_add=True)
    performed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=255, default='', blank=True)
    class Meta:
        ordering = ['order', '-timestamp']

