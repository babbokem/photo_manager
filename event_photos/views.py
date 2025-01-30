import os
import zipfile
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from .models import Event, Photo
from .forms import EventForm, PhotoUploadForm
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
import uuid
from django.http import HttpResponse
import stripe
from django.http import JsonResponse
import json
from django.core.mail import EmailMessage
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.utils.timezone import now
from io import BytesIO
from django.http import FileResponse, Http404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
import logging


logger = logging.getLogger(__name__)




from django.core.mail import send_mail

def download_zip(request, filename):
    # Percorso completo del file ZIP nella cartella temporanea
    zip_path = os.path.join(settings.TEMP_ZIPS_DIR, filename)


    if not os.path.exists(zip_path):
        raise Http404("Il file richiesto non esiste.")

    # Restituisce il file come risposta
    response = FileResponse(open(zip_path, 'rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Cancella il file dopo il download
    
    
    try:
        os.remove(zip_path)
    except Exception as e:
        print(f"Errore durante la cancellazione del file {zip_path}: {e}")

    return response

    return response

def checkout_success(request):
    # Recupera gli ID delle foto acquistate e l'email dalla sessione
    photo_ids = request.session.get('purchased_photo_ids', [])
    customer_email = request.session.get('customer_email', None)

    if not photo_ids or not customer_email:
        return JsonResponse({'error': 'Nessun acquisto trovato'}, status=400)

    # Recupera le foto acquistate
    photos = Photo.objects.filter(id__in=photo_ids)

    # Crea un file ZIP in memoria
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for photo in photos:
            # Aggiungi ogni foto al file ZIP
            file_path = photo.file_path.path
            file_name = os.path.basename(photo.file_path.name)
            zip_file.write(file_path, arcname=file_name)

    # Salva il file ZIP in una directory temporanea
    zip_filename = f"acquisto_{now().strftime('%Y%m%d%H%M%S')}.zip"
    zip_path = os.path.join(settings.TEMP_ZIPS_DIR, zip_filename)
    with open(zip_path, 'wb') as f:
        f.write(zip_buffer.getvalue())

    # Costruisci il link per il download
    zip_url = request.build_absolute_uri(reverse('download_zip', args=[zip_filename]))

    # Crea il contenuto dell'email
    subject = "Le tue foto acquistate"
    message = (
        "Grazie per il tuo acquisto!\n\n"
        "Puoi scaricare tutte le tue foto al seguente link:\n"
        f"{zip_url}\n\n"
        "Il link sarà valido per un periodo limitato.\n"
        "Grazie per averci scelto!"
    )

    try:
        # Invia l'email al cliente
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [customer_email],
            fail_silently=False,
        )
        # Pulisci la sessione
        request.session.pop('purchased_photo_ids', None)
        request.session.pop('customer_email', None)
        return render(request, 'checkout_success.html', {'zip_url': zip_url})
    except Exception as e:
        return JsonResponse({'error': f'Errore durante l\'invio dell\'email: {e}'}, status=500)




def checkout_cancel(request):
    return render(request, 'checkout_cancel.html')


from django.views.decorators.csrf import csrf_exempt
import stripe



stripe.api_key = settings.STRIPE_SECRET_KEY

# views.py
def create_checkout_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            photo_ids = data.get('photo_ids', [])
            customer_email = data.get('email', '')  # Email del cliente

            if not photo_ids:
                return JsonResponse({'error': 'Nessuna foto selezionata'}, status=400)

            # Salva nella sessione
            request.session['purchased_photo_ids'] = photo_ids
            request.session['customer_email'] = customer_email

            # Recupera le foto dal database
            photos = Photo.objects.filter(id__in=photo_ids)
            line_items = [
                {
                    'price_data': {
                        'currency': 'eur',
                        'unit_amount': int(photo.event.price_per_photo * 100),  # Prezzo in centesimi
                        'product_data': {
                            'name': photo.original_name,
                        },
                    },
                    'quantity': 1,
                }
                for photo in photos
            ]

            # Crea la sessione di checkout con Stripe
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=request.build_absolute_uri('/photos/checkout/success/'),
                cancel_url=request.build_absolute_uri('/photos/checkout/cancel/'),
            )

            return JsonResponse({'id': checkout_session.id})
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Errore nella decodifica del JSON'}, status=400)
        except stripe.error.StripeError as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Metodo non consentito'}, status=405)






