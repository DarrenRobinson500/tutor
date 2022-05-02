from django import forms
from .models import *

WIDGETS = {
    'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder':"Your Name"}),
    'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder':"Your Email"}),
    'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder':"Your Message"}),
}


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['name', 'email', 'message']
        widgets = WIDGETS