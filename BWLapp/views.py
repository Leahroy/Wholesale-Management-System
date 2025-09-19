from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import AccessMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.db import transaction
from django.db.models import Sum, F, Count, Q
from django.db.models.functions import TruncDay, TruncMonth
from django.urls import reverse_lazy
from django.contrib import messages
from django.forms import inlineformset_factory

import json

from .forms import RegisterForm, LoginForm, OrderForm, OrderItemForm, PaymentForm
from .models import Product, Customer, Order, OrderItem, Payment, Employee, Profile, Notification, Category

# --- New: AjaxableResponseMixin ---
class AjaxableResponseMixin:
    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Render the partial template and return the HTML as an HttpResponse.
            return HttpResponse(render_to_string(self.get_template_names()[0], context, self.request), **response_kwargs)
        # For a standard browser request, fall back to the default behavior.
        return super().render_to_response(context, **response_kwargs)

# --- NEW: API Views for Search and Notifications ---
@login_required
def get_notifications(request):
    """
    Fetches the latest unread notifications for the user.
    """
    # Assuming 'Notification' is a model you've created with 'message' and 'is_read' fields
    notifications = Notification.objects.filter(is_read=False).order_by('-created_at')[:10]
    notification_data = [{
        'id': n.id,
        'message': n.message,
        'created_at': n.created_at.isoformat()
    } for n in notifications]
    return JsonResponse({'notifications': notification_data, 'count': len(notification_data)})

@login_required
def search_dashboard(request):
    """
    Performs a search across relevant models (Products, Customers, Orders).
    """
    query = request.GET.get('query', '')
    if not query:
        return JsonResponse({'results': []})

    results = []

    # Search Products by name or description
    products = Product.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
    for product in products:
        results.append({
            'type': 'product',
            'label': product.name,
            'url': reverse_lazy('product-detail', args=[product.pk])
        })

    # Search Customers by name or email
    customers = Customer.objects.filter(Q(name__icontains=query) | Q(email__icontains=query))
    for customer in customers:
        results.append({
            'type': 'customer',
            'label': customer.name,
            'url': reverse_lazy('customer-detail', args=[customer.pk]) # Assuming a detail view for customers
        })

    # Search Orders by order number or customer name
    orders = Order.objects.filter(
        Q(order_number__icontains=query) |
        Q(customer__name__icontains=query)
    )
    for order in orders:
        results.append({
            'type': 'order',
            'label': f"Order #{order.order_number} by {order.customer.name}",
            'url': reverse_lazy('order-list') # Or a specific detail view for orders
        })

    return JsonResponse({'results': results})

# --- Login & Registration Views ---
def login_register_view(request):
    # ... (Your existing code)
    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        if 'login_submit' in request.POST:
            login_form = LoginForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                return redirect('employee_dashboard')
        elif 'register_submit' in request.POST:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                return redirect('employee_dashboard')

    context = {'login_form': login_form, 'register_form': register_form}
    return render(request, 'Registration/login.html', context)

# --- Standard Views ---
def logout_view(request):
    logout(request)
    return redirect('login') 

def homepage(request):
    return render(request, 'BWLapp/homepage.html')

@login_required
def admin_dashboard(request):
    total_products = Product.objects.count()
    low_stock_threshold = 10
    low_stock_products = Product.objects.filter(stock_quantity__lt=low_stock_threshold).order_by('stock_quantity')

    total_inventory_value = Product.objects.aggregate(
        total_value=Sum(F('price') * F('stock_quantity'))
    )['total_value'] or 0

    total_stock_quantity = Product.objects.aggregate(
        total_quantity=Sum('stock_quantity')
    )['total_quantity'] or 0
    
    # Monthly Sales Chart Data
    # Use order__payment__total_amount for a more accurate sales figure
 # Monthly Sales Chart Data
    monthly_sales = Order.objects.annotate(
    month=TruncMonth('order_date')
    ).values('month').annotate(
    # Corrected line: Access the total_amount field through the 'payment' relationship
    total_sales=Sum('payment__total_amount')
    ).order_by('month')

    sales_labels = [entry['month'].strftime('%b %Y') for entry in monthly_sales]
    sales_data = [float(entry['total_sales']) for entry in monthly_sales]

    # Product Categories Chart Data
    category_counts = Product.objects.values('category__name').annotate(count=Count('pk'))
    product_labels = [item['category__name'] or 'Uncategorized' for item in category_counts]
    product_data = [item['count'] for item in category_counts]
    
    # Example of recent activities (you need to implement a logging system or get from relevant models)
    recent_orders = Order.objects.order_by('-order_date')[:5]
    recent_activities = [{
        'action': 'New Order', 
        'details': f"Order #{order.order_id} created for {order.customer.name}",
        'date': order.order_date.strftime('%Y-%m-%d')
    } for order in recent_orders]
    
    # Low Stock Notifications
    low_stock_notifs = [{
        'message': f"Product '{p.name}' is low on stock (Only {p.stock_quantity} left).",
    } for p in low_stock_products]
    
    # Combine notifications for the dashboard view
    all_notifications = low_stock_notifs 
    # Add other notification types here, e.g., recent payments, new customer registrations

    context = {
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_products.count(),
        'total_inventory_value': total_inventory_value,
        'total_stock_quantity': total_stock_quantity,
        'low_stock_threshold': low_stock_threshold,
        'recent_activities': recent_activities,
        'notifications': all_notifications, # Pass this to the template for the dropdown
        
        'sales_labels_json': json.dumps(sales_labels),
        'sales_data_json': json.dumps(sales_data),
        'product_labels_json': json.dumps(product_labels),
        'product_data_json': json.dumps(product_data),
    }

    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
