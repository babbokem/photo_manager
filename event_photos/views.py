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
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)




from django.core.mail import send_mail
def download_zip(request, filename):
    zip_path = f"temp/{filename}" if settings.USE_S3 else os.path.join(settings.TEMP_ZIPS_DIR, filename)

    if settings.USE_S3:
        if default_storage.exists(zip_path):
            return redirect(f"{settings.MEDIA_URL}{zip_path}")
        raise Http404("Il file richiesto non esiste su S3.")
    else:
        if not os.path.exists(zip_path):
            raise Http404("Il file richiesto non esiste.")
        response = FileResponse(open(zip_path, 'rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        os.remove(zip_path)  # Rimuove il file dopo il download
        return response

### **Funzione di checkout con ZIP generato su S3**



### **Funzione di checkout con ZIP generato su S3**
def checkout_success(request):
    photo_ids = request.session.get('purchased_photo_ids', [])
    customer_email = request.session.get('customer_email', None)

    if not photo_ids or not customer_email:
        return JsonResponse({'error': 'Nessun acquisto trovato'}, status=400)

    photos = Photo.objects.filter(id__in=photo_ids)
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for photo in photos:
            file_name = os.path.basename(photo.file_path.name)
            with default_storage.open(photo.file_path.name, 'rb') as f:
                zip_file.writestr(file_name, f.read())

    zip_filename = f"acquisto_{now().strftime('%Y%m%d%H%M%S')}.zip"
    zip_path = f"temp/{zip_filename}" if settings.USE_S3 else os.path.join(settings.TEMP_ZIPS_DIR, zip_filename)

    if settings.USE_S3:
        default_storage.save(zip_path, ContentFile(zip_buffer.getvalue()))
        zip_url = f"{settings.MEDIA_URL}{zip_path}"
    else:
        with open(zip_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        zip_url = request.build_absolute_uri(reverse('download_zip', args=[zip_filename])).replace("http://", "https://")

    send_mail("Le tue foto acquistate", f"Scaricale qui: {zip_url}", settings.EMAIL_HOST_USER, [customer_email])
    request.session.pop('purchased_photo_ids', None)
    request.session.pop('customer_email', None)
    
    return render(request, 'checkout_success.html', {'zip_url': zip_url})






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
            customer_email = data.get('email', '')

            if not photo_ids:
                return JsonResponse({'error': 'Nessuna foto selezionata'}, status=400)

            request.session['purchased_photo_ids'] = photo_ids
            request.session['customer_email'] = customer_email

            photos = Photo.objects.filter(id__in=photo_ids)
            line_items = [{
                'price_data': {
                    'currency': 'eur',
                    'unit_amount': int(photo.event.price_per_photo * 100),
                    'product_data': {'name': photo.original_name},
                },
                'quantity': 1,
            } for photo in photos]

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
    print("✅ ENTRATO NELLA VIEW dashboard")

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
    if request.method == 'POST':
        request.session[f'privacy_accepted_{event_id}'] = True
        request.session.modified = True

        # 🔍 Recupera il codice di accesso dalla sessione o dall'URL
        access_code = request.GET.get('access_code', request.session.get(f'access_code_{event_id}', ''))

        print(f"DEBUG - Privacy accettata per l'evento {event_id}")
        print(f"DEBUG - Codice di accesso recuperato: '{access_code}'")

        # ✅ Dopo la privacy, reindirizza all'evento passando il codice
        return redirect(f'/event/{event_id}/?access_code={access_code}')

    return render(request, 'privacy_policy.html', {'event_id': event_id})
















def test_media_url(request):
    return HttpResponse(f"MEDIA_URL: {settings.MEDIA_URL}<br>MEDIA_ROOT: {settings.MEDIA_ROOT}")


def check_media_path(request):
    media_path = os.path.join(settings.MEDIA_ROOT, 'event_photos/event_6/IMG-20241208-WA0003.jpg')
    if os.path.exists(media_path):
        return HttpResponse(f"File trovato in: {media_path}")
    else:
        return HttpResponse(f"File NON trovato! Django sta cercando in: {media_path}")



def dettagli_privacy(request):
    return render(request, 'dettagli_privacy.html')  # Assicurati di avere questo file HTML











def event_photos(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    photos = event.photos.all()

    # 🔍 Recupera il carrello dalla sessione
    cart_data = request.session.get("cart", {})
    selected_photo_ids = []
    cart_photos = []
    total_amount = 0

    for event_items in cart_data.values():
        for item in event_items:
            selected_photo_ids.append(item.get("photo_id"))
            cart_photos.append(item)
            total_amount += item.get("price", 0)

    return render(request, 'event_photos.html', {
        'event': event,
        'photos': photos,
        'cart_photos': cart_photos,
        'cart_total': total_amount,
        'selected_photo_ids': selected_photo_ids,
    })













@login_required
def send_access_code(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        recipients = request.POST.get('recipients')
        recipient_list = [email.strip() for email in recipients.split(',')]

        # Link alla privacy policy
        
        
        privacy_url = request.build_absolute_uri(reverse('privacy_policy_all'))

        # Link all'evento
        access_url = request.build_absolute_uri(f"/evento/{event.id}/")

        # Ottenere la prima foto come anteprima
        first_photo = event.photos.all().first()
        foto_anteprima = request.build_absolute_uri(first_photo.file_path.url) if first_photo else request.build_absolute_uri('/static/images/default_event.jpg')

       
        
        # Generare il contenuto HTML dell'email
        # Aggiungi i percorsi assoluti delle icone dei social
        social_icons = {
        "logo": request.build_absolute_uri(settings.STATIC_URL + "icon/logo.png"),
        "whatsapp": request.build_absolute_uri(settings.STATIC_URL + "icon/whatsapp.png"),
        "instagram": request.build_absolute_uri(settings.STATIC_URL + "icon/instagram.png"),
        "facebook": request.build_absolute_uri(settings.STATIC_URL + "icon/facebook.png"),
        "email": request.build_absolute_uri(settings.STATIC_URL + "icon/email.png"),
        }
        
        
        
        html_content = render_to_string("event_email.html", {
            "cliente_nome": "Cliente",
            "access_code": event.access_code,
            "link_evento": privacy_url,
            "foto_anteprima": foto_anteprima,
            "price_per_photo": event.price_per_photo,
            "privacy_url": privacy_url,
            "social_icons": social_icons  # ✅ Passo gli URL assoluti al template
        })

        text_content = strip_tags(html_content)

        try:
            email = EmailMultiAlternatives(
                subject=f"Codice di Accesso per l'Evento: {event.name}",
                body=text_content,
                from_email=settings.EMAIL_HOST_USER,
                to=recipient_list,
            )
            email.attach_alternative(html_content, "text/html")  
            email.send()

            messages.success(request, "Email inviata con successo!")
        except Exception as e:
            messages.error(request, f"Errore durante l'invio dell'email: {e}")

        return redirect('dashboard')

    return render(request, 'send_email.html', {'event': event})






def purchase_photos(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    photos = event.photos.all()

       # Controlla se la privacy è stata accettata
    privacy_accepted = request.session.get(f'privacy_accepted_{event_id}', False)
    if not privacy_accepted:
        messages.error(request, "Devi accettare la privacy policy per procedere all'acquisto.")
        return redirect('privacy_policy', event_id=event.id)
    context = {
        'event': event,
        'photos': photos,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,  # Passa la chiave al template
    }
    return render(request, 'purchase_photos.html', context)


@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    photos = event.photos.all()

    for photo in photos:
        default_storage.delete(photo.file_path.name)

    event.delete()
    messages.success(request, "Evento e foto eliminati con successo.")
    return redirect('dashboard')





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

















@login_required
def upload_zip(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    print("✅ ENTRATO NELLA VIEW upload_zip")  # <-- Terminale
    messages.info(request, "👀 Sei entrato nella funzione upload_zip")  # <-- Browser

    if request.method == 'POST' and request.FILES.get('zip_file'):
        zip_file = request.FILES['zip_file']
        zip_path = f"event_zips/{event.id}/{zip_file.name}"
        
        
        
        print("🌍 STORAGE IN USO:", default_storage.__class__)  # <<<<< QUI
        
        
        
        saved_zip_path = default_storage.save(zip_path, ContentFile(zip_file.read()))
          

        try:
            with default_storage.open(saved_zip_path, 'rb') as f:
                with zipfile.ZipFile(f, 'r') as zip_ref:
                    for file_name in zip_ref.namelist():
                        if file_name.lower().endswith(('jpg', 'jpeg', 'png')):
                            image_data = zip_ref.read(file_name)
                            final_path = f"event_photos/{event.id}/{os.path.basename(file_name)}"
                            saved_image_path = default_storage.save(final_path, ContentFile(image_data))
                            Photo.objects.create(event=event, file_path=saved_image_path, original_name=os.path.basename(file_name))
                            
        except zipfile.BadZipFile:
            messages.error(request, "Il file caricato non è un archivio ZIP valido.")
            return redirect('event_photos', event_id=event.id)

        messages.success(request, "Foto caricate con successo su S3!")
        return redirect('event_photos', event_id=event.id)

    return render(request, 'upload_zip.html', {'event': event})










def access_event(request):
    """
    Consente l'accesso a un evento tramite un codice di accesso.
    """
    if request.method == 'POST':
        access_code = request.POST.get('access_code', '').strip()
        event = Event.objects.filter(access_code=access_code).first()

        if event:
            # Salva nella sessione che l'utente ha accettato la privacy policy
            request.session[f'privacy_accepted_{event.id}'] = True
            request.session.modified = True  # Assicura che la sessione venga salvata

            messages.success(request, "Accesso effettuato con successo!")
            return redirect('event_photos', event_id=event.id)
        else:
            messages.error(request, "Codice di accesso non valido. Riprova.")

    return render(request, 'access_event.html')




def cart(request):
    cart_data = request.session.get("cart", {})
    photos = []
    total_amount = 0

    for event_id, items in cart_data.items():
        for item in items:
            photo = Photo.objects.filter(id=item["photo_id"]).first()
            if photo:
                photos.append({
                    "photo_id": photo.id,
                    "photo_url": photo.file_path.url,
                    "event_name": photo.event.name,
                    "price": float(photo.event.price_per_photo),
                })
                total_amount += float(photo.event.price_per_photo)

    return render(request, 'cart.html', {
        'photos': photos,
        'cart_count': len(photos),
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







def test_storage(request):
    return HttpResponse(f"""
        ✅ USE_S3: {getattr(settings, 'USE_S3', 'NON TROVATO')}<br>
        📦 STORAGE IN USO: {default_storage.__class__}<br>
        📸 MEDIA_URL: {settings.MEDIA_URL}
    """)


def process_zip_file(self):
    print("✅ ENTRATO NELLA VIEW process_zip")

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
                    print(f"Foto estratta: {relative_path}")  # Debugging
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




def view_foto(request):
    # Percorso della cartella in cui sono salvate le foto
    media_path = os.path.join(settings.MEDIA_ROOT, 'event_photos')

    # Verifica che la cartella esista
    if not os.path.exists(media_path):
        return HttpResponse(f"La cartella {media_path} non esiste.", status=404)

    try:
        # Crea una lista per memorizzare i file immagine
        image_files = []

        # Esplora la cartella e le sue sottocartelle
        for root, dirs, files in os.walk(media_path):
            # Aggiungi i file immagine alla lista
            for file in files:
                if file.lower().endswith(('jpg', 'jpeg', 'png')):  # Aggiungi il filtro per immagini
                    # Aggiungi il percorso relativo alla foto
                    relative_path = os.path.relpath(os.path.join(root, file), settings.MEDIA_ROOT)
                    image_files.append(relative_path)

        # Se non ci sono immagini, restituisci un errore
        if not image_files:
            return HttpResponse("Nessuna immagine trovata.", status=404)

        # Passa i file trovati al template
        return render(request, 'view_foto.html', {'files': image_files})

    except Exception as e:
        return HttpResponse(f"Errore durante la lettura dei file: {str(e)}", status=500)






def all_events(request):
    if not request.session.get('privacy_global_accepted'):
        return redirect('privacy_policy_all')
    
    events = Event.objects.all()
    return render(request, 'all_events.html', {'events': events})

def privacy_policy_all(request):
    if request.method == 'POST':
        request.session['privacy_global_accepted'] = True
        return redirect('all_events')  # Sempre e solo qui

    return render(request, 'privacy_policy_all.html')







@login_required
def send_all_events_email(request):
    if request.method == "POST":
        recipients = request.POST.get("recipients")
        recipient_list = [email.strip() for email in recipients.split(',') if email.strip()]

        # ✅ Link diretto alla privacy policy (che poi reindirizza a tutti gli eventi)
        all_events_url = request.build_absolute_uri(reverse("privacy_policy_all"))

        # ✅ Icone social
        social_icons = {
            "logo": request.build_absolute_uri(settings.STATIC_URL + "icon/logo.png"),
            "whatsapp": request.build_absolute_uri(settings.STATIC_URL + "icon/whatsapp.png"),
            "instagram": request.build_absolute_uri(settings.STATIC_URL + "icon/instagram.png"),
            "facebook": request.build_absolute_uri(settings.STATIC_URL + "icon/facebook.png"),
            "email": request.build_absolute_uri(settings.STATIC_URL + "icon/email.png"),
        }

        # ✅ Rendering della mail con un solo pulsante
        html_content = render_to_string("all_events_email.html", {
            "all_events_url": all_events_url,
            "social_icons": social_icons,
        })

        text_content = strip_tags(html_content)

        try:
            email = EmailMultiAlternatives(
                subject="📸 Tutte le tue Gallerie Foto sono pronte!",
                body=text_content,
                from_email=settings.EMAIL_HOST_USER,
                to=recipient_list,
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            messages.success(request, "Email inviata con successo!")
        except Exception as e:
            messages.error(request, f"Errore durante l'invio dell'email: {e}")

        return redirect('dashboard')

    return redirect('dashboard')



def event_detail(request, access_code):
    """
    Mostra i dettagli di un evento specifico.
    """
    event = get_object_or_404(Event, access_code=access_code)
    return render(request, 'event_detail.html', {'event': event})






#@login_required
def add_to_cart(request):
    if request.method == "POST":
        event_id = request.POST.get("event_id")
        selected_photos = request.POST.getlist("selected_photos")

        # Recupera il carrello dalla sessione
        cart = request.session.get("cart", {})

        # Assicuriamoci che `cart` sia un dizionario
        if not isinstance(cart, dict):
            cart = {}

        if event_id not in cart:
            cart[event_id] = []

        for photo_id in selected_photos:
            photo = Photo.objects.filter(id=photo_id).first()
            if photo:
                cart[event_id].append({
                    "photo_id": photo.id,
                    "photo_url": photo.file_path.url,
                    "event_name": photo.event.name,
                    "price": float(photo.event.price_per_photo),  # ✅ Convertito in float
                })

        # Salviamo il carrello nella sessione
        request.session["cart"] = cart
        request.session.modified = True  # Forziamo Django a salvare la sessione

        messages.success(request, "Foto aggiunta al carrello!")
        #return redirect("cart_view")  # Reindirizza alla pagina del carrello
        return redirect('event_photos', event_id=event_id)





def remove_from_cart(request, photo_id):
    cart = request.session.get("cart", {})

    if not isinstance(cart, dict):
        cart = {}

    for event_id in list(cart.keys()):  # Usa list() per evitare modifiche durante l'iterazione
        cart[event_id] = [item for item in cart[event_id] if item["photo_id"] != int(photo_id)]
        if not cart[event_id]:  # Se l'evento è vuoto, rimuovilo dal carrello
            del cart[event_id]

    request.session["cart"] = cart
    request.session.modified = True

    messages.success(request, "Foto rimossa dal carrello.")
    return redirect("cart")