def process_payment(request):
    try:
        # Crea il pagamento con Stripe
        payment_intent = stripe.PaymentIntent.create(
            amount=1000,  # Importo in centesimi (es. 10,00 EUR)
            currency='eur',
            description='Acquisto foto',
            payment_method_types=['card'],
        )

        # Mostra il messaggio di successo
        messages.success(request, "Acquisto completato con successo!")
        return redirect('checkout_success')
    except stripe.error.StripeError as e:
        messages.error(request, f"Errore durante il pagamento: {e}")
        return redirect('checkout_cancel')








def checkout(request):
    cart_items = request.session.get('cart_items', [])
    if not cart_items:
        messages.error(request, "Il carrello è vuoto.")
        return redirect('cart')

    line_items = []
    for photo_id in cart_items:
        photo = Photo.objects.get(id=photo_id)
        line_items.append({
            'price_data': {
                'currency': 'eur',
                'unit_amount': int(photo.price * 100),  # Prezzo in centesimi
                'product_data': {
                    'name': photo.original_name,
                    'images': [request.build_absolute_uri(photo.file_path.url)],
                },
            },
            'quantity': 1,
        })

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri('/checkout/success/'),
            cancel_url=request.build_absolute_uri('/checkout/cancel/'),
        )
        print("Success URL:", request.build_absolute_uri('/checkout/success/'))  # Debug
        return redirect(checkout_session.url)
    except stripe.error.StripeError as e:
        messages.error(request, f"Errore durante il checkout: {e}")
        return redirect('cart')



def is_admin(user):
    return user.is_superuser  # Oppure controlla un attributo custom nel tuo modello utente

@login_required
def dashboard(request):
    query = request.GET.get('q', '')  # Usa una stringa vuota come valore di default se 'q' non è presente
    events = Event.objects.all()

    if query:
        events = events.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            # Generazione codice univoco
            unique_code_generated = False
            while not unique_code_generated:
                access_code = uuid.uuid4().hex[:8]  # Genera un codice univoco di 8 caratteri
                if not Event.objects.filter(access_code=access_code).exists():
                    event.access_code = access_code
                    unique_code_generated = True

            try:
                event.save()
                messages.success(request, "Evento creato con successo!")
                return redirect('dashboard')
            except IntegrityError:
                messages.error(request, "Errore: il codice di accesso esiste già, riprova.")
        else:
            messages.error(request, "Errore durante la creazione dell'evento.")
    else:
        form = EventForm()

    return render(request, 'dashboard.html', {
        'events': events,
        'form': form,
        'query': query,
    })







