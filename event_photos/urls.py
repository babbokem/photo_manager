from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from . import views

urlpatterns = [
    # Amministrazione Django
    path('admin/', admin.site.urls),

    # App Eventi
    path('photos/', include('event_photos.urls')),

    # Rotte per la gestione degli eventi
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_event, name='create_event'),
    
    # Rotte per le foto
    path('event/<int:event_id>/', views.event_photos, name='event_photos'),
    path('event/<int:event_id>/upload/', views.upload_photos, name='upload_photos'),
    
    # Rotte per il carrello e acquisto
    path('cart/', views.cart, name='cart'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),
    
    # Download foto
    path('download/<str:filename>/', views.download_zip, name='download_zip'),

    # Visualizzazione file media
    path('view-foto/', views.view_foto, name='view_foto'),  # Assicurati che questa sia presente
]

# Servire i file statici e media, ma solo in modalità DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Servire i file media in produzione con il proxy inverso (Nginx) o tramite la configurazione di Django
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
