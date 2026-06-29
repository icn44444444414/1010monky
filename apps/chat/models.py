"""
Databasmodeller for chatten.

ChatConversation = en besokares chatt-trad. ChatMessage = ett meddelande i en
trad. Relation 1-till-manga. sender_type stoder 'bot' redan nu sa systemet ar
AI-redo utan schemandring senare.
"""
import secrets
from datetime import datetime
from apps import db


# Tillatna varden (hally som konstanter sa admin/API kan validera mot dem)
CONV_STATUSES = ('new', 'open', 'closed', 'spam')
SENDER_TYPES = ('visitor', 'admin', 'bot', 'system')


def _new_token():
    # 192 bitar entropi -> ogissningsbart. Anvands utat istallet for det
    # lopande id:t sa ingen kan rakna upp och lasa andras konversationer.
    return secrets.token_urlsafe(24)


class ChatConversation(db.Model):
    __tablename__ = 'chat_conversations'

    id = db.Column(db.Integer, primary_key=True)
    # Publik, ogissningsbar nyckel. Widgeten anvander denna; aldrig id:t.
    public_token = db.Column(db.String(48), unique=True, index=True,
                             nullable=False, default=_new_token)
    visitor_name = db.Column(db.String(120))
    visitor_email = db.Column(db.String(255))
    visitor_phone = db.Column(db.String(60))
    status = db.Column(db.String(20), default='new', nullable=False, index=True)
    source_page = db.Column(db.String(255))
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(400))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)
    last_seen_at = db.Column(db.DateTime)

    messages = db.relationship(
        'ChatMessage',
        backref='conversation',
        order_by='ChatMessage.created_at',
        cascade='all, delete-orphan',
        lazy='select',
    )

    @property
    def last_message(self):
        return self.messages[-1] if self.messages else None

    @property
    def unread_count(self):
        # Olasta besoksmeddelanden (det admin behover agera pa).
        return sum(1 for m in self.messages
                   if m.sender_type == 'visitor' and not m.is_read)

    def touch(self):
        self.updated_at = datetime.utcnow()

    def __repr__(self):
        return f'<ChatConversation {self.id} {self.status} {self.visitor_name!r}>'


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey('chat_conversations.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    sender_type = db.Column(db.String(20), default='visitor', nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_public(self):
        # Endast falt som ar ofarliga att visa for besokaren. Ingen PII,
        # inga interna id:n, ingen is_read/ip.
        return {
            'id': self.id,
            'sender_type': self.sender_type,
            'body': self.body,
            'created_at': self.created_at.isoformat() + 'Z',
        }

    def __repr__(self):
        return f'<ChatMessage {self.id} {self.sender_type} conv={self.conversation_id}>'


class PushSubscription(db.Model):
    """En admins webb-push-prenumeration (fran mobilen/datorn). Anvands for att
    skicka en notis nar en besokare skriver. Ingen PII; bara push-endpoint +
    krypteringsnycklar som webblasaren gav oss."""
    __tablename__ = 'push_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.Text, unique=True, nullable=False)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<PushSubscription {self.id}>'
