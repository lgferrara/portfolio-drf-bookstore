from rest_framework.reverse import reverse


def obtain_list_url(serializer, basename):
    """
    Generates a 'back to list' URL with the appropriate view basename for list navigation.
    """
    request = serializer.context.get('request')
    url  = reverse(f'{basename}-list', request=request)
    return f'Back to list: {url}'

def handle_representation(serializer, data, list_fields):
    """
    Optimizes list vs. detail views by selectively displaying fields in list mode.
    Used for consistent minimalist API responses in collections.
    """
    request = serializer.context.get('request')
    if request and request.parser_context.get('view').action == 'list':
        return {field: data[field] for field in list_fields}
    return {field: data[field] for field in data.keys() if field!='url'}
