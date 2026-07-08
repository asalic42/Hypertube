from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import Token
import requests

class MicroServiceClient:
    def __init__(self):
        ms_settings = getattr(settings, 'MS_CLIENT_SETTINGS', {})
        try :
            self.auth_url = ms_settings['AUTH_URL']
            self.service_name = ms_settings['SERVICE_NAME']
            self.service_secret = ms_settings['SERVICE_SECRET']
        except KeyError as e:
            raise ImproperlyConfigured(f'Missing settings for microservice_client: {e.args[0]}')
        self.timeout = ms_settings.get('MS_TIMEOUT', 10)

    def send_requests(self, urls:list, method:str, expected_status:list, headers={}, body={}, *args, **kwargs):
        headers.update({'Authorization': f'Bearer {self._getToken()}'})
        successed_requests=[]
        response_dict = {}
        for url in urls:
            response = self._send_request(url, method, body=body, headers=headers)
            if response.status_code not in expected_status:
                self._on_failure(successed_requests, method, headers=headers, body=body, *args, **kwargs)
            successed_requests.append(url)
            response_dict.update({url : response})
        return response_dict

    def _send_request(self, url:str, method:str, body={}, headers={}) -> int:
        req_methods = {
                'post':requests.post,
                'delete':requests.delete,
                'patch':requests.patch,
                }
        response = req_methods[method](url, json=body ,headers=headers)
        return response

    def _getToken(self):
        try :
            token = Token.objects.get(serviceName=self.service_name)
            UntypedToken(token.token)
            return token
        except (Token.DoesNotExist, TokenError):
            return self._getFreshToken()

    def _getFreshToken(self):
        body = {
                'serviceName': self.service_name,
                'password': self.service_secret,
                }
        response = requests.post(self.auth_url, json=body)
        if response.status_code != 200:
            raise InvalidCredentialsException('Auth refused to issue a token for the microservice')
        return response.json()['token']
    
    def _on_failure(self, urls:list, method:str, headers={}, body={}, *args, **kwargs):
        raise RequestsFailed('Communication between microservices failed')


class InvalidCredentialsException(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)

class RequestsFailed(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
