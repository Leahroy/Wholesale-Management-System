from django import forms
from.models import CustomUser
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Order, OrderItem, Payment
from django.contrib.auth import get_user_model

class RegisterForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'password1', 'password2']
        
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput)
    
    
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer', 'status', 'created_by']
        
class OrderItemForm(forms.ModelForm):
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
    class Meta:
        model = Payment
        fields = ['order', 'method', 'processed_by']
        widgets = {
            'method': forms.Select(choices=PAYMENT_METHOD_CHOICES),
        }