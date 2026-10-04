"""Safe, append-only audit writes and request-local correlation."""
import uuid
from contextvars import ContextVar
from contextlib import contextmanager

from .models import AuditEvent


_context = ContextVar('hub_audit_request', default=None)
_suppress_model_events = ContextVar('hub_suppress_model_events', default=False)


@contextmanager
def suppress_model_audit():
    marker = _suppress_model_events.set(True)
    try:
        yield
    finally:
        _suppress_model_events.reset(marker)


def model_audit_suppressed():
    return _suppress_model_events.get()
_secret_keys = ('password', 'token', 'secret', 'session', 'authorization', 'cookie', 'file_content', 'reset_url')


def safe_detail(value):
    if isinstance(value, dict):
        return {str(key): '[redacted]' if any(secret in str(key).lower() for secret in _secret_keys)
                else safe_detail(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_detail(item) for item in value]
    return value


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        marker = _context.set((uuid.uuid4(), request))
        try:
            return self.get_response(request)
        finally:
            _context.reset(marker)


def write_audit(actor, area, action, record, **detail):
    context = _context.get()
    request_id = context[0] if context else uuid.uuid4()
    if actor is None and context:
        candidate = context[1].user
        actor = candidate if candidate.is_authenticated else None
    # Callers supply only explicitly selected fields; never copy request bodies,
    # headers, passwords, reset links, or model dictionaries into detail.
    return AuditEvent.objects.create(actor=actor, area=area, action=action,
                                     record=str(record)[:200], detail=safe_detail(detail), request_id=request_id)


def current_actor():
    context = _context.get()
    if context:
        user = context[1].user
        if user.is_authenticated:
            return user
    return None
