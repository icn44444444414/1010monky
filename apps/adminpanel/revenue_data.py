import json
import os
import uuid
from datetime import date, datetime, timedelta


STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "revenue_entries.json")


def _today():
    return date.today()


def _parse_date(value):
    if not value:
        return _today()
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _read_entries():
    if not os.path.exists(STORE_PATH):
        return []
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _write_entries(entries):
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    tmp_path = f"{STORE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, STORE_PATH)


def _range_start(range_key):
    today = _today()
    if range_key == "7d":
        return today - timedelta(days=6)
    if range_key == "90d":
        return today - timedelta(days=89)
    return today - timedelta(days=29)


def _clean_entry(data):
    title = str(data.get("title") or data.get("client") or "").strip()
    amount = float(str(data.get("amount", "0")).replace(",", "."))
    if amount <= 0:
        raise ValueError("Belopp måste vara större än 0.")

    entry_date = _parse_date(data.get("date")).isoformat()
    status = str(data.get("status") or "paid").strip().lower()
    if status not in ("paid", "invoiced", "pending", "lead"):
        status = "paid"

    source = str(data.get("source") or "Manuell").strip() or "Manuell"
    currency = str(data.get("currency") or "SEK").strip().upper() or "SEK"

    return {
        "id": str(uuid.uuid4()),
        "date": entry_date,
        "title": title or "Intäkt",
        "amount": round(amount, 2),
        "currency": currency,
        "source": source,
        "status": status,
        "note": str(data.get("note") or "").strip(),
        "createdAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def add_entry(data):
    entry = _clean_entry(data or {})
    entries = _read_entries()
    entries.append(entry)
    entries.sort(key=lambda item: item.get("date", ""), reverse=True)
    _write_entries(entries)
    return entry


def delete_entry(entry_id):
    entries = _read_entries()
    kept = [entry for entry in entries if entry.get("id") != entry_id]
    if len(kept) == len(entries):
        return False
    _write_entries(kept)
    return True


def _sum(entries):
    return round(sum(float(entry.get("amount") or 0) for entry in entries), 2)


def _group_sum(entries, key):
    grouped = {}
    for entry in entries:
        group = entry.get(key) or "Okänd"
        grouped[group] = round(grouped.get(group, 0) + float(entry.get("amount") or 0), 2)
    return [{"label": label, "amount": amount} for label, amount in sorted(grouped.items(), key=lambda item: item[1], reverse=True)]


def _month_key(entry):
    return str(entry.get("date", ""))[:7] or "Okänd"


def summary(range_key="30d"):
    entries = _read_entries()
    start = _range_start(range_key)
    today = _today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    def in_range(entry, from_date):
        try:
            entry_date = _parse_date(entry.get("date"))
        except ValueError:
            return False
        return entry_date >= from_date

    paid = [entry for entry in entries if entry.get("status") == "paid"]
    pipeline = [entry for entry in entries if entry.get("status") != "paid"]
    ranged = [entry for entry in entries if in_range(entry, start)]
    month_entries = [entry for entry in entries if in_range(entry, month_start)]
    year_entries = [entry for entry in entries if in_range(entry, year_start)]

    by_month = {}
    for entry in entries:
        key = _month_key(entry)
        by_month[key] = round(by_month.get(key, 0) + float(entry.get("amount") or 0), 2)

    return {
        "currency": "SEK",
        "count": len(entries),
        "total": _sum(paid),
        "pending": _sum(pipeline),
        "projected": _sum(entries),
        "rangeTotal": _sum(ranged),
        "monthTotal": _sum(month_entries),
        "yearTotal": _sum(year_entries),
        "average": round(_sum(paid) / len(paid), 2) if paid else 0,
        "bySource": _group_sum(entries, "source"),
        "byMonth": [{"label": label, "amount": amount} for label, amount in sorted(by_month.items())[-12:]],
        "recent": entries[:20],
    }


def overview(range_key="30d"):
    return {
        "configured": True,
        "range": range_key,
        "summary": summary(range_key),
        "entries": _read_entries(),
    }
