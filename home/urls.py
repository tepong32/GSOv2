from django.urls import path
from .views import *

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
	path('', home, name='home'),
	path('add/', ItemCreateView.as_view(), name='add-item'),
	path('list/', ItemListView.as_view(), name='list-item'),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)