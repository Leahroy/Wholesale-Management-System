from django.contrib import admin
from .models import CustomUser, Customer, Payment, Product, Order, Category, OrderItem, Stock

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Payment)
admin.site.register(OrderItem)
admin.site.register(Category)
admin.site.register(Stock)
