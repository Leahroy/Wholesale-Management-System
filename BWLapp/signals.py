from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from decimal import Decimal
import json
from django.contrib.auth import get_user_model
from .models import Order, Product, Customer, AuditTrail, OrderItem, Payment

# Now get the custom User model
User = get_user_model()

# --- New: Custom JSON Encoder for Decimal values ---
class CustomJSONEncoder(DjangoJSONEncoder):
    """
    A custom JSON encoder that handles Decimal objects by converting them to strings.
    This prevents the "TypeError: Object of type Decimal is not JSON serializable" error.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

# --- End Custom JSON Encoder ---

@receiver(post_save, sender=Order)
def update_product_stock(sender, instance, created, **kwargs):
    """
    Reduces product stock quantity and increases quantity_sold when a new order is created.
    """
    if created:
        for item in instance.items.all():
            product = item.product
            if product.stock_quantity >= item.quantity:
                product.stock_quantity -= item.quantity
                # Note: 'quantity_sold' field is not in your models.py.
                # If you have it, uncomment the line below. Otherwise, remove it.
                # product.quantity_sold += item.quantity
                product.save()
            else:
                # Optional: cancel the order or raise error
                raise ValidationError(
                    f"Not enough stock for {product.name}. Available: {product.stock_quantity}, Ordered: {item.quantity}"
                )

@receiver(post_save, sender=Product)
@receiver(post_save, sender=Customer)
@receiver(post_save, sender=Order)
@receiver(post_save, sender=OrderItem)
@receiver(post_save, sender=Payment)
@receiver(post_save, sender=User)
def log_post_save(sender, instance, created, **kwargs):
    """
    Logs creation and update actions for key models in the AuditTrail.
    """
    if transaction.get_connection().in_atomic_block:
        transaction.on_commit(lambda: _do_log_post_save(sender, instance, created))
    else:
        _do_log_post_save(sender, instance, created)

def _do_log_post_save(sender, instance, created):
    action = f"Created {sender.__name__}" if created else f"Updated {sender.__name__}"
    user = getattr(instance, 'created_by', None) or getattr(instance, 'processed_by', None)
    if isinstance(instance, User):
        user = instance

    if instance.pk:
        try:
            # Corrected: Use CustomJSONEncoder for serialization
            details = json.dumps(model_to_dict(instance, exclude=['password', 'last_login', 'is_superuser']), cls=CustomJSONEncoder)
        except Exception as e:
            details = f"Could not serialize instance to JSON: {e}"

        AuditTrail.objects.create(
            user=user,
            action=action,
            details=details
        )
@receiver(post_delete, sender=Product)
@receiver(post_delete, sender=Customer)
@receiver(post_delete, sender=Order)
def log_post_delete(sender, instance, **kwargs):
    """
    Logs deletion actions for key models in the AuditTrail.
    """
    user = None # This part is tricky. Deletion signals don't carry the user.
    
    try:
        # Corrected: Use CustomJSONEncoder for serialization
        details = json.dumps(model_to_dict(instance), cls=CustomJSONEncoder)
    except Exception as e:
        details = f"Could not serialize deleted instance to JSON: {e}"
        
    AuditTrail.objects.create(
        user=user,
        action=f"Deleted {sender.__name__}",
        details=details
    )