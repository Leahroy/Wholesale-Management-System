from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
# Custom user model with roles
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('employee', 'Employee'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default= 'employee')
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
# User profile extending CustomUser    
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

# Employees managing the system and managed by admin    
class Employee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    address = models.TextField(max_length=200)
    phone = models.CharField(max_length=20)
    def __str__(self):
        return self.name
        

# Customers who place orders
class Customer(models.Model):
    cust_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
# Products to sell
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    PACKAGE_CHOICES = [
        ('6pack', '6 pack'),
        ('dozen', 'dozen'),
        ('carton', 'carton'),
        ('bulk', 'bulk'),
    ]
    packaging = models.CharField(max_length=20, choices=PACKAGE_CHOICES, default='6pack')

    def __str__(self):
        return self.name

# Orders placed by customers
class Order(models.Model):
    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='Pending')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_created')
    order_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.order_id} for {self.customer.name}"

# Items within each order
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price_each = models.DecimalField(max_digits=10, decimal_places=2)
    def save(self, *args, **kwargs):
        # Reduce stock only when creating a new order item
        if not self.pk:  # Only decrease stock for new items
            if self.quantity > self.product.stock_quantity:
                raise ValueError(f"Not enough stock for {self.product.name}!")
            self.product.stock_quantity -= self.quantity
            self.product.save()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


# Payments made for orders
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
            # Use a different variable name to avoid shadowing the built-in sum() function
            calculated_total = sum(item.quantity * item.price_each for item in self.order.items.all())
            self.total_amount = calculated_total
        super().save(*args, **kwargs)

