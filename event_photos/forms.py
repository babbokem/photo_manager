from django import forms
from .models import Event, Photo






class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'description', 'zip_file', 'price_per_photo']

class PhotoUploadForm(forms.Form):
    zip_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'accept': '.zip'}),
        required=True,
        label="Carica un file ZIP"
    )



class ZipUploadForm(forms.Form):
    zip_file = forms.FileField(label="Carica un file ZIP contenente le foto")

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'description', 'zip_file', 'price_per_photo']






