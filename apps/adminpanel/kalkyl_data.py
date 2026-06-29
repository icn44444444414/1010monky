"""Kalkyl-lager (för- och efterkalkyl) för admin. En kalkyl = ett jobb.
Förkalkyl: uppskattade timmar × timpris + externa kostnader → riktpris.
Efterkalkyl: faktiska timmar/kostnader/pris → faktisk timpenning + diff mot plan.
Samma post delas av båda sidorna. Ren JSON (kalkyl_entries.json).
"""
import json
import os
import uuid
from datetime import datetime


STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kalkyl_entries.json")


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


def _compute(entry):
    """Lägger på uträknade fält. Muterar inte lagret, bara svaret."""
    e = dict(entry)
    est_hours = _num(e.get("estHours"))
    rate = _num(e.get("hourlyRate"))
    est_ext = _num(e.get("estExternal"))
    e["estPrice"] = round(est_hours * rate + est_ext)

    act_hours = _num(e.get("actHours"))
    act_ext = _num(e.get("actExternal"))
    act_price = _num(e.get("actPrice"))
    has_actuals = act_hours > 0 and act_price > 0
    e["hasActuals"] = has_actuals
    if has_actuals:
        net = act_price - act_ext
        e["actNet"] = round(net)
        e["actHourly"] = round(net / act_hours) if act_hours else 0
        e["hourlyDiff"] = round(e["actHourly"] - rate)
        e["hoursDiff"] = round(act_hours - est_hours, 1)
    return e


def add_kalkyl(data):
    data = data or {}
    title = str(data.get("title") or "").strip()
    if not title:
        raise ValueError("Kalkylen behöver en titel.")
    entry = {
        "id": str(uuid.uuid4()),
        "createdAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "title": title,
        "client": str(data.get("client") or "").strip(),
        "estHours": round(_num(data.get("estHours")), 1),
        "hourlyRate": round(_num(data.get("hourlyRate"), 800)),
        "estExternal": round(_num(data.get("estExternal"))),
        "actHours": 0,
        "actExternal": 0,
        "actPrice": 0,
        "note": str(data.get("note") or "").strip(),
    }
    items = _read()
    items.insert(0, entry)
    _write(items)
    return _compute(entry)


def list_kalkyler():
    return [_compute(e) for e in _read()]


_EST_FIELDS = {"title", "client", "estHours", "hourlyRate", "estExternal", "note"}
_ACT_FIELDS = {"actHours", "actExternal", "actPrice"}


def update_kalkyl(kalkyl_id, data):
    items = _read()
    found = None
    for entry in items:
        if entry.get("id") == kalkyl_id:
            for key in _EST_FIELDS:
                if key in data:
                    if key in ("title", "client", "note"):
                        entry[key] = str(data[key] or "").strip()
                    elif key == "estHours":
                        entry[key] = round(_num(data[key]), 1)
                    else:
                        entry[key] = round(_num(data[key]))
            for key in _ACT_FIELDS:
                if key in data:
                    entry[key] = round(_num(data[key]), 1) if key == "actHours" else round(_num(data[key]))
            found = entry
            break
    if found:
        _write(items)
        return _compute(found)
    return None


def delete_kalkyl(kalkyl_id):
    items = _read()
    kept = [e for e in items if e.get("id") != kalkyl_id]
    if len(kept) == len(items):
        return False
    _write(kept)
    return True


def summary():
    items = [_compute(e) for e in _read()]
    done = [e for e in items if e.get("hasActuals")]
    est_pipeline = round(sum(e["estPrice"] for e in items))
    avg_hourly = round(sum(e["actHourly"] for e in done) / len(done)) if done else 0
    return {
        "total": len(items),
        "done": len(done),
        "estPipeline": est_pipeline,
        "avgActHourly": avg_hourly,
    }
