"""
Aggregeringar for admin-vyerna. Raknar fram live-besokare, sidflode och
sammanstallningar fran VisitorSession/VisitorEvent. Inget PII lamnar systemet.
"""
from datetime import datetime, timedelta

from apps.analytics.models import VisitorSession, VisitorEvent


def fmt_duration(secs):
    secs = max(0, int(secs))
    m, s = divmod(secs, 60)
    if m:
        return f"{m} min {s} sek"
    return f"{s} sek"


def anon_id(session):
    return '#' + (session.session_token[:3].upper())


def live_sessions(minutes=5):
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    return (VisitorSession.query
            .filter(VisitorSession.last_seen >= cutoff)
            .order_by(VisitorSession.last_seen.desc())
            .all())


def session_view(s):
    """Plockar fram det live-vyn behover ur en session (svensk text, ingen PII)."""
    now = datetime.utcnow()
    last_pv = None
    for e in reversed(s.events):
        if e.event_type == 'pageview':
            last_pv = e
            break
    since = last_pv.created_at if last_pv else s.last_seen
    la = s.last_action
    last_txt = '–'
    if la:
        if la.event_type == 'click':
            last_txt = f'Klickade "{la.element_text or ""}"'
        elif la.event_type == 'scroll':
            last_txt = f'Scrollade {la.value or ""}%'
        elif la.event_type == 'pageview':
            last_txt = f'Öppnade {la.page_url or ""}'
        elif la.event_type == 'form_submit':
            last_txt = 'Skickade formulär'
        elif la.event_type == 'form_start':
            last_txt = 'Fyller i formulär'
        elif la.event_type == 'chat_open':
            last_txt = 'Öppnade chatten'
    return {
        'id': anon_id(s),
        'device': s.device or '–',
        'page': s.current_page or '–',
        'last': last_txt,
        'time': fmt_duration((now - since).total_seconds()),
        'flow': s.page_flow,
        'score': s.lead_score,
    }


def count_today():
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return VisitorSession.query.filter(VisitorSession.first_seen >= start).count()
