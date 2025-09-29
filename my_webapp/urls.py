# my_webapp/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # This includes all the URL patterns from your BWLapp application.
    path('', include('BWLapp.urls')),
]

# This is a crucial block for development.
# It tells Django's dev server to serve media files from MEDIA_ROOT at MEDIA_URL.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)