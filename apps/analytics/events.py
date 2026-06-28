"""
Event-API for analytics. Tar emot pageview/click/scroll m.m. fran ett litet
script pa sajten och sparar dem anonymt.

Sakerhet/integritet:
  * Inget PII, ingen ra IP lagras. Besokaren identifieras av ett token som
    klienten sjalv haller i localStorage.
  * Rate limit per IP (ateranvander chattens security-modul).
  * Klienten skickar bara nar cookie-samtycke finns; vi noterar samtycket.
"""
from datetime import datetime

from flask import request, jsonify

from apps import db
from apps.analytics import blueprint
from apps.analytics.models import VisitorSession, VisitorEvent, EVENT_TYPES, _new_token
from apps.chat.security import client_ip, rate_limit


def _clean(value, n):
    if not value:
        return None
    return str(value).strip()[:n] or None


def _detect_device(ua):
    ua = (ua or '').lower()
    if 'ipad' in ua or 'tablet' in ua:
        return 'surfplatta'
    if 'mobi' in ua or 'android' in ua or 'iphone' in ua:
        return 'mobil'
    return 'dator'


def _detect_browser(ua):
    ua = ua or ''
    for name in ('Edg', 'OPR', 'Chrome', 'Firefox', 'Safari'):
        if name in ua:
            return {'Edg': 'Edge', 'OPR': 'Opera'}.get(name, name)
    return None


@blueprint.route('/api/analytics/event', methods=['POST'])
def track_event():
    ip = client_ip()
    # Generost (pageview + klick + scroll kan bli manga), men inte obegransat.
    if not rate_limit(f'analytics:{ip}', 240, 60):
        return jsonify(ok=False), 429

    data = request.get_json(silent=True) or {}
    etype = (data.get('type') or '').strip()[:40]
    if etype not in EVENT_TYPES:
        return jsonify(ok=False, error='okant event'), 400

    token = (data.get('token') or '').strip()
    sess = VisitorSession.query.filter_by(session_token=token).first() if token else None
    if sess is None:
        ua = request.headers.get('User-Agent', '')
        sess = VisitorSession(
            session_token=_new_token(),
            device=_detect_device(ua),
            browser=_detect_browser(ua),
            source=_clean(request.headers.get('Referer'), 255),
        )
        db.session.add(sess)
        db.session.flush()

    sess.last_seen = datetime.utcnow()
    if data.get('consent'):
        sess.consent_analytics = True

    db.session.add(VisitorEvent(
        session_id=sess.id,
        event_type=etype,
        page_url=_clean(data.get('url'), 255),
        element_text=_clean(data.get('text'), 200),
        value=_clean(data.get('value'), 60),
    ))
    db.session.commit()

    return jsonify(ok=True, token=sess.session_token)
