"""Offert-lager för admin. Ren JSON-fil (offers_entries.json), samma mönster
som revenue_data.py / leads_data.py. En offert har rader (beskrivning, antal,
à-pris), momssats och status. Summor räknas ut server-side så de alltid stämmer.
"""
import json
import os
import uuid
from datetime import date, datetime


STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offers_entries.json")
STATUSES = ("utkast", "skickad", "accepterad", "avbojd")


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


def _num(value, default=0.0):
    try:
        return float(str(value).replace(",", ".").strip() or default)
    except (TypeError, ValueError):
        return default


def _clean_items(raw):
    items = []
    for row in raw or []:
        desc = str(row.get("desc") or "").strip()
        if not desc:
            continue
        qty = _num(row.get("qty"), 1) or 1
        price = _num(row.get("unitPrice"), 0)
        items.append({"desc": desc, "qty": round(qty, 2), "unitPrice": round(price, 2)})
    return items


def _calc(items, vat_rate):
    subtotal = sum(i["qty"] * i["unitPrice"] for i in items)
    vat = subtotal * vat_rate / 100.0
    return round(subtotal, 2), round(vat, 2), round(subtotal + vat, 2)


def _next_number(items):
    year = date.today().year
    used = sum(1 for it in items if str(it.get("number", "")).startswith(str(year)))
    return f"{year}-{used + 1:03d}"


def add_offer(data):
    items = _clean_items((data or {}).get("items"))
    if not items:
        raise ValueError("Lägg till minst en rad med beskrivning.")
    vat_rate = _num((data or {}).get("vatRate"), 25)
    status = str((data or {}).get("status") or "utkast").strip().lower()
    if status not in STATUSES:
        status = "utkast"
    subtotal, vat, total = _calc(items, vat_rate)

    store = _read()
    offer = {
        "id": str(uuid.uuid4()),
        "number": _next_number(store),
        "createdAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "date": date.today().isoformat(),
        "client": str((data or {}).get("client") or "").strip() or "Okänd kund",
        "email": str((data or {}).get("email") or "").strip(),
        "items": items,
        "vatRate": vat_rate,
        "subtotal": subtotal,
        "vat": vat,
        "total": total,
        "status": status,
        "note": str((data or {}).get("note") or "").strip(),
        "bookedRevenue": False,
    }
    store.insert(0, offer)
    _write(store)
    return offer


def list_offers():
    return _read()


def update_offer(offer_id, data):
    store = _read()
    found = None
    for offer in store:
        if offer.get("id") == offer_id:
            if "status" in data:
                status = str(data["status"]).strip().lower()
                if status in STATUSES:
                    offer["status"] = status
            if "note" in data:
                offer["note"] = str(data["note"] or "").strip()
            if data.get("bookedRevenue") is True:
                offer["bookedRevenue"] = True
            found = offer
            break
    if found:
        _write(store)
    return found


def delete_offer(offer_id):
    store = _read()
    kept = [o for o in store if o.get("id") != offer_id]
    if len(kept) == len(store):
        return False
    _write(kept)
    return True


def summary():
    store = _read()
    by_status = {}
    for offer in store:
        status = offer.get("status") or "utkast"
        by_status[status] = by_status.get(status, 0) + 1
    accepted_value = round(sum(o.get("total", 0) for o in store if o.get("status") == "accepterad"), 2)
    sent_value = round(sum(o.get("total", 0) for o in store if o.get("status") == "skickad"), 2)
    return {
        "total": len(store),
        "sent": by_status.get("skickad", 0),
        "accepted": by_status.get("accepterad", 0),
        "byStatus": by_status,
        "acceptedValue": accepted_value,
        "outstandingValue": sent_value,
    }
