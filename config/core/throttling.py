from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from .roles import get_role

class CustomerThrottle(UserRateThrottle):
    scope = 'customer'

class ManagerThrottle(UserRateThrottle):
    scope = 'manager'

class DeliveryThrottle(UserRateThrottle):
    scope = 'delivery'

def get_role_throttle(user):
    """
    Returns the appropriate throttle class based on the user's role.
    - Admins and Managers get ManagerThrottle
    - Delivery users get DeliveryThrottle
    - Customers (all others) get CustomerThrottle
    - Unauthenticated users get AnonRateThrottle
    """
    role = get_role(user)
    if not user.is_authenticated:
        return [AnonRateThrottle()]
    if role in ('admin', 'manager'):
        return [ManagerThrottle()]
    if role == 'delivery':
        return [DeliveryThrottle()]
    return [CustomerThrottle()]
    