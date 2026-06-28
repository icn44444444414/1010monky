"""
Routes for analytics-dashboarden (steg 1: demodata).

Bakom admin-login (samma session som chatt-adminen). Skickar in demodata sa
hela dashboarden gar att se live; i nasta steg byts demodata mot riktiga
siffror fran VisitorSession/VisitorEvent/Lead.
"""
from functools import wraps

from flask import session, redirect, url_for, request, render_template

from apps.analytics import blueprint


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('chat_admin'):
            return redirect(url_for('chat_blueprint.admin_login', next=request.path))
        return view(*args, **kwargs)
    return wrapper


# Demodata tills analytics-modulen lagrar riktiga siffror.
DEMO = {
    'live_now': 3,
    'today': 247, 'today_delta': '+12%', 'today_up': True,
    'hot_leads': 5, 'hot_delta': '+2', 'hot_up': True,
    'new_leads': 18, 'new_delta': '+23%', 'new_up': True,
    'conversion': '4,2%', 'conv_delta': '-0,4%', 'conv_up': False,
    # linjediagram: senaste 30 dagarna
    'days': ['1 jun', '5 jun', '10 jun', '15 jun', '20 jun', '25 jun', '30 jun'],
    'visits': [120, 210, 190, 260, 240, 300, 280],
    'clicks': [40, 80, 70, 110, 95, 130, 120],
    'leads': [2, 4, 3, 6, 5, 8, 7],
    # enheter (donut)
    'devices': {'Mobil': 62, 'Dator': 33, 'Surfplatta': 5},
    # topp-CTA
    'top_cta': [
        {'text': 'Begär offert', 'clicks': 71, 'pct': 100},
        {'text': 'Se priser', 'clicks': 34, 'pct': 48},
        {'text': 'Boka samtal', 'clicks': 12, 'pct': 17},
    ],
    # leads per månad (stapel)
    'months': ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun'],
    'leads_per_month': [6, 9, 7, 12, 10, 14],
    # senaste leads
    'recent_leads': [
        {'name': 'Erik Lundgren', 'service': 'Ny hemsida', 'score': 82, 'status': 'Ny', 'cls': 'green'},
        {'name': 'Sara Holm', 'service': 'WordPress', 'score': 64, 'status': 'Kontaktad', 'cls': 'blue'},
        {'name': 'Johan Ek', 'service': 'Webbshop', 'score': 91, 'status': 'Offert skickad', 'cls': 'purple'},
        {'name': 'Anna Berg', 'service': 'SEO', 'score': 38, 'status': 'Ny', 'cls': 'green'},
    ],
    # insikter
    'insights': [
        {'icon': 'fa-fire', 'title': 'Het lead', 'text': 'Johan Ek (91) tittade på priser och kontakt.'},
        {'icon': 'fa-arrow-trend-down', 'title': 'Tapp i tratten', 'text': 'Många når kontakt men få skickar formuläret.'},
    ],
}


@blueprint.route('/admin')
@admin_required
def admin_home():
    return redirect(url_for('analytics_blueprint.dashboard'))


@blueprint.route('/admin/dashboard')
@admin_required
def dashboard():
    return render_template('analytics/dashboard.html', d=DEMO)
