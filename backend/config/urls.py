from django.urls import path, include
from django.contrib import admin
from django.views.generic import RedirectView
from backend.views import tutor_payments_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("backend.urls")),
    path('tutor/payments/', tutor_payments_page, name='tutor_payments'),
    path('', RedirectView.as_view(url='/index.html', permanent=False)),
]
