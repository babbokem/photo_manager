from django.urls import path
from . import views  # Importa le view definite nel file views.py

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
]
