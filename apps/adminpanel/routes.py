"""
Serverar Gentelella-adminpanelen som statiskt bygge pa /admin - utan losenord.

Den gamla chatt-/analytics-adminen togs bort 2026-06-29. Det har ar bara en
ren statisk servering av admin/dist (Gentelella v4, byggt med BASE_PATH=/admin/),
helt med sin egen stil.

Bygg om panelen sa har (fran projektroten):
  cd admin
  NODE_ENV=production BASE_PATH=/admin/ npx vite build

Startsidan /admin serverar dashboarden direkt. Gamla /admin/production/*.html
skickas vidare till rena admin-lankar.
Alla tillgangar (/admin/js, /admin/assets, /admin/images ...) ligger i dist-roten.
Push-routesen (/admin/push, /admin/install, /admin/sw.js ...) ar mer specifika
och tar fortfarande sina egna anrop; resten faller hit till de statiska filerna.
"""
import hmac
import os

from datetime import datetime, timezone

from flask import Blueprint, send_from_directory, redirect, abort, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from apps.adminpanel.ga_reports import overview
from apps.adminpanel.revenue_data import add_entry, delete_entry, overview as revenue_overview
from apps.adminpanel.leads_data import list_leads, update_lead, delete_lead, summary as leads_summary
from apps.adminpanel.offers_data import (
    list_offers, add_offer, update_offer, delete_offer, summary as offers_summary,
)
from apps.adminpanel.projects_data import (
    list_projects, add_project, update_project, delete_project, summary as projects_summary,
)
from apps.adminpanel import chat_data, push_data
from apps.adminpanel.kalkyl_data import (
    list_kalkyler, add_kalkyl, update_kalkyl, delete_kalkyl, summary as kalkyl_summary,
)
from apps.adminpanel import account_data
from flask import current_app

blueprint = Blueprint('adminpanel_blueprint', __name__, url_prefix='')

# .../1010monky/admin/dist  (tre niverar upp fran apps/adminpanel/routes.py)
_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'admin', 'dist',
)

# Mager modul-uppsattning for en frilansare (svenska clean-URLer).
# Lagg till en rad har nar en ny modulsida byggs i production/. Översikt = /admin.
_CLEAN_PAGES = {
    'leads': 'leads.html',
    'inkorg': 'inkorg.html',
    'offerter': 'offerter.html',
    'projekt': 'projekt.html',
    'intakter': 'ekonomi.html',
    'forkalkyl': 'forkalkyl.html',
    'efterkalkyl': 'efterkalkyl.html',
    'installningar': 'installningar.html',
}

_LEGACY_FILES = {
    'index.html': '',
    'index2.html': '',
    'leads.html': 'leads',
    'inkorg.html': 'inkorg',
    'offerter.html': 'offerter',
    'projekt.html': 'projekt',
    'ekonomi.html': 'intakter',
    'forkalkyl.html': 'forkalkyl',
    'efterkalkyl.html': 'efterkalkyl',
    'installningar.html': 'installningar',
}


def _send_admin_file(filename):
    full = os.path.normpath(os.path.join(_DIST, filename))
    if not full.startswith(os.path.normpath(_DIST)) or not os.path.isfile(full):
        abort(404)
    return send_from_directory(_DIST, filename)


def _redirect_clean(slug):
    target = '/admin' if not slug else f'/admin/{slug}'
    return redirect(target, code=302)


_LOGIN_HTML = """<!DOCTYPE html>
<html lang="sv"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Logga in – 1010monky</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
 *{box-sizing:border-box;margin:0;padding:0}
 body{font-family:Inter,-apple-system,Segoe UI,sans-serif;background:#14171a;color:#1e2633;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
 .card{background:#fff;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,.3);width:100%;max-width:360px;padding:32px}
 .brand{display:flex;align-items:center;gap:10px;margin-bottom:22px}
 .brand .m{width:38px;height:38px;border-radius:9px;background:#448C74;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700}
 .brand b{font-size:16px}.brand small{display:block;color:#7e8896;font-size:12px;font-weight:400}
 h1{font-size:18px;margin-bottom:4px}.sub{color:#7e8896;font-size:13px;margin-bottom:20px}
 label{display:block;font-size:12px;color:#626d7d;margin:12px 0 5px}
 input{width:100%;font:inherit;font-size:14px;padding:10px 12px;border:1px solid #e6e7eb;border-radius:9px;outline:none}
 input:focus{border-color:#448C74}
 button{width:100%;margin-top:20px;border:0;border-radius:9px;background:#448C74;color:#fff;font-weight:600;font-size:14px;padding:11px;cursor:pointer}
 button:hover{background:#36715d}
 .err{background:#fdeaea;color:#d63939;font-size:13px;padding:9px 12px;border-radius:8px;margin-bottom:8px}
</style></head><body>
 <form class="card" method="post" action="/admin/login">
  <div class="brand"><div class="m">10</div><div><b>1010monky</b><small>adminpanel</small></div></div>
  <h1>Logga in</h1><p class="sub">Du måste vara inloggad för att komma åt panelen.</p>
  {{ERROR}}
  <label for="user">Användarnamn</label><input id="user" name="user" autocomplete="username" autofocus>
  <label for="password">Lösenord</label><input id="password" name="password" type="password" autocomplete="current-password">
  <button type="submit">Logga in</button>
 </form>
</body></html>"""


