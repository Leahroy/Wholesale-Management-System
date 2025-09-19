from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import Order, Product

@receiver(post_save, sender=Order)
def update_product_stock(sender, instance, created, **kwargs):
    if created:
        for item in instance.items.all():  # Use related_name='items'
            product = item.product
            if product.stock_quantity >= item.quantity:
                product.stock_quantity -= item.quantity  # reduce stock
                product.quantity_sold += item.quantity  # increase sold count
                product.save()
            else:
                # Optional: cancel the order or raise error
                raise ValidationError(
                    f"Not enough stock for {product.name}. Available: {product.stock_quantity}, Ordered: {item.quantity}"
                )
