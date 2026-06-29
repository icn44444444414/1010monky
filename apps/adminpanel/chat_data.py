"""Chatt-lager: konversationer + meddelanden. Ren JSON-fil, polling-baserad
(inget websocket). Besökaren identifieras av en hemlig token (uuid) som widgeten
sparar i localStorage. Admin svarar via inkorgen. Lågt volym-antagande (frilansare).
"""
import json
import os
import uuid
from datetime import datetime, timezone


STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_conversations.json")
MAX_TEXT = 4000


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def _by_token(convs, token):
    return next((c for c in convs if token and c.get("token") == token), None)


def _by_id(convs, conv_id):
    return next((c for c in convs if c.get("id") == conv_id), None)


def _message(sender, text):
    return {"id": uuid.uuid4().hex[:10], "from": sender, "text": str(text)[:MAX_TEXT], "at": _now()}


# ---- Publik (besökare) ----

def visitor_send(token, text, name=None, page=None):
    """Lagg ett besokarmeddelande. Skapar konversation om token saknas/okand.
    Returnerar (conversation, token)."""
    convs = _read()
    conv = _by_token(convs, token)
    if not conv:
        token = uuid.uuid4().hex
        conv = {
            "id": uuid.uuid4().hex[:12],
            "token": token,
            "createdAt": _now(),
            "lastAt": _now(),
            "status": "open",
            "visitorName": (name or "").strip() or "Besökare",
            "page": (page or "")[:200],
            "adminUnread": 0,
            "visitorUnread": 0,
            "messages": [],
        }
        convs.insert(0, conv)
    text = (text or "").strip()
    if text:
        conv["messages"].append(_message("visitor", text))
        conv["adminUnread"] = conv.get("adminUnread", 0) + 1
        conv["lastAt"] = _now()
        conv["status"] = "open"
        if name and conv.get("visitorName") in ("Besökare", ""):
            conv["visitorName"] = name.strip()
        _write(convs)
    return conv, token


def visitor_poll(token):
    convs = _read()
    conv = _by_token(convs, token)
    if not conv:
        return None
    if conv.get("visitorUnread"):
        conv["visitorUnread"] = 0
        _write(convs)
    return conv


# ---- Admin ----

def list_conversations():
    convs = _read()
    out = []
    for c in convs:
        msgs = c.get("messages", [])
        last = msgs[-1] if msgs else None
        out.append({
            "id": c.get("id"),
            "visitorName": c.get("visitorName", "Besökare"),
            "status": c.get("status", "open"),
            "adminUnread": c.get("adminUnread", 0),
            "lastAt": c.get("lastAt"),
            "page": c.get("page", ""),
            "lastMessage": (last["text"][:90] if last else ""),
            "lastFrom": (last["from"] if last else ""),
        })
    out.sort(key=lambda x: x.get("lastAt") or "", reverse=True)
    return out


def get_conversation(conv_id, mark_read=False):
    convs = _read()
    conv = _by_id(convs, conv_id)
    if not conv:
        return None
    if mark_read and conv.get("adminUnread"):
        conv["adminUnread"] = 0
        _write(convs)
    return conv


def admin_reply(conv_id, text):
    convs = _read()
    conv = _by_id(convs, conv_id)
    if not conv:
        return None
    text = (text or "").strip()
    if text:
        conv["messages"].append(_message("admin", text))
        conv["visitorUnread"] = conv.get("visitorUnread", 0) + 1
        conv["adminUnread"] = 0
        conv["lastAt"] = _now()
        _write(convs)
    return conv


def set_status(conv_id, status):
    if status not in ("open", "closed"):
        return None
    convs = _read()
    conv = _by_id(convs, conv_id)
    if not conv:
        return None
    conv["status"] = status
    _write(convs)
    return conv


def delete_conversation(conv_id):
    convs = _read()
    kept = [c for c in convs if c.get("id") != conv_id]
    if len(kept) == len(convs):
        return False
    _write(kept)
    return True


def summary():
    convs = _read()
    return {
        "open": sum(1 for c in convs if c.get("status") == "open"),
        "unread": sum(c.get("adminUnread", 0) for c in convs),
        "total": len(convs),
    }


def export_all():
    """Fulla konversationer for dataexport (GDPR)."""
    return _read()
