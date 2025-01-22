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

    return render(request, 'event_photos/dashboard.html', {
        'events': events,
        'form': form,
        'query': query,
    })



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

    return render(request, 'event_photos/event_photos.html', {
        'event': event,
        'photos': photos,
    })

@login_required
def send_access_code(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        recipients = request.POST.get('recipients')
        recipient_list = [email.strip() for email in recipients.split(',')]

        access_url = request.build_absolute_uri(f"/acquista-foto/?access_code={event.access_code}")

        subject = f"Codice di Accesso per l'Evento: {event.name}"
        message = (
            f"Ciao,\n\n"
            f"Ti è stato condiviso il codice di accesso per l'evento \"{event.name}\":\n\n"
            f"Codice: {event.access_code}\n"
            f"Prezzo per Foto: {event.price_per_photo} €\n\n"
            f"Puoi acquistare le foto qui: {access_url}\n\n"
            f"Grazie!"
        )
        
        try:
           send_mail(subject, message, settings.EMAIL_HOST_USER, recipient_list)
           messages.success(request, "Email inviata con successo!")
        except smtplib.SMTPException as e:
           messages.error(request, f"Errore SMTP: {e}")
        except ValueError:
           messages.error(request, "Indirizzo email non valido.")
        except Exception as e:
            messages.error(request, f"Errore durante l'invio dell'email: {e}")

        
        return redirect('dashboard')

    return render(request, 'event_photos/send_email.html', {'event': event})


@login_required
def purchase_photos(request):
    access_code = request.GET.get('access_code', '').strip()
    event = None
    photos = []

    if access_code:
        try:
            event = Event.objects.get(access_code=access_code)
            photos = event.photos.all()
        except Event.DoesNotExist:
            messages.error(request, "Codice di accesso non valido.")
            return render(request, 'event_photos/purchase_photos.html', {
                'event': None,
                'photos': [],
            })

    return render(request, 'event_photos/purchase_photos.html', {
        'event': event,
        'photos': photos,
    })


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

    return render(request, 'event_photos/create_event.html', {'form': form})


from django.http import HttpResponse

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

    return render(request, 'event_photos/upload_photos.html', {
        'event': event,
        'form': form,
    })



@login_required
def upload_zip(request, event_id):
    print("La funzione upload_zip è stata chiamata.")  # Debug
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST' and request.FILES.get('zip_file'):
        zip_file = request.FILES['zip_file']
        print(f"Nome file ZIP ricevuto: {zip_file.name}")  # Debug

        if not zip_file.name.endswith('.zip'):
            messages.error(request, "Carica un file ZIP valido.")
            return redirect('event_photos', event_id=event.id)

        try:
            event_folder = os.path.join(settings.MEDIA_ROOT, f'event_photos/event_{event.id}')
            os.makedirs(event_folder, exist_ok=True)
            print(f"Cartella creata: {event_folder}")  # Debug

            with zipfile.ZipFile(zip_file, 'r') as zf:
                for file_name in zf.namelist():
                    if file_name.lower().endswith(('png', 'jpg', 'jpeg')):
                        extracted_file_path = os.path.join(event_folder, os.path.basename(file_name))
                        with open(extracted_file_path, 'wb') as f:
                            f.write(zf.read(file_name))
                        print(f"Foto salvata: {extracted_file_path}")  # Debug

                        relative_path = os.path.relpath(extracted_file_path, settings.MEDIA_ROOT)
                        Photo.objects.create(event=event, file_path=relative_path, original_name=os.path.basename(file_name))

            messages.success(request, "Foto caricate con successo dal file ZIP!")
        except Exception as e:
            messages.error(request, f"Errore durante il caricamento del file ZIP: {e}")
            print(f"Errore durante il caricamento: {e}")  # Debug

        return redirect('event_photos', event_id=event.id)

    return render(request, 'event_photos/upload_zip.html', {'event': event})







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

    return render(request, 'event_photos/access_event.html')


@login_required
def cart(request):
    cart_items = request.session.get('cart_items', [])

    if request.method == 'POST':
        photo_id = request.POST.get('photo_id')
        if photo_id and photo_id not in cart_items:
            cart_items.append(photo_id)
            request.session['cart_items'] = cart_items
            messages.success(request, "Foto aggiunta al carrello.")
        else:
            messages.warning(request, "Questa foto è già nel carrello.")

    photos = Photo.objects.filter(id__in=cart_items)

    return render(request, 'event_photos/cart.html', {
        'photos': photos,
        'cart_count': len(cart_items)
    })

@login_required
def delete_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    photo.delete()
    messages.success(request, f"La foto '{photo.original_name}' è stata eliminata con successo.")
    return redirect('dashboard')