def employee_dashboard(request):
    return render(request, 'dashboard/employee_dashboard.html')

@login_required
def profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
        
        request.user.email = request.POST.get('email', request.user.email)
        profile.name = request.POST.get('name', profile.name)
        profile.phone_number = request.POST.get('phone_number', profile.phone_number)
        
        request.user.save()
        profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')

    return render(request, 'BWLapp/profile.html')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'incorrect password.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'BWLapp/change_password.html', {'form': form})

# --- Access Control Mixins ---
class AdminRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'admin':
            return redirect('employee_dashboard')
        return super().dispatch(request, *args, **kwargs)

class EmployeeRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in ['admin', 'employee']:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

# --- Employee Views ---
class EmployeeListView(AjaxableResponseMixin, EmployeeRequiredMixin, ListView):
    model = Employee
    template_name = 'BWLapp/employee_list.html'
    context_object_name = 'employees'

class EmployeeCreateView(AdminRequiredMixin, CreateView):
    model = Employee
    fields = ['name', 'email', 'address', 'phone']
    template_name = 'BWLapp/employee_form.html'
    success_url = reverse_lazy('employee-list')

class EmployeeUpdateView(AdminRequiredMixin, UpdateView):
    model = Employee
    fields = ['name', 'email', 'address', 'phone']
    template_name = 'BWLapp/employee_form.html'
    success_url = reverse_lazy('employee-list')

class EmployeeDeleteView(AdminRequiredMixin, DeleteView):
    model = Employee
    template_name = 'BWLapp/employee_confirm_delete.html'
    success_url = reverse_lazy('employee-list')

# --- Customer Views ---
class CustomerListView(AjaxableResponseMixin, EmployeeRequiredMixin, ListView):
    model = Customer
    template_name = 'BWLapp/customer_list.html'
    context_object_name = 'customers'
    
class CustomerCreateView(EmployeeRequiredMixin, CreateView):
    model = Customer
    fields = ['name', 'email', 'phone', 'address']
    template_name = 'BWLapp/customer_form.html'
    success_url = reverse_lazy('customer-list')
    
class CustomerUpdateView(EmployeeRequiredMixin, UpdateView):
    model = Customer
    fields = ['name', 'email', 'phone', 'address']
    template_name = 'BWLapp/customer_form.html'
    success_url = reverse_lazy('customer-list')
    
class CustomerDeleteView(AdminRequiredMixin, DeleteView):
    model = Customer
    template_name = 'BWLapp/customer_confirm_delete.html'
    success_url = reverse_lazy('customer-list')

# --- Product Views ---
class ProductListView(AjaxableResponseMixin, EmployeeRequiredMixin, ListView):
    model = Product
    template_name = 'BWLapp/product_list.html'
    context_object_name = 'products'

class ProductDetailView(EmployeeRequiredMixin, DetailView):
    model = Product
    template_name = 'BWLapp/product_detail.html'

class ProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    fields = ['name', 'description', 'price', 'stock_quantity', 'category']
    template_name = 'BWLapp/product_form.html'
    success_url = reverse_lazy('product-list')

class ProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    fields = ['name', 'description', 'price', 'stock_quantity', 'category']
    template_name = 'BWLapp/product_form.html'
    success_url = reverse_lazy('product-list')
    
class ProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    template_name = 'BWLapp/product_confirm_delete.html'
    success_url = reverse_lazy('product-list')
    
# --- Order Views ---
class OrderListView(AjaxableResponseMixin, EmployeeRequiredMixin, ListView):
    model = Order
    template_name = 'BWLapp/order_list.html'
    context_object_name = 'orders'
    