def _is_authed():
    return bool(session.get('admin_authed'))


@blueprint.before_request
def _admin_guard():
    path = request.path
    if path in ('/admin/login', '/admin/logout'):
        return None
    is_api = path.startswith('/api/admin/')
    last = path.rsplit('/', 1)[-1]
    is_page = path in ('/admin', '/admin/') or (path.startswith('/admin/') and '.' not in last)
    if (is_api or is_page) and not _is_authed():
        if is_api:
            return jsonify({"ok": False, "error": "Inte inloggad."}), 401
        return redirect('/admin/login')
    return None


@blueprint.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        user = (request.form.get('user') or '').strip()
        pw = request.form.get('password') or ''
        cfg_user = current_app.config.get('ADMIN_USER', '')
        effective_hash = account_data.get_override_hash() or current_app.config.get('ADMIN_PASSWORD_HASH', '')
        if effective_hash and hmac.compare_digest(user, cfg_user) and check_password_hash(effective_hash, pw):
            session['admin_authed'] = True
            session.permanent = True
            return redirect('/admin')
        error = '<p class="err">Fel användarnamn eller lösenord.</p>'
    return _LOGIN_HTML.replace('{{ERROR}}', error)


@blueprint.route('/admin/logout')
def admin_logout():
    session.pop('admin_authed', None)
    return redirect('/admin/login')


@blueprint.route('/admin')
@blueprint.route('/admin/')
def admin_index():
    return _send_admin_file('production/index2.html')


@blueprint.route('/admin/production/index.html')
def admin_legacy_index():
    return _redirect_clean('')


@blueprint.route('/admin/production/<path:filename>')
def admin_legacy_production(filename):
    slug = _LEGACY_FILES.get(filename)
    if slug is not None:
        return _redirect_clean(slug)
    return _send_admin_file(f'production/{filename}')


@blueprint.route('/admin/<page>')
def admin_clean_page(page):
    if page in ('index', 'index2', 'index.html', 'index2.html'):
        return _redirect_clean('')

    if page.endswith('.html'):
        page_slug = page[:-5]
        if page_slug in _CLEAN_PAGES:
            return _redirect_clean(page_slug)

    filename = _CLEAN_PAGES.get(page)
    if not filename:
        if '.' in page:
            return _send_admin_file(page)
        abort(404)
    return _send_admin_file(f'production/{filename}')


@blueprint.route('/api/admin/ga/overview')
def admin_ga_overview():
    range_key = request.args.get('range', '30d')
    if range_key not in ('7d', '30d', '90d'):
        range_key = '30d'
    return jsonify(overview(range_key))


@blueprint.route('/api/admin/revenue', methods=['GET'])
def admin_revenue_overview():
    range_key = request.args.get('range', '30d')
    if range_key not in ('7d', '30d', '90d'):
        range_key = '30d'
    return jsonify(revenue_overview(range_key))


@blueprint.route('/api/admin/revenue', methods=['POST'])
def admin_revenue_add():
    try:
        entry = add_entry(request.get_json(silent=True) or {})
    except (TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "entry": entry, "summary": revenue_overview("30d")["summary"]}), 201


@blueprint.route('/api/admin/revenue/<entry_id>', methods=['DELETE'])
def admin_revenue_delete(entry_id):
    if not delete_entry(entry_id):
        return jsonify({"ok": False, "error": "Intäktsraden hittades inte."}), 404
    return jsonify({"ok": True, "summary": revenue_overview("30d")["summary"]})


@blueprint.route('/api/admin/leads', methods=['GET'])
def admin_leads():
    return jsonify({"summary": leads_summary(), "leads": list_leads()})


