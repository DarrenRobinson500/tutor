from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('about', about, name='about'),
    path('pricing', pricing, name='pricing'),
    path('contact.html', contact, name='contact'),
    path('messages.html', messages, name='messages'),
    path('book/<date_adj>', book, name='book'),
    path('diary/<date_adj>', diary, name='diary'),
    path('create_dates', create_dates, name='create_dates'),
]
