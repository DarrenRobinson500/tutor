from django.db import models
import datetime

class Message(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    mobile = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(max_length=200, null=True, blank=True)
    message = models.TextField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.name


DAYS = [("Monday","Monday"),("Tuesday","Tuesday"),("Wednesday","Wednesday"),("Thursday","Thursday"),("Friday","Friday"),("Saturday","Saturday"),("Sunday","Sunday"),]
TIMES = [("3:30pm","3:30pm"),("4:30pm","4:30pm"),("5:30pm","5:30pm"),("Other", "Other"),]

class Booking(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    mobile = models.CharField(max_length=200, null=True, blank=True)
    day = models.CharField(max_length=200, null=True, blank=True, choices=DAYS)
    time = models.CharField(max_length=200, null=True, blank=True, choices=TIMES)
    date = models.ForeignKey("Day", null=True, blank=True, on_delete=models.SET_NULL)
    confirmed = models.TextField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.name

class Day(models.Model):
    date = models.DateField(null=True, blank=True)

    def __str__(self):
        return str(self.date)

    def weekday(self):
        self.date.weekday().strftime('%A')

    def times_tutoring(self):
        print(self.date.strftime('%A'))
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
                times_available.remove(x)
            except:
                pass
        return times_available


