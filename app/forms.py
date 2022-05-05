from django import forms
from .models import *

WIDGETS = {
    'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder':"Your Name"}),
    'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder':"Your mobile"}),
    'message': forms.TextInput(attrs={'class': 'form-control', 'placeholder':"Your message"}),
    'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder':"Your Email"}),
}


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['name', 'mobile', 'email', 'message',]
        widgets = WIDGETS

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['name', 'mobile', 'message']
        widgets = WIDGETS

    def clean_mobile(self):
        print("checking")
        mobile = self.cleaned_data.get("mobile")
        print(mobile)
        if not mobile.isdigit():
            raise forms.ValidationError("Please enter a valid mobile number")
        return mobile

    def clean_name(self):
        print("checking")
        name = self.cleaned_data.get("name")
        print(name)
        return name