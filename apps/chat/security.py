"""
Sammanhallet sakerhetslager for chatten (Milestone 8).

Allt sakerhetskanslit pa ett stalle sa det gar att granska:
  * client_ip()            - ratt IP bakom nginx (X-Forwarded-For)
  * rate_limit()           - sliding-window per nyckel (flod/brute force)
  * verify_admin_password()- konstant-tids jamforelse, stod for losenordshash
  * csrf_token()/validate  - CSRF-skydd for admin-formular
  * apply_security_headers - frame/referrer/nosniff/CSP/no-store
  * log_suspicious()       - logga honeypot, rate-limit, failade logins

Designval: rate limit och login-throttle halls i minnet (per gunicorn-worker).
Enkelt och utan extra beroenden; med 2 workers blir effektiv grans ~2x men
det racker val for MVP. Kan flyttas till Redis nar trafiken vaxer.
"""
import os
import time
import hmac
import secrets
import threading
import logging

from flask import request, session, current_app
from werkzeug.security import check_password_hash

log = logging.getLogger('chat.security')

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'monky-dev-2026')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')  # valfri, vinner om satt


# ---------- IP ----------

def client_ip():
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()[:64]
    return (request.remote_addr or '')[:64]


# ---------- Rate limiting (sliding window, in-memory) ----------

_hits = {}
_lock = threading.Lock()
_last_gc = [0.0]


def rate_limit(key, limit, per_seconds):
    """Returnerar True om anropet far passera, False om gransen ar nadd."""
    now = time.time()
    with _lock:
        # enkel periodisk stadning sa dicten inte vaxer obegransat
        if now - _last_gc[0] > 300:
            for k in [k for k, q in _hits.items() if not q or q[-1] < now - 3600]:
                _hits.pop(k, None)
            _last_gc[0] = now

        q = _hits.setdefault(key, [])
        cutoff = now - per_seconds
        while q and q[0] < cutoff:
            q.pop(0)
        if len(q) >= limit:
            return False
        q.append(now)
        return True


# ---------- Admin-losenord ----------

def verify_admin_password(pw):
    """Konstant-tids verifiering. Foredrar hash om ADMIN_PASSWORD_HASH satt."""
    if not pw:
        return False
    if ADMIN_PASSWORD_HASH:
        try:
            return check_password_hash(ADMIN_PASSWORD_HASH, pw)
        except Exception:
            return False
    return hmac.compare_digest(str(pw), str(ADMIN_PASSWORD))


# ---------- CSRF ----------

def csrf_token():
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['csrf_token'] = token
    return token


def validate_csrf():
    sent = request.form.get('csrf_token', '')
    real = session.get('csrf_token', '')
    return bool(real) and hmac.compare_digest(str(sent), str(real))


# ---------- Sakerhetsheaders ----------

_CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "script-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def apply_security_headers(resp):
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['Content-Security-Policy'] = _CSP
    resp.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    # Chatt-svar och admin ska aldrig cachas (kan innehalla privata meddelanden)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


# ---------- Logg ----------

def log_suspicious(event, detail=''):
    try:
        current_app.logger.warning(
            'CHAT-SECURITY %s ip=%s ua=%r path=%s %s',
            event, client_ip(),
            request.headers.get('User-Agent', '')[:120],
            request.path, detail)
    except Exception:
        pass
