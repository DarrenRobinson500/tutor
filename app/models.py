from django.db import models

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
    confirmed = models.TextField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.name