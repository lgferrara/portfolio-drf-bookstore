from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework.reverse import reverse
from config.core import serializer_utils
from store.models import Book
from .models import Review
import bleach

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    customer = serializers.StringRelatedField(source='user', read_only=True)    

    book = serializers.PrimaryKeyRelatedField(
        queryset = Book.objects.all(),
        write_only=True,
        required=False
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
    url = serializers.SerializerMethodField()
    list_url = serializers.SerializerMethodField()

    def validate(self, attrs):        
        # Strict sanitization for CharFields (No HTML tags at all)
        if 'title' in attrs:
            attrs['title'] = bleach.clean(attrs.get('title'), tags=[], attributes={}, strip=True)
        # Default sanitization for TextFields (allowing rich formatting)
        attrs['comment'] = bleach.clean(attrs.get('comment', ''))
        
        rating = attrs.get('rating', None)
        m = 'Please enter an integer value between 1 and 5.'
        if not rating:
            raise serializers.ValidationError({'rating': m})
        if rating < 1 or rating > 5:
            raise serializers.ValidationError({'rating': f'Your input value is out of range. {m}'})
        
        return super().validate(attrs)

    def to_representation(self, instance):
        data =  super().to_representation(instance)
        if instance.created_at:
            data['created_at'] = timezone.localtime(instance.created_at).isoformat()
        if instance.updated_at:
            data['updated_at'] = timezone.localtime(instance.updated_at).isoformat()
        list_representation_fields = ['id', 'customer',  'book_display', 'book_url', 'rating', 'title', 'comment', 'created_at', 'url']
        return serializer_utils.handle_representation(self, data=data, list_fields=list_representation_fields)

    def get_url(self, obj):
        request = self.context.get('request')
        return reverse('reviews:review-detail', kwargs={
            'book_id': obj.book.id,
            'pk': obj.pk
        }, request=request)

    def get_list_url(self, obj):
        """
        Generates a 'back to list' URL with the appropriate view basename for list navigation.
        """
        request = self.context.get('request')
        url  = reverse('reviews:reviews-by-book',  kwargs={
            'book_id': obj.book.id,
            }, request=request)
        return f'Back to list: {url}'
        

    class Meta:
        model = Review
        fields = ['id', 'user', 'customer', 'book', 'book_display', 'book_url', 'rating', 'title', 'comment', 'created_at', 'updated_at', 'url', 'list_url']
        validators = [UniqueTogetherValidator(
            queryset=Review.objects.all(),
            fields=['user', 'book'],
            message='You have already posted a review for this book.')]