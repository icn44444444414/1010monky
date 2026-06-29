"""Projekt-lager för admin. Ren JSON-fil (projects_entries.json), samma mönster
som de andra modulerna. Ett projekt = ett jobb: titel, kund, värde, start,
deadline och status (offert/pagaende/levererat/pausad).
"""
import json
import os
import uuid
from datetime import date, datetime


STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects_entries.json")
STATUSES = ("offert", "pagaende", "levererat", "pausad")


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


def _date_or_empty(value):
    if not value:
        return ""
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        return ""


def add_project(data):
    data = data or {}
    title = str(data.get("title") or "").strip()
    if not title:
        raise ValueError("Projektet behöver en titel.")
    status = str(data.get("status") or "pagaende").strip().lower()
    if status not in STATUSES:
        status = "pagaende"
    project = {
        "id": str(uuid.uuid4()),
        "createdAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "title": title,
        "client": str(data.get("client") or "").strip(),
        "value": round(_num(data.get("value"), 0), 2),
        "startDate": _date_or_empty(data.get("startDate")) or date.today().isoformat(),
        "deadline": _date_or_empty(data.get("deadline")),
        "status": status,
        "note": str(data.get("note") or "").strip(),
    }
    items = _read()
    items.insert(0, project)
    _write(items)
    return project


def list_projects():
    return _read()


def update_project(project_id, data):
    items = _read()
    found = None
    for project in items:
        if project.get("id") == project_id:
            if "status" in data:
                status = str(data["status"]).strip().lower()
                if status in STATUSES:
                    project["status"] = status
            if "note" in data:
                project["note"] = str(data["note"] or "").strip()
            if "value" in data:
                project["value"] = round(_num(data.get("value"), project.get("value", 0)), 2)
            if "deadline" in data:
                project["deadline"] = _date_or_empty(data.get("deadline"))
            found = project
            break
    if found:
        _write(items)
    return found


def delete_project(project_id):
    items = _read()
    kept = [p for p in items if p.get("id") != project_id]
    if len(kept) == len(items):
        return False
    _write(kept)
    return True


def summary():
    items = _read()
    by_status = {}
    for project in items:
        status = project.get("status") or "pagaende"
        by_status[status] = by_status.get(status, 0) + 1
    active_value = round(sum(p.get("value", 0) for p in items if p.get("status") == "pagaende"), 2)
    return {
        "total": len(items),
        "active": by_status.get("pagaende", 0),
        "delivered": by_status.get("levererat", 0),
        "byStatus": by_status,
        "activeValue": active_value,
    }
