from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.negotiation import BaseContentNegotiation

from movies_app.services import streaming


class StreamUser:
    """The holder of a valid stream token."""

    is_authenticated = True
    is_anonymous = False
    username = ""

    def __init__(self, user_id):
        self.id = user_id
        self.pk = user_id


class StreamTokenAuthentication(BaseAuthentication):
    """
    Authenticates media requests with the signed `token` query parameter
    issued by the download endpoint. Only meant for the views serving
    <video> and <track>, which cannot send an Authorization header.
    """

    def authenticate(self, request):
        token = request.query_params.get("token")
        movie_id = request.parser_context["kwargs"].get("movie_id")
        if not token or movie_id is None:
            return None
        user_id = streaming.read_token(token, movie_id)
        # An invalid token falls through to the next authenticator, then to a 401.
        return (StreamUser(user_id), None) if user_id else None

    def authenticate_header(self, request):
        # DRF answers 401 rather than 403 only when the first authenticator names a scheme.
        return 'Bearer realm="api"'


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    """Media players send Accept headers no API renderer matches: never answer 406 to them."""

    def select_parser(self, request, parsers):
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        return (renderers[0], renderers[0].media_type)


class StreamTokenScheme(OpenApiAuthenticationExtension):
    target_class = StreamTokenAuthentication
    name = "streamToken"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "query", "name": "token"}
