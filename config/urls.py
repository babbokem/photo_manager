from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from event_photos import views  # Importa le view della tua app
from event_photos.views import test_image_view 
from event_photos.views import check_media_path
from event_photos.views import test_media_url
from event_photos.views import privacy_policy


urlpatterns = [
    # Admin di Django
    path('admin/', admin.site.urls),

    # App "event_photos"
    path('photos/', include('event_photos.urls')),

    # Homepage reindirizzata alla dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Autenticazione
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),

    # Eventi
    path('event/<int:event_id>/', views.event_photos, name='event_photos'),
    path('event/<int:event_id>/upload_zip/', views.upload_zip, name='upload_zip'),
    path('acquista-foto/<int:event_id>/', views.purchase_photos, name='purchase_photos'),  # Assicurati che questa riga sia presente

    # Homepage (dashboard)
    path('', views.dashboard, name='homepage'),
    path('test-image/', test_image_view, name='test-image'),
    path('check-media/', check_media_path),
    path('test-media-config/', test_media_url),
    path('privacy-policy/<int:event_id>/', privacy_policy, name='privacy_policy'),
    path('list-media/', views.list_media_files, name='list_media_files'),


]

# Configurazione per servire file statici e media solo in modalità DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

