from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from store.models import Book
from config.core.throttling import get_role_throttle
from .models import Review
from .serializers import ReviewSerializer
from .permissions import ReviewPermission
from .filters import ReviewFilter


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [ReviewPermission]
    filterset_class = ReviewFilter
    ordering_fields = ['rating', 'created_at', 'updated_at']
    search_fields = ['user__username']

    def get_book(self):
        """
        Resolve the parent Book from the URL kwarg `book_id`.

        Returns
        -------
        Book
            The parent book object.

        Raises
        ------
        NotFound
            If no book exists with the given `book_id`.
        """
        book_id = self.kwargs.get('book_id')
        book = Book.objects.filter(id=book_id).first()
        if not book:
            raise NotFound('Book not found.')
        return book

    def get_queryset(self):
        """
        Return reviews strictly scoped to the parent book.

        Flow
        ----
        1) Ensure the parent book exists (404 otherwise).
        2) Return `Review` queryset filtered by that book, with
           `select_related('user', 'book')` for efficient DB access.
        """
        book = self.get_book()
        return (
            Review.objects
            .select_related('user', 'book')
            .filter(book=book)
        )

    def get_serializer_context(self):
        """
        Add a best-effort `book` to the serializer context.

        Returns
        -------
        dict
            Base context plus `book` (or None if not found).
        """
        context = super().get_serializer_context()
        book_id = self.kwargs.get('book_id')
        context['book'] = Book.objects.filter(id=book_id).first()
        return context

    def get_serializer(self, *args, **kwargs):
        """
        Initialize the serializer and, for write actions, inject the parent book ID.

        Behavior
        --------
        - For `create`, `update`, or `partial_update`, if request data is present,
          copy it and set `book` to the ID of the book in context (when available).
          This keeps validator logic (e.g., unique (user, book)) consistent even
          if the client omits `book` in the payload.
        """
        if self.action in ('create', 'update', 'partial_update') and 'data' in kwargs:
            ctx_book = self.get_serializer_context().get('book')
            if ctx_book:
                mutable = kwargs['data'].copy()
                mutable['book'] = ctx_book.id
                kwargs['data'] = mutable
        return super().get_serializer(*args, **kwargs)

    def get_throttles(self):
        return get_role_throttle(self.request.user)

    def get_object(self):
        """
        Retrieve a single review and enforce nested integrity.

        Flow
        ----
        1) Ensure the parent book exists (404 otherwise).
        2) Resolve the review via the standard DRF lookup.
        3) Verify the review actually belongs to the `book_id` in the URL.
           If mismatched, raise 404 to prevent cross-book access.
        4) Run object-level permission checks.

        Returns
        -------
        Review
            The retrieved and validated review instance.

        Raises
        ------
        NotFound
            If the review does not belong to the specified book.
        """
        self.get_book()
        obj = super().get_object()
        if obj.book.id != int(self.kwargs.get('book_id')):
            raise NotFound('This review does not belong to the specified book.')
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        book = self.get_book()
        serializer.save(user=self.request.user, book=book)
