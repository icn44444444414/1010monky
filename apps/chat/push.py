"""
Webb-push for chatt-adminen (sa Matias far en pling i mobilen nar nagon skriver).

Anvander VAPID (sjalv-hostat, ingen Firebase). Admin-appen/sidan prenumererar och
skickar sin push-subscription hit; nar en besokare skriver skickar backenden en
push till alla sparade prenumerationer via pywebpush. Skickas i en bakgrundstrad
sa besokarens meddelande aldrig fordrojs.

Nycklar i .env:
  VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUB (mailto:info@1010monky.se)
"""
import os
import json
import logging
import threading

from flask import request, jsonify, current_app

from apps import db
from apps.chat import blueprint
from apps.chat.models import PushSubscription
from apps.chat.admin_routes import admin_required

log = logging.getLogger('chat.push')

VAPID_PUBLIC = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_SUB = os.getenv('VAPID_SUB', 'mailto:info@1010monky.se')


# ---- Skicka push ----

def _send_all(app, payload):
    """Korande i en bakgrundstrad. Skickar till alla prenumerationer och
    stadar bort doda (404/410)."""
    try:
        from pywebpush import webpush, WebPushException
    except Exception:
        return
    with app.app_context():
        dead = []
        for s in PushSubscription.query.all():
            try:
                webpush(
                    subscription_info={'endpoint': s.endpoint,
                                       'keys': {'p256dh': s.p256dh, 'auth': s.auth}},
                    data=json.dumps(payload),
                    vapid_private_key=VAPID_PRIVATE,
                    vapid_claims={'sub': VAPID_SUB},
                    timeout=10,
                )
            except WebPushException as e:
                code = getattr(getattr(e, 'response', None), 'status_code', None)
                if code in (404, 410):
                    dead.append(s)
            except Exception:
                pass
        for s in dead:
            db.session.delete(s)
        if dead:
            db.session.commit()


def notify_new_message(body, url='/admin/chat'):
    """Anropas nar en besokare skrivit. Fire-and-forget i en trad."""
    if not (VAPID_PRIVATE and VAPID_PUBLIC):
        return
    app = current_app._get_current_object()
    payload = {'title': 'Nytt chattmeddelande', 'body': (body or '').strip()[:120], 'url': url}
    threading.Thread(target=_send_all, args=(app, payload), daemon=True).start()


# ---- Endpoints (admin) ----

@blueprint.route('/admin/push/key')
@admin_required
def push_key():
    return jsonify(key=VAPID_PUBLIC, enabled=bool(VAPID_PUBLIC and VAPID_PRIVATE))


@blueprint.route('/admin/push/subscribe', methods=['POST'])
@admin_required
def push_subscribe():
    data = request.get_json(silent=True) or {}
    endpoint = (data.get('endpoint') or '').strip()
    keys = data.get('keys') or {}
    if not endpoint or not keys.get('p256dh') or not keys.get('auth'):
        return jsonify(ok=False, error='ogiltig prenumeration'), 400
    if not PushSubscription.query.filter_by(endpoint=endpoint).first():
        db.session.add(PushSubscription(endpoint=endpoint,
                                        p256dh=keys['p256dh'], auth=keys['auth']))
        db.session.commit()
    return jsonify(ok=True)


@blueprint.route('/admin/push/test', methods=['POST'])
@admin_required
def push_test():
    notify_new_message('Testnotis fran 1010monky-chatten.')
    return jsonify(ok=True)


# ---- PWA/TWA: manifest, service worker, asset links ----

from flask import Response, current_app as _ca  # noqa: E402

_SW_JS = """
self.addEventListener('push', function (e) {
  var d = {}; try { d = e.data.json(); } catch (x) {}
  e.waitUntil(self.registration.showNotification(d.title || 'Nytt meddelande', {
    body: d.body || '', icon: '/static/app-icons/icon-192x192.png',
    badge: '/static/app-icons/icon-192x192.png', tag: 'monky-chat',
    data: { url: d.url || '/admin/chat' }
  }));
});
self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || '/admin/chat';
  e.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (cl) {
    for (var i = 0; i < cl.length; i++) { if (cl[i].url.indexOf(url) > -1 && 'focus' in cl[i]) return cl[i].focus(); }
    if (clients.openWindow) return clients.openWindow(url);
  }));
});
"""


@blueprint.route('/admin/sw.js')
def push_sw():
    r = Response(_SW_JS, mimetype='application/javascript')
    r.headers['Service-Worker-Allowed'] = '/admin/'
    return r


@blueprint.route('/admin/manifest.webmanifest')
def push_manifest():
    root = _ca.config.get('ASSETS_ROOT', '/static')
    return jsonify({
        'name': '1010monky Chatt', 'short_name': 'Monky Chatt',
        'start_url': '/admin/chat', 'scope': '/admin/', 'display': 'standalone',
        'background_color': '#f6f8f9', 'theme_color': '#448C74',
        'icons': [
            {'src': root + '/app-icons/icon-192x192.png', 'sizes': '192x192', 'type': 'image/png'},
            {'src': root + '/app-icons/icon-512x512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
        ],
    })


@blueprint.route('/.well-known/assetlinks.json')
def assetlinks():
    # Verifierar TWA-appen (tar bort webblasar-raden). Fingeravtrycket fran
    # signeringsnyckeln satts i .env (TWA_SHA256) efter forsta APK-bygget.
    fp = os.getenv('TWA_SHA256', '')
    pkg = os.getenv('TWA_PACKAGE', 'se.monky1010.chat')
    return jsonify([{
        'relation': ['delegate_permission/common.handle_all_urls'],
        'target': {'namespace': 'android_app', 'package_name': pkg,
                   'sha256_cert_fingerprints': [fp] if fp else []},
    }])
