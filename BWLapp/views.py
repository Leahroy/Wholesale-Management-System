# BWLapp/views.py

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
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.urls import reverse_lazy
from django.contrib import messages
from django.forms import inlineformset_factory
from django.utils import timezone
from datetime import timedelta
import json
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder

from .models import AuditTrail, Product, Customer, Order, OrderItem, Payment, Employee, Profile, Notification, Category, Stock
from .forms import RegisterForm, LoginForm, OrderForm, OrderItemForm, PaymentForm, ProductForm, StockForm

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
    Fetches the latest unread notifications and returns them as JSON.
    """
    notifications = Notification.objects.filter(is_read=False).order_by('-created_at')[:10]
    notification_data = [{
        'id': n.id,
        'message': n.message,
        'created_at': n.created_at.isoformat()
    } for n in notifications]
    # Corrected: Use CustomJSONEncoder for JsonResponse
    return JsonResponse({'notifications': notification_data, 'count': len(notification_data)}, encoder=CustomJSONEncoder)

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
            'url': reverse_lazy('customer-detail', args=[customer.pk])
        })

    # Search Orders by order number or customer name
    orders = Order.objects.filter(
                Q(order_number__icontains=query) |
                Q(customer__name__icontains=query)
    )
    for order in orders:
        results.append({
            'type': 'order',
            'label': f"Order #{order.order_id} by {order.customer.name}",
            'url': reverse_lazy('order-list')
        })

    # Corrected: Use CustomJSONEncoder for JsonResponse
    return JsonResponse({'results': results}, encoder=CustomJSONEncoder)

# --- Login & Registration Views ---
def login_register_view(request):
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
    return redirect('auth')

def homepage(request):
    # This is the corrected template path to resolve the TemplateDoesNotExist error.
    return render(request, "BWLapp/homepage.html")

@login_required
def admin_dashboard(request):
    # Fetch the data needed for the overview cards
    low_stock_threshold = 10
    
    # Calculate total stock and filter for low stock products in a single query
    low_stock_products = Product.objects.annotate(
        total_stock_quantity=Sum('stock__quantity')
    ).filter(
        total_stock_quantity__lt=low_stock_threshold
    )

    # Calculate total inventory value using ORM aggregation
    total_inventory_value = Product.objects.aggregate(
        total_expected_revenue=Sum(F('stock__quantity') * F('selling_price'))
    )['total_expected_revenue'] or Decimal('0')

    # Calculate total stock quantity using ORM aggregation
    total_stock_quantity = Stock.objects.aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # Monthly Sales Chart Data
    monthly_sales = Order.objects.annotate(
        month=TruncMonth('order_date')
    ).values('month').annotate(
        total_sales=Sum('payment__total_amount')
    ).order_by('month')

    sales_labels = [entry['month'].strftime('%b %Y') for entry in monthly_sales]
    sales_data = [float(entry['total_sales']) if entry['total_sales'] is not None else 0 for entry in monthly_sales]

    # Product Categories Chart Data
    category_counts = Product.objects.values('category__name').annotate(count=Count('pk'))
    product_labels = [item['category__name'] or 'Uncategorized' for item in category_counts]
    product_data = [item['count'] for item in category_counts]
    
    # Example of recent activities
    recent_orders = Order.objects.order_by('-order_date')[:5]
    recent_activities = [{
        'action': 'New Order', 
        'details': f"Order #{order.order_id} created for {order.customer.name}",
        'date': order.order_date.strftime('%Y-%m-%d')
    } for order in recent_orders]
    
    # Low Stock Notifications
    low_stock_notifs = [{
        'message': f"Product '{p.name}' is low on stock (Only {p.total_stock_quantity} left).",
    } for p in low_stock_products]
    
    all_notifications = low_stock_notifs 
    
    context = {
        'total_products': Product.objects.count(),
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_products.count(),
        'total_inventory_value': total_inventory_value,
        'total_stock_quantity': total_stock_quantity,
        'low_stock_threshold': low_stock_threshold,
        'recent_activities': recent_activities,
        'notifications': all_notifications,
        
        'sales_labels_json': json.dumps(sales_labels, cls=CustomJSONEncoder),
        'sales_data_json': json.dumps(sales_data, cls=CustomJSONEncoder),
        'product_labels_json': json.dumps(product_labels, cls=CustomJSONEncoder),
        'product_data_json': json.dumps(product_data, cls=CustomJSONEncoder),
    }

    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
def employee_dashboard(request):
    # Fetch the data needed for the overview cards
    total_customers = Customer.objects.count()
    total_orders = Order.objects.count()
    total_payments = Payment.objects.count()
    pending_orders = Order.objects.filter(status='Pending').count()
    
    # Fetch recent activities for the employee dashboard
    recent_orders = Order.objects.order_by('-order_date')[:5]
    recent_activities = [{
        'action': 'New Order',
        'details': f"Order #{order.order_id} created for {order.customer.name}",
        'date': order.order_date.strftime('%Y-%m-%d')
    } for order in recent_orders]
    

    # Pass the data to the template in a context dictionary
    context = {
        'total_customers': total_customers,
        'total_orders': total_orders,
        'total_payments': total_payments,
        'pending_orders': pending_orders,
        'recent_activities': recent_activities,
    }

    return render(request, 'dashboard/employee_dashboard.html', context)

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
        
        if request.user.role == 'admin':
            return redirect('admin_dashboard')
        else:
            return redirect('employee_dashboard')

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
class EmployeeListView(AjaxableResponseMixin, AdminRequiredMixin, ListView):
    model = Employee
    template_name = 'BWLapp/employee_list.html'
    context_object_name = 'employees'
    ordering = ['id']

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
    ordering = ['cust_id']
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.role == 'admin'
        return context

class CustomerCreateView(EmployeeRequiredMixin, CreateView):
    model = Customer
    fields = ['name', 'email', 'phone', 'address']
    template_name = 'BWLapp/customer_form.html'
    def get_success_url(self):
        if self.request.user.role == 'admin':
            return reverse_lazy('admin_dashboard')
        else:
            return reverse_lazy('employee_dashboard')

class CustomerUpdateView(AdminRequiredMixin, UpdateView):
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
    ordering = ['product_id']
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.role == 'admin'
        return context
    
class ProductDetailView(EmployeeRequiredMixin, DetailView):
    model = Product
    template_name = 'BWLapp/product_detail.html'

class ProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'BWLapp/product_form.html'
    success_url = reverse_lazy('product-list')

    def form_valid(self, form):
        messages.success(self.request, "Product created successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error creating the product. Please check the form.")
        return super().form_invalid(form)

class ProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'BWLapp/product_form.html'
    success_url = reverse_lazy('product-list')

    def form_valid(self, form):
        messages.success(self.request, "Product updated successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error updating the product. Please check the form.")
        return super().form_invalid(form)
    
class ProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    template_name = 'BWLapp/product_confirm_delete.html'
    success_url = reverse_lazy('product-list')
    
# --- Order Views ---
class OrderListView(AjaxableResponseMixin, EmployeeRequiredMixin, ListView):
    model = Order
    template_name = 'BWLapp/order_list.html'
    context_object_name = 'orders'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.role == 'admin'
        return context
    
class OrderDeleteView(AdminRequiredMixin, DeleteView):
    model = Order
    template_name = 'BWLapp/order_confirm_delete.html'
    success_url = reverse_lazy('order-list')

# --- OrderItem Views ---
class OrderItemListView(EmployeeRequiredMixin, ListView):
    model = OrderItem
    template_name = 'BWLapp/orderitem_list.html'
    context_object_name = 'order_items'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.role == 'admin'
        return context

class OrderItemCreateView(EmployeeRequiredMixin, CreateView):
    model = OrderItem
    fields = ['order', 'product', 'quantity', 'price_each']
    template_name = 'BWLapp/orderitem_form.html'
    def get_success_url(self):
        return reverse_lazy('employee_dashboard')

class OrderItemUpdateView(AdminRequiredMixin, UpdateView):
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
        if not request.user.role == 'admin':
            return redirect('employee_dashboard')
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
            
            # --- CORRECTED REDIRECT LOGIC ---
            if request.user.role == 'admin':
                return redirect('admin_dashboard')
            else:
                return redirect('employee_dashboard')
            # --- END CORRECTED REDIRECT LOGIC ---
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
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.role == 'admin'
        return context

class PaymentCreateView(EmployeeRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'BWLapp/payment_form.html'
    
    def form_valid(self, form):
        form.instance.processed_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        # CORRECTED: Redirect based on user's role
        if self.request.user.role == 'admin':
            return reverse_lazy('admin_dashboard')
        return reverse_lazy('employee_dashboard')

class PaymentUpdateView(AdminRequiredMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'BWLapp/payment_form.html'

    def get_success_url(self):
        # CORRECTED: Redirect based on user's role
        if self.request.user.role == 'admin':
            return reverse_lazy('admin_dashboard')
        return reverse_lazy('payment-list') # Assumed to be the correct page for employees

    def form_valid(self, form):
        messages.success(self.request, "Payment updated successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error updating the payment. Please check the form.")
        return super().form_invalid(form)
    
class PaymentDeleteView(AdminRequiredMixin, DeleteView):
    model = Payment
    template_name = 'BWLapp/payment_confirm_delete.html'
    success_url = reverse_lazy('payment-list')

@login_required
def reports_view(request):
    """
    Generates comprehensive reports for the wholesale business,
    including sales, inventory, customer, and financial insights.
    """
    time_range = request.GET.get('time_range', 'monthly')
    
    end_date = timezone.now()
    if time_range == 'daily':
        start_date = end_date - timedelta(days=30)
        trunc_by = TruncDay
    elif time_range == 'annual':
        start_date = end_date.replace(month=1, day=1) - timedelta(days=365*3)
        trunc_by = TruncYear
    else:
        start_date = end_date - timedelta(days=365)
        trunc_by = TruncMonth

    # 1. Sales Reports
    sales_over_time = Payment.objects.filter(
        payment_date__range=(start_date, end_date)
    ).annotate(
        date_group=trunc_by('payment_date')
    ).values('date_group').annotate(
        total_sales=Sum('total_amount')
    ).order_by('date_group')

    sales_labels = [entry['date_group'].strftime('%Y-%m-%d' if time_range == 'daily' else '%b %Y') for entry in sales_over_time]
    sales_data = [entry['total_sales'] for entry in sales_over_time]

    sales_by_product = OrderItem.objects.annotate(
        total_revenue=Sum(F('quantity') * F('price_each'))
    ).values('product__name').order_by('-total_revenue')[:10]

    sales_by_employee = Payment.objects.values(
        'processed_by__username'
    ).annotate(
        total_sales=Sum('total_amount')
    ).order_by('-total_sales')

    # 2. Inventory Reports
    # Corrected logic to use the `total_stock_quantity` property.
    low_stock_threshold = 10 # You can adjust this value
    stock_on_hand = Product.objects.all().order_by('name')
    low_stock_products = [p for p in stock_on_hand if p.total_stock_quantity < low_stock_threshold]
    
    six_months_ago = timezone.now() - timedelta(days=180)
    sold_products = OrderItem.objects.filter(order__order_date__gte=six_months_ago).values_list('product_id', flat=True)
    dead_stock = Product.objects.exclude(product_id__in=sold_products)

    # CORRECTED: Use 'cost_price' as the field name
    stock_valuation = Product.objects.aggregate(
        total_at_cost=Sum(F('stock_items__quantity') * F('cost_price')),
        total_at_selling_price=Sum(F('stock_items__quantity') * F('selling_price'))
    ) or {'total_at_cost': Decimal('0'), 'total_at_selling_price': Decimal('0')}
    
    # 3. Customer Reports
    top_customers = Customer.objects.annotate(
        total_spent=Sum('order__payment__total_amount')
    ).exclude(total_spent__isnull=True).order_by('-total_spent')[:10]

    outstanding_balances = Order.objects.filter(
        payment__isnull=True,
        status='pending'
    ).annotate(
        total_order_value=Sum(F('items__quantity') * F('items__price_each'))
    ).order_by('-total_order_value')

    # 4. Financial Reports
    total_revenue = Payment.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_cogs = OrderItem.objects.aggregate(total=Sum(F('quantity') * F('product__cost_price'))).get('total') or Decimal('0')
    total_profit = total_revenue - total_cogs
    
    # 5. Operational Reports
    returned_orders = Order.objects.filter(status='Returned').order_by('-order_date')

    # 6. Audit Trail Report
    audit_trail_log = AuditTrail.objects.all().order_by('-timestamp')[:50]
    
    context = {
        # Sales Report Data
        'sales_labels_json': json.dumps(sales_labels, cls=CustomJSONEncoder),
        'sales_data_json': json.dumps(sales_data, cls=CustomJSONEncoder),
        'time_range': time_range,
        'sales_by_product': sales_by_product,
        'sales_by_employee': sales_by_employee,
        
        # Inventory Report Data
        'stock_on_hand': stock_on_hand,
        'low_stock_products': low_stock_products,
        'dead_stock': dead_stock,
        'stock_valuation': stock_valuation,

        # Customer Report Data
        'top_customers': top_customers,
        'outstanding_balances': outstanding_balances,

        # Financial Report Data
        'total_revenue': total_revenue,
        'total_profit': total_profit,

        # Operational Reports
        'returned_orders': returned_orders,
        
        # Audit Trail Data
        'audit_trail_log': audit_trail_log,
    }
    
    return render(request, 'BWLapp/reports.html', context)

def payment_receipt(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, "BWLapp/payment_receipt.html", {"payment": payment})

# --- New: Stock Views ---
class StockListView(AjaxableResponseMixin, AdminRequiredMixin, ListView):
    model = Stock
    template_name = 'BWLapp/stock_list.html'
    context_object_name = 'all_stocks'
    ordering = ['product__name']
class StockCreateView(AdminRequiredMixin, CreateView):
    model = Stock
    form_class = StockForm
    template_name = 'BWLapp/stock_form.html'
    success_url = reverse_lazy('stock-list') # Or wherever you want to redirect
class StockUpdateView(AdminRequiredMixin, UpdateView):
    model = Stock
    form_class = StockForm
    template_name = 'BWLapp/stock_form.html'
    success_url = reverse_lazy('stock-list') # Or wherever you want to redirect

class StockDeleteView(AdminRequiredMixin, DeleteView):
    model = Stock
    template_name = 'BWLapp/stock_confirm_delete.html'
    success_url = reverse_lazy('stock-list')