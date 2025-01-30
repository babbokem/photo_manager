from django.urls import path
from . import views  # Importa le view definite nel file views.py
from .views import check_media_path
from .views import create_checkout_session
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    # Homepage
    path('', views.dashboard, name='homepage'),  # Usa dashboard come homepage
    
    # Dashboard e gestione eventi
    path('dashboard/', views.dashboard, name='dashboard'),  # Dashboard principale
    path('create/', views.create_event, name='create_event'),  # Creazione evento
    
    # Foto e gestione foto
    path('event/<int:event_id>/', views.event_photos, name='event_photos'),  # Foto di un evento specifico
    path('event/<int:event_id>/upload/', views.upload_photos, name='upload_photos'),  # Caricamento foto
    path('event/<int:event_id>/upload_zip/', views.upload_zip, name='upload_zip'),  # Caricamento file ZIP
    
    # Azioni su eventi e foto
    path('event/<int:event_id>/delete/', views.delete_event, name='delete_event'),  # Eliminazione evento
    path('delete-photo/<int:photo_id>/', views.delete_photo, name='delete_photo'),  # Eliminazione foto

    # Accesso e acquisto
    path('access/', views.access_event, name='access_event'),  # Accesso tramite codice evento
    path('acquista-foto/', views.purchase_photos, name='purchase_photos'),  # Acquisto foto tramite codice

    # Email
    path('event/<int:event_id>/send_email/', views.send_access_code, name='send_access_code'),  # Invio email con codice accesso

    # Carrello
    path('cart/', views.cart, name='cart'),  # Gestione carrello
    path('check-media/', check_media_path, name='check-media'),
    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),  # URL per iniziare il pagamento
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),
    path('download/<str:filename>/', views.download_zip, name='download_zip'),
    
    ]


if settings.DEBUG:  # Assicurati di abilitare questo solo in fase di sviluppo, in produzione sarà gestito diversamente
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)