@blueprint.route('/api/admin/leads/<lead_id>', methods=['PATCH'])
def admin_lead_update(lead_id):
    item = update_lead(lead_id, request.get_json(silent=True) or {})
    if not item:
        return jsonify({"ok": False, "error": "Leadet hittades inte."}), 404
    return jsonify({"ok": True, "lead": item, "summary": leads_summary()})


@blueprint.route('/api/admin/leads/<lead_id>', methods=['DELETE'])
def admin_lead_delete(lead_id):
    if not delete_lead(lead_id):
        return jsonify({"ok": False, "error": "Leadet hittades inte."}), 404
    return jsonify({"ok": True, "summary": leads_summary()})


@blueprint.route('/api/admin/offers', methods=['GET'])
def admin_offers():
    return jsonify({"summary": offers_summary(), "offers": list_offers()})


@blueprint.route('/api/admin/offers', methods=['POST'])
def admin_offer_add():
    try:
        offer = add_offer(request.get_json(silent=True) or {})
    except (TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "offer": offer, "summary": offers_summary()}), 201


@blueprint.route('/api/admin/offers/<offer_id>', methods=['PATCH'])
def admin_offer_update(offer_id):
    offer = update_offer(offer_id, request.get_json(silent=True) or {})
    if not offer:
        return jsonify({"ok": False, "error": "Offerten hittades inte."}), 404
    return jsonify({"ok": True, "offer": offer, "summary": offers_summary()})


@blueprint.route('/api/admin/offers/<offer_id>', methods=['DELETE'])
def admin_offer_delete(offer_id):
    if not delete_offer(offer_id):
        return jsonify({"ok": False, "error": "Offerten hittades inte."}), 404
    return jsonify({"ok": True, "summary": offers_summary()})


@blueprint.route('/api/admin/offers/<offer_id>/book', methods=['POST'])
def admin_offer_book(offer_id):
    offer = next((o for o in list_offers() if o.get("id") == offer_id), None)
    if not offer:
        return jsonify({"ok": False, "error": "Offerten hittades inte."}), 404
    entry = add_entry({
        "title": f"Offert {offer['number']} – {offer['client']}",
        "amount": offer["total"],
        "status": "invoiced",
        "source": "Offert",
    })
    update_offer(offer_id, {"bookedRevenue": True, "status": "accepterad"})
    return jsonify({"ok": True, "entry": entry, "summary": offers_summary()})


@blueprint.route('/api/admin/projects', methods=['GET'])
def admin_projects():
    return jsonify({"summary": projects_summary(), "projects": list_projects()})


@blueprint.route('/api/admin/projects', methods=['POST'])
def admin_project_add():
    try:
        project = add_project(request.get_json(silent=True) or {})
    except (TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "project": project, "summary": projects_summary()}), 201


@blueprint.route('/api/admin/projects/<project_id>', methods=['PATCH'])
def admin_project_update(project_id):
    project = update_project(project_id, request.get_json(silent=True) or {})
    if not project:
        return jsonify({"ok": False, "error": "Projektet hittades inte."}), 404
    return jsonify({"ok": True, "project": project, "summary": projects_summary()})


@blueprint.route('/api/admin/projects/<project_id>', methods=['DELETE'])
def admin_project_delete(project_id):
    if not delete_project(project_id):
        return jsonify({"ok": False, "error": "Projektet hittades inte."}), 404
    return jsonify({"ok": True, "summary": projects_summary()})


@blueprint.route('/api/admin/chat', methods=['GET'])
def admin_chat_list():
    return jsonify({"summary": chat_data.summary(), "conversations": chat_data.list_conversations()})


@blueprint.route('/api/admin/chat/<conv_id>', methods=['GET'])
def admin_chat_get(conv_id):
    conv = chat_data.get_conversation(conv_id, mark_read=True)
    if not conv:
        return jsonify({"ok": False, "error": "Konversationen hittades inte."}), 404
    return jsonify({"ok": True, "conversation": conv, "summary": chat_data.summary()})


@blueprint.route('/api/admin/chat/<conv_id>/reply', methods=['POST'])
def admin_chat_reply(conv_id):
    text = (request.get_json(silent=True) or {}).get("text", "")
    conv = chat_data.admin_reply(conv_id, text)
    if not conv:
        return jsonify({"ok": False, "error": "Konversationen hittades inte."}), 404
    return jsonify({"ok": True, "conversation": conv})


