"""Strukturerat lead-lager för admin-CRM.

Kontaktformuläret (apps/pages/routes.py) sparar varje förfrågan hit som en
strukturerad post i leads_entries.json (utöver mejl + textloggen). Adminpanelen
läser/uppdaterar härifrån. Ren JSON-fil, samma enkla mönster som revenue_data.py.
"""
import json
import os
import uuid
from datetime import date, datetime, timedelta


STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads_entries.json")
STATUSES = ("ny", "kontaktad", "offert", "vunnen", "forlorad")


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


def add_lead(data):
    services = data.get("services") or []
    if isinstance(services, str):
        services = [services]
    item = {
        "id": str(uuid.uuid4()),
        "createdAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "date": date.today().isoformat(),
        "name": str(data.get("name") or "").strip(),
        "email": str(data.get("email") or "").strip(),
        "phone": str(data.get("phone") or "").strip(),
        "company": str(data.get("company") or "").strip(),
        "services": [str(s).strip() for s in services if str(s).strip()],
        "message": str(data.get("message") or "").strip(),
        "source": str(data.get("source") or "kontaktformulär").strip(),
        "status": "ny",
        "note": "",
    }
    items = _read()
    items.insert(0, item)
    _write(items)
    return item


def list_leads():
    return _read()


def update_lead(lead_id, data):
    items = _read()
    found = None
    for item in items:
        if item.get("id") == lead_id:
            if "status" in data:
                status = str(data["status"]).strip().lower()
                if status in STATUSES:
                    item["status"] = status
            if "note" in data:
                item["note"] = str(data["note"] or "").strip()
            found = item
            break
    if found:
        _write(items)
    return found


def delete_lead(lead_id):
    items = _read()
    kept = [item for item in items if item.get("id") != lead_id]
    if len(kept) == len(items):
        return False
    _write(kept)
    return True


def summary():
    items = _read()
    by_status = {}
    for item in items:
        status = item.get("status") or "ny"
        by_status[status] = by_status.get(status, 0) + 1

    today = date.today()
    last7 = today - timedelta(days=6)

    def parse(value):
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None

    new7 = sum(1 for item in items if (parse(item.get("date")) or today) >= last7)
    return {
        "total": len(items),
        "new7d": new7,
        "open": sum(by_status.get(s, 0) for s in ("ny", "kontaktad", "offert")),
        "won": by_status.get("vunnen", 0),
        "byStatus": by_status,
    }
