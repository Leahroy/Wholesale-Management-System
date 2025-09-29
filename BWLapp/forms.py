from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import CustomUser, Order, OrderItem, Payment, Product, Category, Stock
from django.contrib.auth import get_user_model


class RegisterForm(UserCreationForm):
    """
    Form for user registration (User Account fields ONLY).
    """
    class Meta:
        model = CustomUser
        fields = ['username', 'email'] + list(UserCreationForm.Meta.fields)

        
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
    
    NOTE: We remove 'price_each' from fields, as it should be automatically 
    set by the view/model's save logic based on the selected 'stock_item'.
    """
    
    # Custom ModelChoiceField for better display and filtering
    stock_item = forms.ModelChoiceField(
        # ✅ CRITICAL UPDATE: Filter to show ONLY available stock items
        queryset=Stock.objects.filter(is_available=True).select_related('product').all(),
        label="Product Package",
        empty_label="Select a Package" 
    )

    class Meta:
        model = OrderItem
        fields = ['stock_item', 'quantity'] 
        # 'price_each' is intentionally omitted here to be set programmatically

        
PAYMENT_METHOD_CHOICES = (
    ('Credit Card', 'Credit Card'),
    ('Debit Card', 'Debit Card'),
    ('Cash', 'Cash'),
    ('Online Transfer', 'Online Transfer'),
)

AVAILABILITY_CHOICES = (
    (True, 'Yes'),
    (False, 'No'),
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

            'selling_price',
            'image', 
        ]
        
# NEW: Create a separate form for the Stock model
class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        # ✅ FIX: 'is_available' is now included in the fields list 
        fields = ['product', 'package_type', 'quantity', 'price_per_package', 'is_available'] 
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'package_type': forms.Select(choices=Stock.PACKAGE_TYPE_CHOICES, attrs={'class': 'form-control'}), 
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_per_package': forms.NumberInput(attrs={'class': 'form-control'}),
            # Optional: Use CheckboxInput if you prefer a checkbox over a dropdown
            # 'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            # Note: By default, Django uses a Select widget for BooleanField, giving you the Yes/No dropdown.
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add basic form styling (recommended practice for all forms)
        for field_name, field in self.fields.items():
            # Apply 'form-control' to non-select and non-checkbox fields
            if not isinstance(field.widget, (forms.Select, forms.CheckboxInput)):
                field.widget.attrs.update({'class': 'form-control'})