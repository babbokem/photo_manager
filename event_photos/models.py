import uuid
from datetime import timedelta, date
from django.db import models
from django.conf import settings
from pathlib import Path
import os
import zipfile
import logging
import shutil
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def validate_zip_file(value):
    """
    Valida che il file caricato sia un archivio ZIP.
    """
    if not value.name.endswith('.zip'):
        raise ValidationError("Il file caricato deve essere un archivio ZIP.")

def upload_to_event(instance, filename):
    """
    Restituisce il percorso personalizzato per il caricamento delle foto.
    """
    return f"event_photos/event_{instance.event.id}/{filename}"

def generate_unique_access_code():
    """
    Genera un codice di accesso univoco.
    """
    while True:
        code = uuid.uuid4().hex[:10]
        if not Event.objects.filter(access_code=code).exists():
            return code

class Event(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nome Evento")
    description = models.TextField(blank=True, verbose_name="Descrizione")
    date_created = models.DateField(auto_now_add=True, verbose_name="Data di Creazione")
    expiry_date = models.DateField(blank=True, null=True, verbose_name="Data di Scadenza")
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
    price_per_photo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name="Prezzo per Foto"
    )

    def save(self, *args, **kwargs):
        """
        Override del metodo save per impostare la data di scadenza e processare i file ZIP.
        """
        if not self.expiry_date:
            self.expiry_date = date.today() + timedelta(days=30)

        # Genera codice univoco se non è presente
        if not self.access_code:
            self.access_code = generate_unique_access_code()

        super().save(*args, **kwargs)

        # Scompatta il file ZIP se presente e non ancora elaborato
        if self.zip_file and not os.path.exists(self.get_extracted_path()):
            self.process_zip_file()

    def process_zip_file(self):
        """
        Scompatta il file ZIP nella directory associata all'evento e crea oggetti Photo.
        """
        if not self.zip_file:
            logger.warning("Nessun file ZIP presente per l'evento.")
            return

        try:
            zip_path = self.zip_file.path
            extract_to = self.get_extracted_path()

            # Assicurati che la directory esista
            os.makedirs(extract_to, exist_ok=True)

            print(f"Estrazione ZIP in: {extract_to}")  # Debugging

            # Estrai i file dal file ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)

            print(f"File ZIP {self.zip_file.name} estratto in {extract_to}")  # Debugging

            # Filtra solo immagini e crea oggetti Photo
            valid_extensions = ('.jpg', '.jpeg', '.png')
            for root, _, files in os.walk(extract_to):
                for file_name in files:
                    if file_name.lower().endswith(valid_extensions):
                        relative_path = os.path.relpath(
                            os.path.join(root, file_name), settings.MEDIA_ROOT
                        )
                        Photo.objects.create(
                            event=self,
                            file_path=relative_path,
                            original_name=file_name
                        )
                        print(f"Foto {file_name} salvata nel database.")  # Debugging

        except zipfile.BadZipFile:
            logger.error(f"Il file {self.zip_file.name} non è un archivio ZIP valido.")
        except Exception as e:
            logger.error(f"Errore durante l'estrazione del file ZIP: {e}")

    def delete(self, *args, **kwargs):
        """
        Cancella il file ZIP e le immagini associate quando l'evento viene eliminato.
        """
        try:
            # Cancella il file ZIP se esiste
            if self.zip_file and os.path.exists(self.zip_file.path):
                os.remove(self.zip_file.path)
                logger.info(f"ZIP eliminato: {self.zip_file.path}")

            # Cancella la cartella delle immagini dell'evento
            event_folder = os.path.join(settings.MEDIA_ROOT, f'event_photos/event_{self.id}')
            if os.path.exists(event_folder):
                shutil.rmtree(event_folder)
                logger.info(f"Cartella immagini eliminata: {event_folder}")

        except Exception as e:
            logger.error(f"Errore durante l'eliminazione dell'evento: {e}")

        super().delete(*args, **kwargs)

    def get_extracted_path(self):
        """
        Restituisce il percorso della directory in cui scompattare i file ZIP.
        """
        return Path(settings.MEDIA_ROOT) / 'event_photos' / f"event_{self.id}"

    def __str__(self):
        return self.name

class Photo(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="photos")
    file_path = models.ImageField(upload_to=upload_to_event)
    original_name = models.CharField(max_length=255, blank=True, verbose_name="Nome Originale del File")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Caricato il")
    purchased = models.BooleanField(default=False, verbose_name="Acquistata")

    def save(self, *args, **kwargs):
        """
        Memorizza il nome originale del file se non già presente.
        """
        if not self.original_name:
            self.original_name = os.path.basename(self.file_path.name)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Elimina il file fisico quando la foto viene eliminata.
        """
        try:
            if self.file_path and os.path.exists(self.file_path.path):
                os.remove(self.file_path.path)
                logger.info(f"Foto eliminata: {self.file_path.path}")

        except Exception as e:
            logger.error(f"Errore durante l'eliminazione della foto: {e}")

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Foto di {self.event.name} - {self.original_name}"