class OrderDeleteView(AdminRequiredMixin, DeleteView):
    model = Order
    template_name = 'BWLapp/order_confirm_delete.html'
    success_url = reverse_lazy('order-list')

# --- OrderItem Views ---
class OrderItemListView(EmployeeRequiredMixin, ListView):
    model = OrderItem
    template_name = 'BWLapp/orderitem_list.html'
    context_object_name = 'order_items'

class OrderItemCreateView(EmployeeRequiredMixin, CreateView):
    model = OrderItem
    fields = ['order', 'product', 'quantity', 'price_each']
    template_name = 'BWLapp/orderitem_form.html'
    success_url = reverse_lazy('orderitem-list')

class OrderItemUpdateView(EmployeeRequiredMixin, UpdateView):
    model = OrderItem
    fields = ['order', 'product', 'quantity', 'price_each']
    template_name = 'BWLapp/orderitem_form.html'
    success_url = reverse_lazy('orderitem-list')

class OrderItemDeleteView(AdminRequiredMixin, DeleteView):
    model = OrderItem
    template_name = 'BWLapp/orderitem_confirm_delete.html'
    success_url = reverse_lazy('orderitem-list')
    
@login_required
def manage_order(request, order_id=None):
    if order_id:
        order = get_object_or_404(Order, pk=order_id)
        is_update = True
    else:
        order = Order()
        is_update = False

    OrderItemFormSet = inlineformset_factory(
        Order,
        OrderItem,
        form=OrderItemForm,
        extra=1,
        can_delete=True
    )
    
    if request.method == 'POST':
        order_form = OrderForm(request.POST, instance=order)
        formset = OrderItemFormSet(request.POST, instance=order)
        
        if order_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = order_form.save(commit=False)
                if not is_update:
                    order.created_by = request.user
                order.save()
                formset.save()
            return redirect('order-list') 
    else:
        order_form = OrderForm(instance=order)
        formset = OrderItemFormSet(instance=order)
    
    context = {
        'order_form': order_form,
        'formset': formset,
        'is_update': is_update,
    }
    
    return render(request, 'BWLapp/order_formset.html', context)
    
# --- Payment Views ---
class PaymentListView(AjaxableResponseMixin, EmployeeRequiredMixin, ListView):
    model = Payment
    template_name = 'BWLapp/payment_list.html'
    context_object_name = 'payments'

class PaymentCreateView(EmployeeRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'BWLapp/payment_form.html'
    success_url = reverse_lazy('payment-list')
    def form_valid(self, form):
        form.instance.processed_by = self.request.user
        return super().form_valid(form)

class PaymentUpdateView(EmployeeRequiredMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'BWLapp/payment_form.html'
    success_url = reverse_lazy('payment-list')

class PaymentDeleteView(AdminRequiredMixin, DeleteView):
    model = Payment
    template_name = 'BWLapp/payment_confirm_delete.html'
    success_url = reverse_lazy('payment-list')

# --- Reports View ---
@login_required
def reports_view(request):
    # ... (Your existing code)
    total_revenue = Payment.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_cogs = OrderItem.objects.aggregate(total=Sum(F('quantity') * F('product__cost_price'))).get('total') or 0
    total_profit = total_revenue - total_cogs
    payment_methods = Payment.objects.values('method').annotate(count=Count('method')).order_by('method')

    sales_over_time = Payment.objects.annotate(
        date=TruncDay('payment_date')
    ).values('date').annotate(
        total_sales=Sum('total_amount')
    ).order_by('date')
    
    fast_moving_products = OrderItem.objects.values('product__name').annotate(
        total_quantity_sold=Sum('quantity')
    ).order_by('-total_quantity_sold')[:5]

    slow_moving_products_data = OrderItem.objects.values('product__name').annotate(
        total_quantity_sold=Sum('quantity')
    ).order_by('total_quantity_sold')[:5]
    
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=F('low_stock_threshold')
    ).order_by('stock_quantity')
    
    top_customers = Customer.objects.annotate(
        total_spent=Sum('order__payment__total_amount')
    ).exclude(total_spent__isnull=True).order_by('-total_spent')[:5]

    context = {
        'total_revenue': total_revenue,
        'total_cogs': total_cogs,
        'total_profit': total_profit,
        'payment_methods': payment_methods,
        'fast_moving_products': fast_moving_products,
        'slow_moving_products_data': slow_moving_products_data,
        'sales_over_time': sales_over_time, 
        'low_stock_products': low_stock_products,
        'top_customers': top_customers, 
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'BWLapp/reports.html', context)
    else:
        return render(request, 'dashboard/admin_dashboard.html', context)