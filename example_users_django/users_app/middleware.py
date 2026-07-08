from django.utils.timezone import now
from .models import PublicUser
import os

class SetRequestHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.META['HTTP_HOST'] = os.getenv('HOSTNAME') + ":8080"
        request.META['wsgi.url_scheme'] = 'http'
        return self.get_response(request)
