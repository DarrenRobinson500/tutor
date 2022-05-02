from django.shortcuts import render, redirect
from django.core.mail import send_mail
from .forms import *
from .models import *
from django.contrib import messages


def home(request):
    return render(request, 'home.html', {})

def contact_old(request):
    if request.method == "POST":
        message_name = request.POST['message-name']
        message_email = request.POST['message-email']
        message = request.POST['message']

        send_mail(
            message_name, # subject
            message, # message
            message_email, # from email
            ['darrenandamanda.robinson@gmail.com', ], # to
            fail_silently=False
        )

        return render(request, 'contact.html', {'message_name': message_name})
    else:
        return render(request, 'contact.html', {})

def contact(request):
    if request.method == 'POST':
        form = MessageForm(request.POST or None)
        if form.is_valid():
            form.save()
            messages.success(request, ("Your message has been sent."))
            return redirect("contact")
        else:
            messages.success(request,('Seems like an error has occurred.'))
            return render(request, 'contact.html', {'form':form})
    else:
        form = MessageForm
        return render(request, 'contact.html', {'form':form})
