from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve  
from . import views  
from .views import (
    check_media_path, privacy_policy, dettagli_privacy, remove_from_cart, 
    add_to_cart, cart, all_events, create_checkout_session
)

urlpatterns = [
    # Homepage
    path('', views.dashboard, name='homepage'),  # Dashboard principale
    
    # Dashboard e gestione eventi
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_event, name='create_event'),
    
    # Foto e gestione foto
    path('event/<int:event_id>/', views.event_photos, name='event_photos'),
    path('event/<int:event_id>/upload/', views.upload_photos, name='upload_photos'),
    path('event/<int:event_id>/upload_zip/', views.upload_zip, name='upload_zip'),
    
    # Azioni su eventi e foto
    path('event/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('delete-photo/<int:photo_id>/', views.delete_photo, name='delete_photo'),

    # Accesso e acquisto
    path('access/', views.access_event, name='access_event'),
    path('acquista-foto/', views.purchase_photos, name='purchase_photos'),

    # Email
    path('event/<int:event_id>/send_email/', views.send_access_code, name='send_access_code'),

    # Carrello
    path('cart/', cart, name='cart_view'),
    path("cart/add/", add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:photo_id>/", remove_from_cart, name="remove_from_cart"),

    # Checkout
    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),

    # Download
    path('download/<str:filename>', views.download_zip, name='download_zip'),
    
    # Media e file handling
    path('check-media/', check_media_path, name='check-media'),
    path('list-media/', views.list_media_files, name='list_media_files'),
    path('list-all-files/', views.list_all_files, name='list_all_files'),

    # Eventi
    #path('photos/all-events/', all_events, name='all_events'),
    #path('event/<str:access_code>/', views.event_detail, name='event_detail'),
    
    # Privacy Policy
    
    path('privacy-policy/<int:event_id>/', privacy_policy, name='privacy_policy'),  # Per un evento specifico
    path('dettagli-privacy/', dettagli_privacy, name='dettagli_privacy'),  # Dettagli privacy
    
    # Invio email con tutti gli eventi
    path('send_all_events_email/', views.send_all_events_email, name='send_all_events_email'),
    path('all-events/', views.all_events, name='all_events'),
    path('privacy-policy-all/', views.privacy_policy_all, name='privacy_policy_all'),
    
    

]

# Configurazione per servire file statici e media in modalità DEBUG
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Servire i file media in produzione (opzionale, utile per debugging)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
