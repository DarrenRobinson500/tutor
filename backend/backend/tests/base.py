from django.test import TestCase, override_settings
from rest_framework.test import APITestCase as DRFAPITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .factories import *


@override_settings(DEBUG=False)
class BaseAPITestCase(DRFAPITestCase):
    def auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def unauth(self):
        self.client.credentials()
