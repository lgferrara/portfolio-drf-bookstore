from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from store.models import OrderStatus, OrderHistory
from config.core.roles import get_role

class OrderUpdater:
    """
    Encapsulates business logic for safely updating an order.
    Handles permission checks, status transitions, deliverer assignments,
    customer intents (refund/cancellation), address changes, and history logging.
    """
    STATUS_TRANSITIONS = {
        # Maps current → allowed new statuses by role
        'pending': {
            'shipped': ['admin', 'manager'],
            'under-review': ['admin', 'manager', 'customer'],
            'failed': ['admin', 'manager'],
        },
        'shipped': {
            'delivered': ['admin', 'delivery'],
            'under-review': ['admin', 'manager', 'delivery'],
        },
        'delivered': {
            'under-review': ['admin', 'manager', 'customer'],
        },
        'under-review': {
            'shipped': ['admin', 'manager'],
            'cancelled': ['admin', 'manager'],
            'refunded': ['admin', 'manager'],
            'failed': ['admin', 'manager'],
        },
        'failed': {
            'under-review': ['admin', 'manager', 'customer'],
        }
    }

    INTENTS_ORIGIN_STATUSES = {
        # Allowed original statuses for intent types
        'cancellation': ['pending', 'failed'],
        'refund': ['delivered'],
    }
    
    
    def __init__(self, *, order, user, data):
        """
        Initialize the updater with the order instance, the acting user,
        and the validated update data from the serializer.
        """
        self.order = order
        self.user = user
        self.data = data
        self.role = get_role(user)
        self.intent = self.data.pop('intent', None)
        self.action_description = ''

    def run(self):
        """
        Executes the full update lifecycle in logical steps:
        1. Field permission validation
        2. Optional deliverer assignment
        3. Optional address change handling
        4. Intent (cancellation/refund) handling
        5. Status transition enforcement and logging
        """
        self._check_allowed_fields()
        self._handle_deliverer()
        self._handle_delivery_address()
        self._handle_intent()
        self._handle_status_transition()
        self.order.save()
        return self.order
    
    def _check_allowed_fields(self):
        """
        Ensures that the user only updates fields permitted for their role.
        Raises ValidationError if disallowed fields are found.
        """
        role = self.role
        attempted_fields = set(self.data.keys())
        if role in ('admin', 'manager'):
            allowed_fields = {'status', 'deliverer'}
        elif role == 'delivery':
            allowed_fields = {'status'}
        else:   #customer
            allowed_fields = {'delivery_address', 'intent'}
        disallowed_fields = attempted_fields - allowed_fields
        if disallowed_fields:
            raise ValidationError(f"You don't have permission to update these fields: {disallowed_fields}.")

    def _handle_deliverer(self):
        """
        If a new deliverer is assigned, set it.
        If the order is early-stage, auto-update status to 'shipped'.
        """
        new_deliverer = self.data.get('deliverer')
        if not new_deliverer:
            return
        if new_deliverer != self.order.deliverer:
            self.order.deliverer = new_deliverer
            if self.order.status.slug in ('pending', 'under-review'):
                self.data['status'] = OrderStatus.objects.get(slug='shipped')
           
    def _handle_delivery_address(self):
        """
        Handles customer address changes.
        Allowed only in 'pending' or 'failed'.
        A change in 'failed' triggers review.
        """
        new_address = self.data.get('delivery_address')
        if not new_address or new_address == self.order.delivery_address:
            return

        current_status = self.order.status
        if current_status.slug not in ('pending', 'failed'):
            raise ValidationError(f'You cannot change the delivery address at this stage (current status: {current_status.title}).')

        self.order.delivery_address = new_address

        if current_status.slug == 'failed':
            self.data['status'] = OrderStatus.objects.get(slug='under-review')

    def _handle_intent(self):
        """
        If a customer requests a cancellation or refund, validate eligibility
        based on current order status and update intent accordingly.
        """
        if not self.intent:
            return
        if self.order.status.slug not in self.INTENTS_ORIGIN_STATUSES[self.intent]:
            raise ValidationError(f'You cannot request {self.intent} at this stage (current status: {self.order.status.title}).')
        self.data['status'] = OrderStatus.objects.get(slug='under-review')
        self.action_description = f'Customer requested {self.intent}. Status transitioned to Under Review.'

    def _handle_status_transition(self):
        """
        Handles the final status transition, ensuring:
        - It’s allowed from the current status
        - The user has role-based permission
        - History is logged
        """
        new_status = self.data.get('status')
        current_status = self.order.status
        if not new_status or new_status == self.order.status:
            return
        allowed_transitions = self.STATUS_TRANSITIONS.get(current_status.slug, {})
        if new_status.slug not in allowed_transitions:
                raise ValidationError({'status': f'You cannot update an order status from {current_status.title} to {new_status.title}'})
        
        if self.role not in allowed_transitions[new_status.slug]:
            raise PermissionDenied({
                'status': f'You do not have permission to update this order status from {current_status.title} to {new_status.title}'
            })
        
        self.order.status = new_status
        self.order.when_last_update = timezone.localtime()
        self._log_history(new_status)

    def _log_history(self, new_status):
        """
        Logs the change in order status or customer intent in the OrderHistory table.
        """
        action = self.action_description or f'Status transitioned to {new_status.title}'
        OrderHistory.objects.create(
            order=self.order,
            status=new_status,
            #timestamp=timezone.localtime(),
            performed_by=self.user,
            action=action
        )


    