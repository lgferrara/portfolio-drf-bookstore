from rest_framework.permissions import BasePermission, SAFE_METHODS

class ReviewPermission(BasePermission):
    """
    Read: everyone
    Update: only review owner
    Delete: review owner or admin (superuser)
    """
    def has_permission(self, request, view):
        return True
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        
        user = request.user
        is_author = bool(user == obj.user)
        if is_author:
            return True
        if request.method == 'DELETE':
            return is_author or user.is_superuser
        return is_author