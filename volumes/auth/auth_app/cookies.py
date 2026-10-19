from django.conf import settings


def set_refresh_cookie(response, refresh_token):
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        httponly=settings.REFRESH_COOKIE_HTTPONLY,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )
    # Same lifetime as the refresh cookie, readable by scripts, no secret inside.
    response.set_cookie(
        key=settings.SESSION_COOKIE_MARKER_NAME,
        value="1",
        max_age=max_age,
        httponly=False,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.SESSION_COOKIE_MARKER_PATH,
    )


def delete_refresh_cookie(response):
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=settings.SESSION_COOKIE_MARKER_NAME,
        path=settings.SESSION_COOKIE_MARKER_PATH,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )
