# BWLapp/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models import Sum, F
from decimal import Decimal
from django.core.exceptions import ValidationError

# --- 1. Custom User & Profile Models ---

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('employee', 'Employee'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile_picture = models.ImageField(default='BWLapp/profile.jpg', upload_to='profile_pics/')
    name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
class Notification(models.Model):
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message

# --- 2. Employees & Customers ---

class Employee(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    employee_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username
        
class Customer(models.Model):
    cust_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

# --- 3. Product & Stock Models (Stock must come before OrderItem) ---
    
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00')) 
    image = models.ImageField(
        upload_to='product_images/', 
        blank=True, 
        null=True,
        help_text="Upload a high-quality product image."
    )
    @property
    def total_stock_quantity(self):
        """Calculates the total number of packages across all stock items."""
        return self.stock_items.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def total_expected_revenue(self):
        """Calculates the total revenue from all stock items of this product."""
        return self.stock_items.aggregate(
            total=Sum(F('quantity') * F('price_per_package'))
        )['total'] or Decimal('0')

    def __str__(self):
        return self.name

# --- STOCK MODEL (Defined here to be available for OrderItem) ---
class Stock(models.Model):
    PACKAGE_TYPE_CHOICES = (
        ('6pack', '6-Pack'),
        ('dozen', 'Dozen'),
        ('Carton', 'Carton'),
        ('bulk', 'Bulk'),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_items')
    package_type = models.CharField(max_length=50, choices=PACKAGE_TYPE_CHOICES, help_text="e.g., '6-Pack', 'Dozen'")
    quantity = models.PositiveIntegerField(default=0, help_text="Number of packages in stock")
    price_per_package = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price for this specific package type")
    is_available = models.BooleanField(default=True)
    
    @property
    def expected_total_amount(self):
        """Calculates the total revenue expected from this stock."""
        return self.quantity * self.price_per_package

    def __str__(self):
        return f"[ID:{self.pk}] {self.product.name} - {self.get_package_type_display()} ({self.quantity} in stock)"

# --- 4. Order & OrderItem Models ---

class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='Pending')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_created')
    order_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.order_id} for {self.customer.name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    # Reference to Stock works here because Stock is defined above
    stock_item = models.ForeignKey(Stock, on_delete=models.PROTECT) 
    quantity = models.IntegerField(default=1)
    price_each = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        # 1. Price Setting
        if not self.price_each and self.stock_item:
            self.price_each = self.stock_item.price_per_package

        # 2. STOCK DEDUCTION LOGIC
        quantity_to_deduct = self.quantity
        
        if self.pk:
            # If updating an existing item, determine the change in quantity.
            try:
                original_item = OrderItem.objects.get(pk=self.pk)
                # Calculate the difference (Positive=deduct more, Negative=return stock)
                quantity_change = self.quantity - original_item.quantity
                quantity_to_deduct = quantity_change
            except OrderItem.DoesNotExist:
                pass
        
        if quantity_to_deduct != 0:
            stock = self.stock_item
            
            # --- Check 1: Insufficient Stock (only for positive deduction) ---
            if quantity_to_deduct > 0 and stock.quantity < quantity_to_deduct:
                raise ValidationError(
                    f"Insufficient stock for {stock.product.name} ({stock.get_package_type_display()}). "
                    f"Only {stock.quantity} available, requested {quantity_to_deduct} more."
                )

            # --- Check 2: Deduct/Return Stock ---
            stock.quantity -= quantity_to_deduct
            stock.save()

        # Call the parent save method
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # When an OrderItem is deleted, return the stock back to inventory.
        stock = self.stock_item
        stock.quantity += self.quantity # Add the full quantity back
        stock.save()
        super().delete(*args, **kwargs)

# --- 5. Payment & Audit Trail Models ---

class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    method = models.CharField(max_length=50)
    processed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments_processed')

    def __str__(self):
        return f"Payment {self.payment_id} for Order {self.order.order_id}"

    def save(self, *args, **kwargs):
        # Calculate total_amount from order items if not manually set
        if not self.total_amount:
            calculated_total = sum(item.quantity * item.price_each for item in self.order.items.all())
            self.total_amount = calculated_total
        super().save(*args, **kwargs)
        
class AuditTrail(models.Model):
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=50)
    record_id = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user} {self.action} on {self.model_name} (ID: {self.record_id})"