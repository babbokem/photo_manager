import uuid
import os
import zipfile
import shutil
from pathlib import Path
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.timezone import now
import logging

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

    def save(self, *args, **kwargs):
        """
        Override del metodo save per impostare la data di scadenza e processare i file ZIP.
        """
        if not self.expiry_date:
            self.expiry_date = now().date() + timedelta(days=30)

        # Genera codice univoco se non è presente
        if not self.access_code:
            self.access_code = generate_unique_access_code()

        super().save(*args, **kwargs)

        # Scompatta il file ZIP se presente e non ancora elaborato
        if self.zip_file and not os.path.exists(self.get_extracted_path()):
            print(f"ZIP trovato per l'evento: {self.name}. Inizio estrazione.")  # Print aggiunto
            self.process_zip_file()

    def process_zip_file(self):
        """
        Scompatta il file ZIP nella directory associata all'evento e crea oggetti Photo.
        """
        if not self.zip_file:
            print("Nessun file ZIP presente per l'evento.")  # Print aggiunto
            return

        try:
            zip_path = self.zip_file.path
            extract_to = self.get_extracted_path()

            # Assicurati che la directory esista
            os.makedirs(extract_to, exist_ok=True)

            print(f"Estrazione ZIP in: {extract_to}")  # Print aggiunto

            # Estrai i file dal file ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)

            print(f"File ZIP {self.zip_file.name} estratto in {extract_to}")  # Print aggiunto

            # Filtra solo immagini e crea oggetti Photo
            valid_extensions = ('.jpg', '.jpeg', '.png')
            for root, _, files in os.walk(extract_to):
                for file_name in files:
                    if file_name.lower().endswith(valid_extensions):
                        relative_path = os.path.relpath(
                            os.path.join(root, file_name), settings.MEDIA_ROOT
                        )
                        print(f"Salvando foto: {file_name}")  # Print aggiunto
                        Photo.objects.create(
                            event=self,
                            file_path=relative_path,
                            original_name=file_name
                        )
                        print(f"Foto {file_name} salvata nel database.")  # Print aggiunto

        except zipfile.BadZipFile:
            print(f"Il file {self.zip_file.name} non è un archivio ZIP valido.")  # Print aggiunto
        except Exception as e:
            print(f"Errore durante l'estrazione del file ZIP: {e}")  # Print aggiunto

    def get_extracted_path(self):
        """
        Restituisce il percorso della directory in cui scompattare i file ZIP.
        """
        return Path(settings.MEDIA_ROOT) / 'event_photos' / f"event_{self.id}"

    def delete(self, *args, **kwargs):
        """
        Cancella il file ZIP e le immagini associate quando l'evento viene eliminato.
        """
        try:
            # Cancella il file ZIP se esiste
            if self.zip_file and os.path.exists(self.zip_file.path):
                os.remove(self.zip_file.path)
                print(f"ZIP eliminato: {self.zip_file.path}")  # Print aggiunto

            # Cancella la cartella delle immagini dell'evento
            event_folder = os.path.join(settings.MEDIA_ROOT, f'event_photos/event_{self.id}')
            if os.path.exists(event_folder):
                shutil.rmtree(event_folder)
                print(f"Cartella immagini eliminata: {event_folder}")  # Print aggiunto

        except Exception as e:
            print(f"Errore durante l'eliminazione dell'evento: {e}")  # Print aggiunto

        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

class Photo(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="photos")
    file_path = models.ImageField(upload_to=upload_to_event)
    original_name = models.CharField(max_length=255, blank=True, verbose_name="Nome Originale del File")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Caricato il")
    purchased = models.BooleanField(default=False, verbose_name="Acquistata")
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

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
                print(f"Foto eliminata: {self.file_path.path}")  # Print aggiunto

        except Exception as e:
            print(f"Errore durante l'eliminazione della foto: {e}")  # Print aggiunto

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Foto di {self.event.name} - {self.original_name}"
