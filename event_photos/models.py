import uuid
import os
import zipfile
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.urls import reverse
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)


def validate_zip_file(value):
    if not value.name.endswith('.zip'):
        raise ValidationError("Il file caricato deve essere un archivio ZIP.")


def upload_to_event(instance, filename):
    return f"event_photos/event_{instance.event.id}/{filename}"


def generate_unique_access_code():
    while True:
        code = uuid.uuid4().hex[:10]
        if not Event.objects.filter(access_code=code).exists():
            return code


class Event(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nome Evento")
    description = models.TextField(blank=True, verbose_name="Descrizione")
    date_created = models.DateField(auto_now_add=True, verbose_name="Data di Creazione")
    expiry_date = models.DateField(blank=True, null=True, verbose_name="Data di Scadenza")
    price_per_photo = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    access_code = models.CharField(
        max_length=20,
        unique=True,
        default=generate_unique_access_code,
        verbose_name="Codice di Accesso"
    )
    zip_file = models.FileField(
        upload_to='event_zips/',
        blank=True,
        null=True,
        verbose_name="Carica ZIP",
        validators=[validate_zip_file]
    )

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'access_code': self.access_code})

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = now().date() + timedelta(days=30)

        if not self.access_code:
            self.access_code = generate_unique_access_code()

        super().save(*args, **kwargs)

        if self.zip_file and not self.photos.exists():
            print(f"ZIP trovato per l'evento: {self.name}. Inizio estrazione.")
            self.process_zip_file()

    def process_zip_file(self):
        try:
            from django.core.files.storage import default_storage  # IMPORT CORRETTO
            print("💾 SONO DENTRO MODEL")
            print("🌍 STORAGE IN USO:", default_storage.__class__)

            if not self.zip_file:
                print("Nessun file ZIP presente per l'evento.")
                return

            with self.zip_file.open('rb') as zip_file_obj:
                with zipfile.ZipFile(zip_file_obj) as zip_ref:
                    for file_name in zip_ref.namelist():
                        if file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                            image_data = zip_ref.read(file_name)
                            image_name = os.path.basename(file_name)

                            photo = Photo(event=self, original_name=image_name)
                            photo.file_path.save(image_name, ContentFile(image_data))
                            photo.save()

                            print(f"✅ Salvata su storage: {photo.file_path.name}")

        except Exception as e:
            print(f"❌ ERRORE GLOBALE IN process_zip_file: {e}")

    def delete(self, *args, **kwargs):
        try:
            from django.core.files.storage import default_storage
            if self.zip_file:
                default_storage.delete(self.zip_file.name)
                print(f"ZIP eliminato da storage: {self.zip_file.name}")

            for photo in self.photos.all():
                photo.delete()

        except Exception as e:
            print(f"Errore durante l'eliminazione dell'evento: {e}")

        super().delete(*args, **kwargs)


class Photo(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="photos")
    file_path = models.ImageField(upload_to=upload_to_event)
    original_name = models.CharField(max_length=255, blank=True, verbose_name="Nome Originale del File")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Caricato il")
    purchased = models.BooleanField(default=False, verbose_name="Acquistata")
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if not self.original_name:
            self.original_name = os.path.basename(self.file_path.name)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        try:
            from django.core.files.storage import default_storage
            if self.file_path:
                default_storage.delete(self.file_path.name)
                print(f"Foto eliminata da storage: {self.file_path.name}")
        except Exception as e:
            print(f"Errore durante l'eliminazione della foto: {e}")

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Foto di {self.event.name} - {self.original_name}"
