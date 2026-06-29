"""Admin-konto: lösenordshash som kan bytas i drift. Lagras i account.json och
har företräde framför ADMIN_PASSWORD_HASH i .env (som är startvärdet). Gör att
lösenordsbyte funkar utan att redigera .env och överlever omstart.
"""
import json
import os


STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "account.json")


def get_override_hash():
    if not os.path.exists(STORE_PATH):
        return ""
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return ""
    if isinstance(data, dict):
        return str(data.get("passwordHash") or "")
    return ""


def set_password_hash(password_hash):
    tmp_path = f"{STORE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump({"passwordHash": password_hash}, handle)
    os.replace(tmp_path, STORE_PATH)
