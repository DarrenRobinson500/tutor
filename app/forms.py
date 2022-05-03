from django import forms
from .models import *

WIDGETS = {
    'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder':"Your Name"}),
    'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder':"Your mobile"}),
    'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder':"Your Email"}),
    'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder':"Your Message"}),
    'day': forms.Select(attrs={'class': 'form-control', 'placeholder': "Your Preferred Day"}),
    'time': forms.Select(attrs={'class': 'form-control', 'placeholder': "Your Preferred Time"}),
}


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['name', 'mobile', 'email', 'message',]
        widgets = WIDGETS

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['name', 'mobile', 'day', 'time',]
        widgets = WIDGETS