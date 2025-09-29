# BWLapp/urls.py
from django.urls import path
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    homepage,
    login_register_view,
    logout_view,
    admin_dashboard,
    employee_dashboard,
    search_dashboard,
    get_notifications,
    payment_receipt,
    profile,
    change_password,
    reports_view,
    EmployeeListView, EmployeeCreateView,
    EmployeeUpdateView, EmployeeDeleteView,
    ProductListView, ProductCreateView,
    ProductUpdateView, ProductDeleteView,
    CustomerListView, CustomerCreateView,
    CustomerUpdateView, CustomerDeleteView,
    OrderListView, OrderDeleteView,
    manage_order,
    OrderItemListView, OrderItemCreateView,
    OrderItemUpdateView, OrderItemDeleteView,
    PaymentListView, PaymentCreateView,
    PaymentUpdateView, PaymentDeleteView,
    StockListView, StockCreateView, StockUpdateView, StockDeleteView # Added StockListView
)
from django.contrib.auth import views as auth_views
from BWLapp.views import homepage
# Removed redundant import: from . import views

urlpatterns = [
    # Authentication urls
    path('', homepage, name='homepage'),
    path('auth/', login_register_view, name='auth'),
    path('logout/', logout_view, name='logout'),

    #Dashboard urls
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('employee-dashboard/', employee_dashboard, name='employee_dashboard'),

    #search urls
    path('search/', search_dashboard, name='search'),

    #notification urls
    path('notifications/', get_notifications, name='get_notifications'),

    #payment receipt url
    path("payment/<int:pk>/receipt/", payment_receipt, name="payment_receipt"),

    # Profile and Password URLs
    path('profile/', profile, name='profile'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='BWLapp/change_password.html'), name='change_password'),

    #Employee urls
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('employees/create/', EmployeeCreateView.as_view(), name='employee-create'),
    path('employees/<int:pk>/update/', EmployeeUpdateView.as_view(), name='employee-update'),
    path('employees/<int:pk>/delete/', EmployeeDeleteView.as_view(), name='employee-delete'),

    #Customer URLs
    path('customer/', CustomerListView.as_view(), name='customer-list'),
    path('customer/create/', CustomerCreateView.as_view(), name='customer-create'),
    path('customer/<int:pk>/update/', CustomerUpdateView.as_view(), name='customer-update'),
    path('customer/<int:pk>/delete/', CustomerDeleteView.as_view(), name='customer-delete'),

    #Product URLs
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('products/<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),

    # Order URLs
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/create/', manage_order, name='order-create'),
    path('orders/<int:order_id>/update/', manage_order, name='order-update'),
    path('orders/<int:pk>/delete/', OrderDeleteView.as_view(), name='order-delete'),

    # OrderItem URLs
    path('orderitem/', OrderItemListView.as_view(), name='orderitem-list'),
    path('orderitem/<int:pk>/update/', OrderItemUpdateView.as_view(), name='orderitem-update'),
    path('orderitem/<int:pk>/delete/', OrderItemDeleteView.as_view(), name='orderitem-delete'),

    # payment urls
    path('payments/', PaymentListView.as_view(), name='payment-list'),
    path('payments/create/', PaymentCreateView.as_view(), name='payment-create'),
    path('payments/<int:pk>/update/', PaymentUpdateView.as_view(), name='payment-update'),
    path('payments/<int:pk>/delete/', PaymentDeleteView.as_view(), name='payment-delete'),

    #report urls
    path('reports/', reports_view, name='reports'),

    # Stock URLs
 #report urls
    path('reports/', reports_view, name='reports'),

    # Stock URLs
    path('stocks/', StockListView.as_view(), name='stock-list'),
    path('stock/create/', StockCreateView.as_view(), name='stock-create'),
    
    # 🎯 FIX 1: Change name='stock-update' to name='stocks-update'
    path('stocks/<int:pk>/update/', StockUpdateView.as_view(), name='stocks-update'), 
    
    # 🎯 FIX 2: Change name='stock-delete' to name='stocks-delete'
    path('stocks/<int:pk>/delete/', StockDeleteView.as_view(), name='stocks-delete'), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)