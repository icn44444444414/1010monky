"""Web-push (VAPID) för admin-notiser. Lagrar pushprenumerationer (push_subs.json)
och skickar notis när en besökare skriver i chatten. Best-effort: om nycklar
saknas eller pywebpush inte finns gör send_to_all ingenting (chatten påverkas ej).
"""
import json
import os

from flask import current_app


STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "push_subs.json")


def _read():
    if not os.path.exists(STORE_PATH):
        return []
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _write(items):
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    tmp_path = f"{STORE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(items, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, STORE_PATH)


def add_subscription(sub):
    if not isinstance(sub, dict) or not sub.get("endpoint"):
        return False
    subs = [s for s in _read() if s.get("endpoint") != sub["endpoint"]]
    subs.append(sub)
    _write(subs)
    return True


def remove_subscription(endpoint):
    subs = _read()
    kept = [s for s in subs if s.get("endpoint") != endpoint]
    if len(kept) == len(subs):
        return False
    _write(kept)
    return True


def count():
    return len(_read())


def send_to_all(title, body, url="/admin/inkorg"):
    """Skicka push till alla prenumeranter. Returnerar antal lyckade. Best-effort."""
    pub = current_app.config.get("VAPID_PUBLIC_KEY")
    priv = current_app.config.get("VAPID_PRIVATE_KEY")
    if not (pub and priv):
        return 0
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return 0

    claim_email = current_app.config.get("VAPID_CLAIM_EMAIL", "mailto:info@1010monky.se")
    payload = json.dumps({"title": title, "body": body, "url": url})
    subs = _read()
    sent = 0
    dead = []
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=priv,
                vapid_claims={"sub": claim_email},
                timeout=10,
            )
            sent += 1
        except WebPushException as exc:
            resp = getattr(exc, "response", None)
            if resp is not None and resp.status_code in (404, 410):
                dead.append(sub.get("endpoint"))
        except Exception:
            pass
    if dead:
        _write([s for s in subs if s.get("endpoint") not in dead])
    return sent
