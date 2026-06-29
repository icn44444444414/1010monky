"""
Routes for analytics-dashboarden.

Bakom admin-login (samma session som chatt-adminen). All data ar RIKTIG och
raknas fram i stats.py ur VisitorSession/VisitorEvent/Lead (ingen demodata).
"""
from flask import render_template, jsonify, redirect, url_for

from apps.analytics import blueprint
from apps.analytics import models  # noqa: F401  (sakerstaller att tabellerna laddas)
from apps.analytics import events  # noqa: F401  (registrerar event-API:t)
from apps.analytics import crm     # noqa: F401  (registrerar CRM-routes)
from apps.analytics import stats
from apps.analytics.auth import admin_required
from apps.chat.security import csrf_token


# Gor csrf_token() tillganglig i analytics/CRM-mallarna.
@blueprint.context_processor
def _inject_csrf():
    return {'csrf_token': csrf_token}


@blueprint.route('/admin')
@admin_required
def admin_home():
    return redirect(url_for('analytics_blueprint.dashboard'))


@blueprint.route('/admin/dashboard')
@admin_required
def dashboard():
    series = stats.daily_series(14)
    devices = stats.device_breakdown()
    cta = stats.top_cta(5)
    top_dev = max(devices.items(), key=lambda kv: kv[1]) if devices else ('–', 0)

    insights = []
    if cta:
        insights.append({'icon': 'fa-hand-pointer', 'title': 'Mest klickade',
                         'text': f"\"{cta[0]['text']}\" – {cta[0]['clicks']} klick."})
    insights.append({'icon': 'fa-signal', 'title': 'Live just nu',
                     'text': f"{len(stats.live_sessions())} besökare på sajten."})

    d = {
        'live_now': len(stats.live_sessions()),
        'today': stats.count_today(),
        'hot_leads': stats.hot_leads(),
        'new_leads': stats.form_submits(30),
        'days': series['labels'], 'visits': series['visits'],
        'clicks': series['clicks'], 'leads': series['leads'],
        'devices': devices, 'top_device_name': top_dev[0], 'top_device_pct': top_dev[1],
        'top_cta': cta,
        'top_pages': stats.top_pages(6),
        'recent': stats.recent_sessions(8),
        'insights': insights,
    }
    return render_template('analytics/dashboard.html', d=d)


@blueprint.route('/admin/live')
@admin_required
def live():
    return render_template('analytics/live.html')


@blueprint.route('/admin/live/data')
@admin_required
def live_data():
    sessions = [stats.session_view(s) for s in stats.live_sessions()]
    return jsonify(count=len(sessions), sessions=sessions)


@blueprint.route('/admin/leads')
@admin_required
def leads():
    return render_template('analytics/leads.html', leads=stats.lead_list())


@blueprint.route('/admin/innehall')
@admin_required
def content():
    return render_template('analytics/content.html',
                           posts=stats.top_blog_posts(10),
                           pages=stats.top_visited_pages(10))
