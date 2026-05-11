import os
from django.urls import path, include, re_path
from django.contrib import admin
from django.http import JsonResponse, FileResponse, Http404
from django.conf import settings
from backend.views import tutor_payments_page


def health(request):
    return JsonResponse({'status': 'ok'})


def serve_spa(request, path=''):
    index = os.path.join(settings.WHITENOISE_ROOT, 'index.html')
    if not os.path.exists(index):
        raise Http404
    return FileResponse(open(index, 'rb'), content_type='text/html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health),
    path('api/', include('backend.urls')),
    path('tutor/payments/', tutor_payments_page, name='tutor_payments'),
    re_path(r'^(?!api/|admin/|health/|static/).*$', serve_spa),
]
