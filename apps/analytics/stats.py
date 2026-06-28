"""
Aggregeringar for admin-vyerna. Raknar fram live-besokare, sidflode och
sammanstallningar fran VisitorSession/VisitorEvent. Inget PII lamnar systemet.
"""
from datetime import datetime, timedelta

from sqlalchemy import func

from apps import db
from apps.analytics.models import VisitorSession, VisitorEvent
from apps.analytics.scoring import status_label


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
    label, cls = status_label(s.lead_score)
    return {
        'id': anon_id(s),
        'device': s.device or '–',
        'page': s.current_page or '–',
        'last': last_txt,
        'time': fmt_duration((now - since).total_seconds()),
        'flow': s.page_flow,
        'score': s.lead_score,
        'status': label,
        'status_cls': cls,
    }


def count_today():
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return VisitorSession.query.filter(VisitorSession.first_seen >= start).count()


def hot_leads(threshold=50):
    return VisitorSession.query.filter(VisitorSession.lead_score >= threshold).count()


def form_submits(days=30):
    since = datetime.utcnow() - timedelta(days=days)
    return VisitorEvent.query.filter(VisitorEvent.event_type == 'form_submit',
                                     VisitorEvent.created_at >= since).count()


def top_cta(limit=5):
    rows = (db.session.query(VisitorEvent.element_text, func.count().label('n'))
            .filter(VisitorEvent.event_type == 'click',
                    VisitorEvent.element_text.isnot(None),
                    VisitorEvent.element_text != '')
            .group_by(VisitorEvent.element_text)
            .order_by(func.count().desc()).limit(limit).all())
    top = rows[0][1] if rows else 1
    return [{'text': t, 'clicks': n, 'pct': round(n / top * 100)} for t, n in rows]


def top_pages(limit=6):
    rows = (db.session.query(VisitorEvent.page_url, func.count().label('n'))
            .filter(VisitorEvent.event_type == 'pageview', VisitorEvent.page_url.isnot(None))
            .group_by(VisitorEvent.page_url)
            .order_by(func.count().desc()).limit(limit).all())
    return {'labels': [p for p, _ in rows], 'data': [n for _, n in rows]}


def _prettify(path):
    slug = (path or '').rstrip('/').split('/')[-1]
    if not slug:
        return path or '–'
    words = slug.replace('-', ' ').strip()
    return words[:1].upper() + words[1:]


def top_blog_posts(limit=10):
    """Mest lasta blogginlagg (sidvisningar av /blogg/<slug>)."""
    rows = (db.session.query(VisitorEvent.page_url, func.count().label('n'))
            .filter(VisitorEvent.event_type == 'pageview',
                    VisitorEvent.page_url.like('/blogg/%'))
            .group_by(VisitorEvent.page_url)
            .order_by(func.count().desc()).limit(limit).all())
    top = rows[0][1] if rows else 1
    return [{'url': p, 'title': _prettify(p), 'views': n, 'pct': round(n / top * 100)}
            for p, n in rows]


def top_visited_pages(limit=10):
    rows = (db.session.query(VisitorEvent.page_url, func.count().label('n'))
            .filter(VisitorEvent.event_type == 'pageview', VisitorEvent.page_url.isnot(None))
            .group_by(VisitorEvent.page_url)
            .order_by(func.count().desc()).limit(limit).all())
    top = rows[0][1] if rows else 1
    return [{'url': p, 'views': n, 'pct': round(n / top * 100)} for p, n in rows]


def device_breakdown():
    rows = (db.session.query(VisitorSession.device, func.count())
            .group_by(VisitorSession.device).all())
    total = sum(n for _, n in rows) or 1
    out = {}
    for dev, n in rows:
        out[(dev or 'okänd').capitalize()] = round(n / total * 100)
    return out or {'Ingen data': 100}


def daily_series(days=14):
    start = (datetime.utcnow() - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0)
    labels, visits, clicks, leads = [], [], [], []
    for i in range(days):
        day = start + timedelta(days=i)
        nxt = day + timedelta(days=1)
        labels.append(f"{day.day}/{day.month}")

        def n(etype):
            return VisitorEvent.query.filter(
                VisitorEvent.event_type == etype,
                VisitorEvent.created_at >= day,
                VisitorEvent.created_at < nxt).count()
        visits.append(n('pageview'))
        clicks.append(n('click'))
        leads.append(n('form_submit'))
    return {'labels': labels, 'visits': visits, 'clicks': clicks, 'leads': leads}


def lead_list(limit=60):
    """Besokare sorterade efter lead score (hetast forst) for Leads-vyn."""
    rows = (VisitorSession.query
            .filter(VisitorSession.lead_score > 0)
            .order_by(VisitorSession.lead_score.desc(),
                      VisitorSession.last_seen.desc())
            .limit(limit).all())
    return [session_view(s) for s in rows]


def recent_sessions(limit=8):
    out = []
    for s in (VisitorSession.query.order_by(VisitorSession.last_seen.desc())
              .limit(limit).all()):
        out.append({'id': anon_id(s), 'device': s.device or '–',
                    'page': s.current_page or '–', 'score': s.lead_score})
    return out