@blueprint.route('/api/admin/chat/<conv_id>', methods=['PATCH'])
def admin_chat_status(conv_id):
    status = (request.get_json(silent=True) or {}).get("status", "")
    conv = chat_data.set_status(conv_id, status)
    if not conv:
        return jsonify({"ok": False, "error": "Ogiltig status eller konversation."}), 400
    return jsonify({"ok": True, "conversation": conv, "summary": chat_data.summary()})


@blueprint.route('/api/admin/chat/<conv_id>', methods=['DELETE'])
def admin_chat_delete(conv_id):
    if not chat_data.delete_conversation(conv_id):
        return jsonify({"ok": False, "error": "Konversationen hittades inte."}), 404
    return jsonify({"ok": True, "summary": chat_data.summary()})


@blueprint.route('/api/admin/push/key', methods=['GET'])
def admin_push_key():
    key = current_app.config.get("VAPID_PUBLIC_KEY", "")
    return jsonify({"key": key, "enabled": bool(key)})


@blueprint.route('/api/admin/push/subscribe', methods=['POST'])
def admin_push_subscribe():
    sub = request.get_json(silent=True) or {}
    if not push_data.add_subscription(sub):
        return jsonify({"ok": False, "error": "Ogiltig prenumeration."}), 400
    return jsonify({"ok": True, "count": push_data.count()})


@blueprint.route('/api/admin/push/unsubscribe', methods=['POST'])
def admin_push_unsubscribe():
    endpoint = (request.get_json(silent=True) or {}).get("endpoint", "")
    push_data.remove_subscription(endpoint)
    return jsonify({"ok": True, "count": push_data.count()})


@blueprint.route('/api/admin/kalkyl', methods=['GET'])
def admin_kalkyl_list():
    return jsonify({"summary": kalkyl_summary(), "kalkyler": list_kalkyler()})


@blueprint.route('/api/admin/kalkyl', methods=['POST'])
def admin_kalkyl_add():
    try:
        kalkyl = add_kalkyl(request.get_json(silent=True) or {})
    except (TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "kalkyl": kalkyl, "summary": kalkyl_summary()}), 201


@blueprint.route('/api/admin/kalkyl/<kalkyl_id>', methods=['PATCH'])
def admin_kalkyl_update(kalkyl_id):
    kalkyl = update_kalkyl(kalkyl_id, request.get_json(silent=True) or {})
    if not kalkyl:
        return jsonify({"ok": False, "error": "Kalkylen hittades inte."}), 404
    return jsonify({"ok": True, "kalkyl": kalkyl, "summary": kalkyl_summary()})


@blueprint.route('/api/admin/kalkyl/<kalkyl_id>', methods=['DELETE'])
def admin_kalkyl_delete(kalkyl_id):
    if not delete_kalkyl(kalkyl_id):
        return jsonify({"ok": False, "error": "Kalkylen hittades inte."}), 404
    return jsonify({"ok": True, "summary": kalkyl_summary()})


@blueprint.route('/api/admin/account/password', methods=['POST'])
def admin_change_password():
    data = request.get_json(silent=True) or {}
    current = data.get('current') or ''
    new = data.get('new') or ''
    if len(new) < 8:
        return jsonify({"ok": False, "error": "Nytt lösenord måste vara minst 8 tecken."}), 400
    effective = account_data.get_override_hash() or current_app.config.get('ADMIN_PASSWORD_HASH', '')
    if not (effective and check_password_hash(effective, current)):
        return jsonify({"ok": False, "error": "Fel nuvarande lösenord."}), 400
    account_data.set_password_hash(generate_password_hash(new))
    return jsonify({"ok": True})


@blueprint.route('/api/admin/status', methods=['GET'])
def admin_status():
    cfg = current_app.config
    return jsonify({
        "ga": bool(cfg.get('GA_PROPERTY_ID')),
        "analyticsTag": bool(cfg.get('GA_MEASUREMENT_ID')),
        "pushEnabled": bool(cfg.get('VAPID_PUBLIC_KEY')),
        "pushSubs": push_data.count(),
        "smtp": bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_USER')),
    })


@blueprint.route('/api/admin/export', methods=['GET'])
def admin_export():
    bundle = {
        "exportedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site": "1010monky",
        "leads": list_leads(),
        "offers": list_offers(),
        "projects": list_projects(),
        "kalkyler": list_kalkyler(),
        "chat": chat_data.export_all(),
    }
    resp = jsonify(bundle)
    resp.headers['Content-Disposition'] = 'attachment; filename="1010monky-data-export.json"'
    return resp


@blueprint.route('/admin/<path:filename>')
def admin_static(filename):
    # Skydd mot path traversal + 404 for saknade filer.
    return _send_admin_file(filename)
