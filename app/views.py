from django.shortcuts import render, redirect
from django.core.mail import send_mail
from .forms import *
from .models import *
# from django.contrib import messages
import datetime

def home(request):
    return render(request, 'home.html', {})

def about(request):
    return render(request, 'about.html', {})

def pricing(request):
    return render(request, 'pricing.html', {})

def book_old(request):
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
            return render(request, 'book.html', {'form':form, 'error': True})
    else:
        form = BookingForm
        return render(request, 'book.html', {'form':form})

def book(request, date_adj):
    date = today + datetime.timedelta(days=int(date_adj))
    days = create_days(date, date.weekday(), 7)
    date = today + datetime.timedelta(days=7)
    days2 = create_days(date, 0, 7)
    if request.method == 'POST':
        form = BookingForm(request.POST or None)
        if form.is_valid:
            name = request.POST['name']
            response = check_name(name)
            if response != "Good":
                return render(request, 'book.html', {'days': days, 'days2': days2, 'form': form, 'message':response})
            mobile = request.POST['mobile']
            response = check_mobile(mobile)
            if response != "Good":
                return render(request, 'book.html', {'days': days, 'days2': days2, 'form': form, 'message':response})
            else:
                message = request.POST['message']
                date = request.POST['day_selected']
                date = datetime.datetime.strptime(date, '%d %b %Y')
                day_obj = Day.objects.filter(date=date).first()
                time = request.POST['time_selected']
                response = f"Thank you {name.split()[0]}! You have been booked in at {time} on {day_obj}. Please call me if you would like to change this time. "
                Booking(name=name, mobile=mobile, date=day_obj, time=time, message=message).save()
                return render(request, 'book.html', {'days': days, 'days2': days2, 'form': form, 'message': response})
    else:
        form = BookingForm
        return render(request, 'book.html', {'days': days,'days2': days2, 'form': form,})

def diary(request, date_adj):
    date = today + datetime.timedelta(days=int(date_adj))
    days = create_days(date, date.weekday(),14)
    return render(request, 'diary.html', {'days': days, })

def messages(request):
    messages = Message.objects.all().order_by('-time_stamp')
    return render(request, 'messages.html', {'messages': messages, })

def create_days(date, first_day, number):
    days = []
    for x in range(number):
        if x < first_day:
            days.append(None)
        else:
            day = Day.objects.filter(date=date).first()
            date += datetime.timedelta(days=1)
            days.append(day)
    return days


def check_mobile(mobile):
    mobile = mobile.replace(" ", "")
    if len(mobile) != 10: return f"Your mobile has {len(mobile)} numbers in it, and should have 10. Please enter a valid phone number."
    if not mobile.isdigit(): return f"Your mobile has characters that aren't numbers in it. Please enter a phone number with only numbers in it."
    if mobile[0:2] != "04": return f"Your mobile number starts with '{mobile[0:1]}' and should start with '04'. Please enter a phone number starting with '04'."
    return "Good"

def check_name(name):
    if len(name) == 0: return "Please enter your name."
    return "Good"

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
