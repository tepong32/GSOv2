
from django.urls import path, include
from . import views

# app_name = 'users'

urlpatterns = [
	# func-based views
    path('<username>/', views.profile, name='profile' ),
    path('<username>/edit/', views.profile_edit, name='profile-edit' ),
]


from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)