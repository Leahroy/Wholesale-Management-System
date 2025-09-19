# BWLapp/urls.py
from django.urls import path
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import (
    reports_view,
    
    EmployeeListView, EmployeeCreateView,
    EmployeeUpdateView, EmployeeDeleteView,
    
    ProductListView, ProductCreateView,
    ProductUpdateView, ProductDeleteView,
    
    CustomerListView, CustomerCreateView, 
    CustomerUpdateView, CustomerDeleteView,
    
    OrderListView, OrderDeleteView,
    
    OrderItemListView, OrderItemCreateView,
    OrderItemUpdateView, OrderItemDeleteView,
    
    PaymentListView, PaymentCreateView, 
    PaymentUpdateView, PaymentDeleteView
)
from django.contrib.auth import views as auth_views

urlpatterns = [
    
    # Authentication urls 
    path('', views.homepage, name='homepage'),
    path('auth/', views.login_register_view, name='auth'),
    path('logout/', views.logout_view, name='logout'),
    
    #Dashboard urls
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    
    # Profile and Password URLs
    path('profile/', views.profile, name='profile'),
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
    path('orders/create/', views.manage_order, name='order-create'),
    path('orders/<int:order_id>/update/', views.manage_order, name='order-update'),
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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)