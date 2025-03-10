from event_photos.models import Photo
from decimal import Decimal

def cart_context(request):
    """
    Rende disponibile il carrello in tutti i template.
    """
    cart_data = request.session.get("cart", {})

    if not isinstance(cart_data, dict):  
        cart_data = {}  # Assicura che sia un dizionario

    photos = []
    total_amount = Decimal("0.00")

    for event_id, items in cart_data.items():
        for item in items:
            photo_id = item.get("photo_id")
            event_name = item.get("event_name", "Evento Sconosciuto")
            price = Decimal(item.get("price", 0))

            photo = Photo.objects.filter(id=photo_id).first()
            if photo:
                photos.append({
                    "photo_id": photo.id,
                    "photo_url": photo.file_path.url,
                    "event_name": event_name,
                    "price": price,
                })
                total_amount += price

    return {
        "cart_photos": photos,
        "cart_count": len(photos),
        "cart_total": total_amount,
    }
