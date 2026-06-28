"""
Publikt API for chatt-widgeten (Milestone 4).

Sakerhets-/anonymitetsprinciper:
  * Utat anvands ALLTID conversation-token (ogissningsbart), aldrig det
    lopande id:t -> ingen kan rakna upp och lasa andras konversationer.
  * Namn/e-post/telefon ar frivilligt -> besokaren kan vara helt anonym.
  * Svar innehaller ingen PII (se ChatMessage.to_public).
  * Honeypot-falt 'website' fangar enkla bottar (samma monster som /api/contact).
  * Mjuk per-IP-grans pa nya konversationer (full rate limit i M8).

Endpoints:
  POST /api/chat/start                 -> skapar konversation, returnerar token
  POST /api/chat/message               -> lagger besoksmeddelande (via token)
  GET  /api/chat/messages/<token>      -> hamtar trad (for polling i M6)
"""
from datetime import datetime, timedelta

from flask import request, jsonify

from apps import db
from apps.chat import blueprint
from apps.chat import models  # noqa: F401  (sakerstaller att modeller laddas)
from apps.chat import admin_routes  # noqa: F401  (registrerar admin-routes)
from apps.chat.models import ChatConversation, ChatMessage
from apps.chat.validators import (
    clean_text, valid_message, valid_email_optional,
    MAX_NAME_LEN, MAX_EMAIL_LEN, MAX_PHONE_LEN,
)

# Mjuk grans: max antal nya konversationer per IP per timme.
MAX_NEW_CONV_PER_IP_PER_HOUR = 8


def _payload():
    return request.form if request.form else (request.get_json(silent=True) or {})


def _client_ip():
    # Bakom nginx ar remote_addr 127.0.0.1 -> las forsta IP i X-Forwarded-For.
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()[:64]
    return (request.remote_addr or '')[:64]


def _is_bot(data):
    # Honeypot: dolt falt som bara bottar fyller i.
    return bool((data.get('website') or '').strip())


@blueprint.route('/api/chat/start', methods=['POST'])
def chat_start():
    data = _payload()

    # Honeypot -> latsas lyckas, spara inget.
    if _is_bot(data):
        return jsonify(success=True, conversation_token=None)

    message = clean_text(data.get('message'), 4000)
    if not valid_message(message):
        return jsonify(success=False, error='Skriv ett meddelande.'), 400

    email = clean_text(data.get('email'), MAX_EMAIL_LEN)
    if not valid_email_optional(email):
        return jsonify(success=False, error='Ogiltig e-postadress.'), 400

    ip = _client_ip()
    if ip:
        since = datetime.utcnow() - timedelta(hours=1)
        recent = ChatConversation.query.filter(
            ChatConversation.ip_address == ip,
            ChatConversation.created_at >= since,
        ).count()
        if recent >= MAX_NEW_CONV_PER_IP_PER_HOUR:
            return jsonify(success=False,
                           error='For manga forsok. Forsok igen senare.'), 429

    conv = ChatConversation(
        visitor_name=clean_text(data.get('name'), MAX_NAME_LEN) or None,
        visitor_email=email or None,
        visitor_phone=clean_text(data.get('phone'), MAX_PHONE_LEN) or None,
        status='new',
        source_page=clean_text(data.get('source_page'), 255) or None,
        ip_address=ip or None,
        user_agent=clean_text(request.headers.get('User-Agent'), 400) or None,
        last_seen_at=datetime.utcnow(),
    )
    db.session.add(conv)
    db.session.flush()  # ger conv.id + public_token
    db.session.add(ChatMessage(conversation_id=conv.id,
                               sender_type='visitor', body=message))
    db.session.commit()

    return jsonify(success=True, conversation_token=conv.public_token)


@blueprint.route('/api/chat/message', methods=['POST'])
def chat_message():
    data = _payload()

    if _is_bot(data):
        return jsonify(success=True)

    token = (data.get('conversation_token') or data.get('token') or '').strip()
    conv = ChatConversation.query.filter_by(public_token=token).first()
    if not conv:
        return jsonify(success=False, error='Konversationen hittades inte.'), 404

    message = clean_text(data.get('message'), 4000)
    if not valid_message(message):
        return jsonify(success=False, error='Skriv ett meddelande.'), 400

    # Tyst drop pa spam-markerade -> ingen feedback till spammaren.
    if conv.status == 'spam':
        return jsonify(success=True)

    db.session.add(ChatMessage(conversation_id=conv.id,
                               sender_type='visitor', body=message))
    conv.touch()
    conv.last_seen_at = datetime.utcnow()
    db.session.commit()

    return jsonify(success=True)


@blueprint.route('/api/chat/messages/<token>', methods=['GET'])
def chat_messages(token):
    conv = ChatConversation.query.filter_by(public_token=(token or '').strip()).first()
    if not conv:
        return jsonify(success=False, error='Konversationen hittades inte.'), 404

    conv.last_seen_at = datetime.utcnow()
    db.session.commit()

    return jsonify(
        success=True,
        status=conv.status,
        messages=[m.to_public() for m in conv.messages],
    )
