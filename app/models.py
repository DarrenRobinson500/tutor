from django.db import models

class Message(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    message = models.TextField(max_length=200)

    def __str__(self):
        return self.name