from django.db import models
import datetime

today = datetime.date.today()

class Message(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    mobile = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(max_length=200, null=True, blank=True)
    message = models.TextField(max_length=200, null=True, blank=True)
    time_stamp = models.DateField(auto_now_add=True, null=True)

    def __str__(self):
        return self.name


DAYS = [("Monday","Monday"),("Tuesday","Tuesday"),("Wednesday","Wednesday"),("Thursday","Thursday"),("Friday","Friday"),("Saturday","Saturday"),("Sunday","Sunday"),]
TIMES = [("3:30pm","3:30pm"),("4:30pm","4:30pm"),("5:30pm","5:30pm"),("Other", "Other"),]

class Booking(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    mobile = models.CharField(max_length=200, null=True, blank=True)
    time = models.CharField(max_length=200, null=True, blank=True)
    date = models.ForeignKey("Day", null=True, blank=True, on_delete=models.SET_NULL)
    message = models.TextField(max_length=200, null=True, blank=True)
    confirmed = models.BooleanField(default=False)
    time_stamp = models.DateField(auto_now_add=True, null=True)


    def __str__(self):
        return self.name

class Day(models.Model):
    date = models.DateField(null=True, blank=True)
    time_stamp = models.DateField(auto_now_add=True, null=True)

    def __str__(self):
        result = self.date.strftime("%d %b")
        return result

    def format(self):
        result = self.date.strftime("%d %b %Y")
        return result

    def day_of_week(self):
        result = self.date.strftime("%A")
        return result

    def weekday(self):
        self.date.weekday().strftime('%A')

    def times_tutoring(self):
        if self.date.weekday() in [0,1,2,3,4]:
                # ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",]:
            return ["3:30pm", "4:30pm", "5:30pm", ]
        else:
            return ["9:00am", "10:00am", "11:00am", ]

    def times_available(self):
        times_available = self.times_tutoring()
        sessions_on_day = Booking.objects.filter(date=self)
        for x in sessions_on_day:
            try:
                times_available.remove(x.time)
            except:
                pass
        return times_available

    def bookings(self):
        return Booking.objects.filter(date=self).order_by('time')


