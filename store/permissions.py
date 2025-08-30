from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.exceptions import APIException
from config.core.roles import is_role
    

class IsAdminOrManager(IsAuthenticated):
    def has_permission(self, request, view):
        #first check authentication
        if not super().has_permission(request, view):
            return False
        user = request.user
        return (is_role(user, 'admin') or is_role(user, 'manager'))
    
    
class ReadOnlyOrIsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return IsAdminOrManager().has_permission(request, view)
    

class CartPermission(IsAuthenticated):
    """
    Custom object-level permission for Cart access.
    - Cart owners and admins can view and edit.
    - Managers can only view.
    - Others are denied access.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        is_cart_owner = bool(user == obj.user)
        if is_role(user, 'admin') or is_cart_owner:
            return True
        if is_role(user, 'manager') and (request.method in SAFE_METHODS):
            return True
        return False

class AddressPermission(IsAuthenticated):
    """
    Custom object-level permission for Address access.
    - Only address owners and admins can view and edit.
    - All others are denied access.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        is_cart_owner = bool(user == obj.user)
        if is_role(user, 'admin') or is_cart_owner:
            return True
        return False


class HandleEmployeeGroupPermission(IsAuthenticated):
    """
    Permission class that only works with @api_view-decorated function views.
    Ensures only users with the right role can manage users in 'manager' or 'delivery' groups.
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        try:
            group_name = request.parser_context['kwargs'].get('group_name')
        except (AttributeError, KeyError):
            raise APIException("Server misconfiguration: 'group_name' not found in request context.")
        
        user = request.user
        if group_name == 'manager':
            return is_role(user, 'admin')
        if group_name == 'delivery':
            return (is_role(user, 'admin') or is_role(user, 'manager'))
        return False

