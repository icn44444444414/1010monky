"""
Validering och sanering for chatt-input.

Hall logiken enkel och defensiv: blockera tomt, kapa for langt, kanna igen
en uppenbar honeypot. Tyngre spam-/rate-limit-skydd byggs ut i Milestone 8.
Lagring sker som ren text; HTML-escapas vid rendering av Jinja (autoescape),
sa vi sparar aldrig raa HTML som kan kora som markup.
"""
import re

MAX_MESSAGE_LEN = 4000
MAX_NAME_LEN = 120
MAX_EMAIL_LEN = 255
MAX_PHONE_LEN = 60

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_WS_RE = re.compile(r'[ \t]+')


def clean_text(value, max_len):
    """Trimma, normalisera whitespace och kapa till max_len. None -> ''."""
    if not value:
        return ''
    text = str(value).replace('\r\n', '\n').strip()
    text = _WS_RE.sub(' ', text)
    return text[:max_len]


def valid_message(text):
    """Ett giltigt meddelande ar icke-tomt och inte langre an maxgransen."""
    return bool(text) and len(text) <= MAX_MESSAGE_LEN


def valid_email_optional(email):
    """Anonymt tillatet: tom e-post ar ok. Men om angiven maste den se ut som e-post."""
    if not email:
        return True
    return bool(_EMAIL_RE.match(email)) and len(email) <= MAX_EMAIL_LEN
