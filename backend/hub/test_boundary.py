import ipaddress
from datetime import timedelta

from django.conf import settings
from django.db import DatabaseError, transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import AuthRateBucket


def networks(value):
    try:
        parsed = [ipaddress.ip_network(part.strip(), strict=False) for part in value.split(',') if part.strip()]
        return [] if any(network.prefixlen == 0 for network in parsed) else parsed
    except ValueError:
        return []


def in_networks(address, allowed):
    try:
        return any(ipaddress.ip_address(address) in network for network in allowed)
    except ValueError:
        return False


class RestrictedTestBoundaryMiddleware:
    """Fail closed unless one configured local proxy supplies one sanitized client IP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.RESTRICTED_TEST_MODE:
            return self.get_response(request)

        trusted = networks(settings.TEST_TRUSTED_PROXY_NETWORKS)
        peer = request.META.get('REMOTE_ADDR', '')
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        protocol = request.META.get('HTTP_X_FORWARDED_PROTO', '')
        # Nginx replaces these headers. Any alternate client-supplied form is discarded.
        for name in ('HTTP_FORWARDED', 'HTTP_X_FORWARDED_HOST', 'HTTP_X_REAL_IP',
                     'HTTP_X_FORWARDED_PORT', 'HTTP_X_FORWARDED_SERVER'):
            request.META.pop(name, None)
        if not trusted or not in_networks(peer, trusted):
            return HttpResponse(status=403)
        if ',' in forwarded or protocol not in ('http', 'https'):
            return HttpResponse(status=400)
        try:
            client_ip = str(ipaddress.ip_address(forwarded))
        except ValueError:
            return HttpResponse(status=400)
        request.META['REMOTE_ADDR'] = client_ip
        request.META['HTTP_X_FORWARDED_FOR'] = client_ip
        request.META['HTTP_X_FORWARDED_PROTO'] = protocol

        if request.path == '/api/admin' or request.path.startswith('/api/admin/'):
            allowed = networks(settings.TEST_ADMIN_NETWORKS)
            if not allowed or not in_networks(client_ip, allowed):
                return HttpResponse(status=404)

        if request.method == 'POST':
            route = self._auth_route(request.path)
            if route:
                if settings.TEST_AUTH_LIMIT_PER_MINUTE < 1:
                    return HttpResponse(status=503)
                try:
                    if not self._allowed(route, client_ip):
                        return HttpResponse(status=429)
                except DatabaseError:
                    return HttpResponse(status=503)
        return self.get_response(request)

    @staticmethod
    def _auth_route(path):
        if path == '/api/auth/login/':
            return 'login'
        if path in ('/api/auth/password-reset/', '/api/auth/password-reset-confirm/'):
            return 'recovery'
        if path == '/api/admin/login/':
            return 'admin'
        return None

    @staticmethod
    def _allowed(route, client_ip):
        key = salted_hmac('f09-test-throttle', route + ':' + client_ip).hexdigest()
        now = timezone.now()
        with transaction.atomic():
            AuthRateBucket.objects.get_or_create(key=key, defaults={'window_start': now})
            bucket = AuthRateBucket.objects.select_for_update().get(key=key)
            if now - bucket.window_start >= timedelta(minutes=1):
                bucket.window_start = now
                bucket.count = 0
            if bucket.count >= settings.TEST_AUTH_LIMIT_PER_MINUTE:
                return False
            bucket.count += 1
            bucket.save(update_fields=['window_start', 'count'])
        return True
