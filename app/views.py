from django.shortcuts import render, redirect
from django.core.mail import send_mail
from .forms import *
from .models import *
from django.contrib import messages


def home(request):
    return render(request, 'home.html', {})

def about(request):
    return render(request, 'about.html', {})

def pricing(request):
    return render(request, 'pricing.html', {})

def book(request):
    if request.method == 'POST':
        form = BookingForm(request.POST or None)
        if form.is_valid():
            new = form.save()
            send_mail(
                "Booking",  # subject
                "You have a new booking request",  # message
                'darrenjamesspare@gmail.com',  # from email
                ['darrenandamanda.robinson@gmail.com', ],  # to
                fail_silently=False
            )
            form = BookingForm
            return render(request, 'book.html', {'form':form, 'name':new.name,})
        else:
            print(form.errors)
            return render(request, 'book.html', {'form':form, 'error': True})
    else:
        form = BookingForm
        return render(request, 'book.html', {'form':form})

def diary(request, date_adj):
    date = datetime.date.today() + datetime.timedelta(days=int(date_adj))
    days = []
    for x in range(7):
        day = Day.objects.filter(date=date).first()
        date += datetime.timedelta(days=1)
        days.append(day)
    # days.sort()
    print(days)
    for x in days:
        print(x.times_tutoring())
        print(x.times_available())
    return render(request, 'diary.html', {'days': days})

def create_dates(request):
    date_counter = datetime.date.today()
    for x in range(90):
        existing = Day.objects.filter(date=date_counter).first()
        if not existing:
            Day(date=date_counter).save()
        date_counter += datetime.timedelta(days=1)
    return redirect("home")

def contact(request):
    if request.method == 'POST':
        form = MessageForm(request.POST or None)
        if form.is_valid():
            new = form.save()
            send_mail(
                "Enquiry",  # subject
                new.message,  # message
                new.email,  # from email
                ['darrenandamanda.robinson@gmail.com', ],  # to
                fail_silently=False
            )
            form = MessageForm
            message_name = new.name
            return render(request, 'contact.html', {'form':form, 'message_name':message_name,})
        else:
            messages.success(request,('Seems like an error has occurred.'))
            return render(request, 'contact.html', {'form':form})
    else:
        form = MessageForm
        return render(request, 'contact.html', {'form':form})