def privacy_policy(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        # Salva il consenso nella sessione o nel database
        request.session[f'privacy_accepted_{event_id}'] = True
        return redirect('purchase_photos', event_id=event.id)


    return render(request, 'privacy_policy.html', {'event': event})



def test_media_url(request):
    return HttpResponse(f"MEDIA_URL: {settings.MEDIA_URL}<br>MEDIA_ROOT: {settings.MEDIA_ROOT}")


def check_media_path(request):
    media_path = os.path.join(settings.MEDIA_ROOT, 'event_photos/event_6/IMG-20241208-WA0003.jpg')
    if os.path.exists(media_path):
        return HttpResponse(f"File trovato in: {media_path}")
    else:
        return HttpResponse(f"File NON trovato! Django sta cercando in: {media_path}")


@login_required
def event_photos(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    photos = event.photos.all()

    if request.method == 'POST' and 'add_to_cart' in request.POST:
        selected_photos = request.POST.getlist('photos')
        if selected_photos:
            messages.success(request, f"Hai aggiunto {len(selected_photos)} foto al carrello!")
        else:
            messages.warning(request, "Non hai selezionato alcuna foto.")

    return render(request, 'event_photos.html', {
        'event': event,
        'photos': photos,
    })


@login_required
def send_access_code(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        recipients = request.POST.get('recipients')
        recipient_list = [email.strip() for email in recipients.split(',')]

        # Modifica del link per includere la pagina di accettazione privacy
        access_url = request.build_absolute_uri(f"/privacy-policy/{event.id}/")

        subject = f"Codice di Accesso per l'Evento: {event.name}"
        message = (
            f"Ciao,\n\n"
            f"Ti è stato condiviso il codice di accesso per l'evento \"{event.name}\":\n\n"
            f"Codice: {event.access_code}\n"
            f"Prezzo per Foto: {event.price_per_photo} €\n\n"
            f"Prima di accedere, accetta la nostra politica sulla privacy qui: {access_url}\n\n"
            f"Grazie!"
        )

        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, recipient_list)
            messages.success(request, "Email inviata con successo!")
        except Exception as e:
            messages.error(request, f"Errore durante l'invio dell'email: {e}")

        return redirect('dashboard')

    return render(request, 'send_email.html', {'event': event})




@login_required
def purchase_photos(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    photos = event.photos.all()
    context = {
        'event': event,
        'photos': photos,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,  # Passa la chiave al template
    }
    return render(request, 'purchase_photos.html', context)


@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.delete()
    messages.success(request, f"L'evento '{event.name}' è stato eliminato con successo.")
    next_url = request.GET.get('next', 'dashboard')
    return redirect(next_url)





@login_required
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Evento creato con successo!")
            return redirect('dashboard')
        else:
            messages.error(request, "Errore durante la creazione dell'evento.")
    else:
        form = EventForm()

    return render(request, 'create_event.html', {'form': form})




def upload_photos(request, event_id):
    """
    Carica foto per un evento specifico.
    """
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        form = PhotoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            photos = request.FILES.getlist('photos')  # Recupera tutte le foto caricate
            for photo in photos:
                Photo.objects.create(event=event, file_path=photo, original_name=photo.name)
            messages.success(request, f"{len(photos)} foto caricate con successo!")
            return redirect('event_photos', event_id=event.id)
        else:
            messages.error(request, "Errore durante il caricamento delle foto.")
    else:
        form = PhotoUploadForm()

    return render(request, 'upload_photos.html', {
        'event': event,
        'form': form,
    })







def list_media_files(request):
    media_path = settings.MEDIA_ROOT  # Percorso della cartella persistente
    try:
        files = os.listdir(media_path)  # Elenco dei file nella cartella
        files_list = "<br>".join(files)  # Crea una lista HTML dei file
        return HttpResponse(f"File nella cartella media:<br>{files_list}")
    except Exception as e:
        return HttpResponse(f"Errore nell'accesso alla cartella: {str(e)}")






@login_required
@login_required
def upload_zip(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST' and request.FILES.get('zip_file'):
        zip_file = request.FILES['zip_file']

        # Salva il file ZIP nella cartella persistente di Railway
        zip_path = os.path.join(settings.MEDIA_ROOT, 'event_zips', str(event.id), zip_file.name)
        os.makedirs(os.path.dirname(zip_path), exist_ok=True)  # Crea la cartella se non esiste
        print(f"Salvando ZIP in: {zip_path}")  # Debug

        with open(zip_path, 'wb') as f:
            f.write(zip_file.read())  # Salva il file ZIP nella cartella

        # Scompatta il file ZIP direttamente nella cartella persistente
        extracted_folder = os.path.join(settings.MEDIA_ROOT, 'event_photos', str(event.id))  # Percorso per le foto scompattate
        os.makedirs(extracted_folder, exist_ok=True)  # Crea la cartella per le foto estratte se non esiste
        print(f"Scompattando in: {extracted_folder}")  # Debug

        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                print(f"Verifica file: {file_name}")  # Debug
                if file_name.lower().endswith(('png', 'jpg', 'jpeg')):  # Verifica se è un'immagine
                    extracted_file_path = os.path.join(extracted_folder, os.path.basename(file_name))
                    print(f"Estraendo: {extracted_file_path}")  # Debug

                    # Estrai il file nella cartella appropriata
                    with open(extracted_file_path, 'wb') as f:
                        f.write(zip_ref.read(file_name))

                    # Salva il percorso del file estratto nel database
                    relative_path = os.path.relpath(extracted_file_path, settings.MEDIA_ROOT)
                    print(f"Salvando nel database con il percorso: {relative_path}")  # Debug
                    Photo.objects.create(event=event, file_path=relative_path, original_name=os.path.basename(file_name))

        messages.success(request, "Foto caricate con successo dal file ZIP!")
        return redirect('event_photos', event_id=event.id)

    return render(request, 'upload_zip.html', {'event': event})









@login_required
def access_event(request):
    """
    Consente di accedere a un evento tramite un codice di accesso.
    """
    if request.method == 'POST':
        access_code = request.POST.get('access_code', '').strip()
        try:
            # Cerca l'evento con il codice di accesso fornito
            event = Event.objects.get(access_code=access_code)
            return redirect('event_photos', event_id=event.id)
        except Event.DoesNotExist:
            messages.error(request, "Codice di accesso non valido.")

    return render(request, 'access_event.html')


@login_required
def cart(request):
    cart_items = request.session.get('cart_items', [])

    if request.method == 'POST':
        if 'photo_id' in request.POST:
            photo_id = request.POST.get('photo_id')
            if photo_id and photo_id not in cart_items:
                cart_items.append(photo_id)
                request.session['cart_items'] = cart_items
                messages.success(request, "Foto aggiunta al carrello.")
            else:
                messages.warning(request, "Questa foto è già nel carrello.")
        
        if 'checkout' in request.POST:
            return redirect('create_checkout_session')

    photos = Photo.objects.filter(id__in=cart_items)
    total_amount = sum(photo.price for photo in photos) * 100  # Converti in centesimi

    return render(request, 'cart.html', {
        'photos': photos,
        'cart_count': len(cart_items),
        'total_amount': total_amount,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
    })
@login_required
def delete_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    photo.delete()
    messages.success(request, f"La foto '{photo.original_name}' è stata eliminata con successo.")
    return redirect('dashboard')


def test_image_view(request):
    return render(request, 'test_image.html')

def list_media_files(request):
    media_path = settings.MEDIA_ROOT  # Percorso di /app/media (già definito nelle settings)

    # Verifica che la cartella principale esista
    if not os.path.exists(media_path):
        return HttpResponse(f"La cartella {media_path} non esiste.", status=404)

    try:
        # Crea una lista vuota per immagazzinare i file immagine
        image_files = []
        
        # Esplora ricorsivamente la cartella e le sue sottocartelle
        for root, dirs, files in os.walk(media_path):
            # Escludi le cartelle nascoste (opzionale)
            dirs[:] = [d for d in dirs if not d.startswith('.')]  # Esclude cartelle che iniziano con punto
            for file in files:
                if file.lower().endswith(('jpg', 'jpeg', 'png')):  # Filtro per immagini
                    # Aggiungi il percorso completo del file
                    image_files.append(os.path.join(root, file))

        # Se non ci sono file immagine, restituisci un errore
        if not image_files:
            return HttpResponse("Nessuna immagine trovata.", status=404)

        # Mostra i file trovati
        return render(request, 'list_media_files.html', {'files': image_files})

    except Exception as e:
        return HttpResponse(f"Errore durante la lettura dei file: {str(e)}", status=500)
    

    

    import os
from django.http import HttpResponse
from django.shortcuts import render

def list_all_files(request):
    # Percorso di partenza, qui puoi mettere "/" per esplorare tutto il filesystem
    root_path = '/'
    
    # Crea una lista vuota per i file
    all_files = []
    
    try:
        # Esplora ricorsivamente tutte le directory e i file a partire da '/'
        for root, dirs, files in os.walk(root_path):
            for file in files:
                # Aggiungi ogni file alla lista, inclusi il percorso completo
                all_files.append(os.path.join(root, file))
        
        # Se non ci sono file
        if not all_files:
            return HttpResponse("Nessun file trovato.", status=404)

        # Rendi la lista di file disponibile per il template
        return render(request, 'list_all_files.html', {'files': all_files})
    
    except Exception as e:
        return HttpResponse(f"Errore durante la lettura dei file: {str(e)}", status=500)
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
                    print(f"Salvando immagine nel database: {file_name}, percorso: {relative_path}")  # Debug
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
