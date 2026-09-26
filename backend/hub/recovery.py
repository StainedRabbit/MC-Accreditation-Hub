from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


SMTP_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


def recovery_configured():
    """Require an authenticated, encrypted SMTP path and a public HTTPS link."""
    if not settings.PASSWORD_RESET_ENABLED or settings.EMAIL_BACKEND != SMTP_BACKEND:
        return False
    host = settings.EMAIL_HOST.strip().lower()
    sender = settings.DEFAULT_FROM_EMAIL.strip()
    if not host or host in ('localhost', '127.0.0.1') or host.endswith(('.invalid', '.example', '.example.edu')):
        return False
    if (not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD or
            settings.EMAIL_HOST_USER in ('replace-me', '...') or settings.EMAIL_HOST_PASSWORD in ('replace-me', '...')):
        return False
    if settings.EMAIL_USE_TLS == settings.EMAIL_USE_SSL or not 1 <= settings.EMAIL_PORT <= 65535 or settings.EMAIL_TIMEOUT <= 0:
        return False
    try:
        validate_email(sender)
        url = urlsplit(settings.PASSWORD_RESET_FRONTEND_URL)
        return bool(url.scheme == 'https' and url.hostname and not url.username and not url.password and
                    not url.query and not url.fragment and url.hostname not in ('localhost', '127.0.0.1') and
                    not url.hostname.endswith(('.invalid', '.example', '.example.edu')))
    except (ValidationError, ValueError):
        return False
