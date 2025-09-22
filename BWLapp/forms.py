from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import CustomUser, Order, OrderItem, Payment, Product, Category, Stock
from django.contrib.auth import get_user_model


class RegisterForm(UserCreationForm):
    """
    Form for user registration.
    """
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2']
        
class LoginForm(AuthenticationForm):
    """
    Form for user login.
    """
    username = forms.CharField(widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput)
    
    
class OrderForm(forms.ModelForm):
    """
    Form for creating or updating an order.
    """
    class Meta:
        model = Order
        fields = ['customer', 'status', 'created_by']
        
class OrderItemForm(forms.ModelForm):
    """
    Form for creating or updating an order item.
    """
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price_each']
        
PAYMENT_METHOD_CHOICES = (
    ('Credit Card', 'Credit Card'),
    ('Debit Card', 'Debit Card'),
    ('Cash', 'Cash'),
    ('Online Transfer', 'Online Transfer'),
)

class PaymentForm(forms.ModelForm):
    """
    Form for creating or updating a payment.
    """
    class Meta:
        model = Payment
        fields = ['order', 'method', 'processed_by']
        widgets = {
            'method': forms.Select(choices=PAYMENT_METHOD_CHOICES),
        }

class ProductForm(forms.ModelForm):
    """
    Form for creating or updating a Product instance, including all fields.
    """
    # FIX: Added required=False here to allow the field to be optional
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label="Category",
        empty_label="Select a Category",
        required=False
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'category',
            'cost_price',
        ]
        # FIX: The `widgets` dictionary is no longer needed here as `packaging` has been removed.

# NEW: Create a separate form for the Stock model
class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['product', 'package_type', 'quantity', 'price_per_package']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'package_type': forms.Select(choices=Stock.PACKAGE_TYPE_CHOICES, attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_per_package': forms.NumberInput(attrs={'class': 'form-control'}),
        }