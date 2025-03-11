from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from event_photos import views  # Importa tutte le view della tua app

urlpatterns = [
    # ✅ Admin di Django
    path('admin/', admin.site.urls),

    # ✅ Include le URL dell'app "event_photos"
    path('photos/', include('event_photos.urls')),

    # ✅ Homepage reindirizzata alla dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.dashboard, name='homepage'),  # Per reindirizzare la homepage

    # ✅ Autenticazione
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),

    # ✅ Eventi e foto
    path('event/<int:event_id>/', views.event_photos, name='event_photos'),
    path('event/<int:event_id>/upload_zip/', views.upload_zip, name='upload_zip'),
    path('acquista-foto/<int:event_id>/', views.purchase_photos, name='purchase_photos'),

    # ✅ Privacy Policy
    path('privacy-policy/<int:event_id>/', views.privacy_policy, name='privacy_policy'),
    path('dettagli-privacy/', views.dettagli_privacy, name='dettagli_privacy'),  # ✅ Aggiunto questo URL

    # ✅ Debug/Testing
    path('test-image/', views.test_image_view, name='test-image'),
    path('check-media/', views.check_media_path),
    path('test-media-config/', views.test_media_url),
    path('list-media/', views.list_media_files, name='list_media_files'),
    path('list-all-files/', views.list_all_files, name='list_all_files'),
    path('view-foto/', views.view_foto, name='view_foto'),
    

    # ✅ Servire file STATICI e MEDIA in produzione
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

# ✅ Aggiunge il supporto per i file statici/media in modalità DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
