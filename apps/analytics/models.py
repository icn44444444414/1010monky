"""
Databasmodeller for analytics (Live Analytics Light).

Anonymt i grunden: en besokare = ett ogissningsbart session_token, ingen PII,
ingen ra IP. Enhet harleds serverside. lead_score forbereds men fylls i ett
senare steg. Allt bakom cookie-samtycke (consent_analytics).
"""
import secrets
from datetime import datetime
from apps import db


EVENT_TYPES = ('pageview', 'click', 'scroll', 'chat_open',
               'form_open', 'form_start', 'form_submit')


def _new_token():
    return secrets.token_urlsafe(16)


class VisitorSession(db.Model):
    __tablename__ = 'visitor_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_token = db.Column(db.String(40), unique=True, index=True,
                              nullable=False, default=_new_token)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow, nullable=False, index=True)
    source = db.Column(db.String(255))        # landningens referrer
    device = db.Column(db.String(20))         # mobil / dator / surfplatta
    browser = db.Column(db.String(60))
    country = db.Column(db.String(8))         # ungefarlig, valfri
    consent_analytics = db.Column(db.Boolean, default=False, nullable=False)
    lead_score = db.Column(db.Integer, default=0, nullable=False)

    events = db.relationship('VisitorEvent', backref='session',
                             order_by='VisitorEvent.created_at',
                             cascade='all, delete-orphan', lazy='select')

    @property
    def current_page(self):
        for e in reversed(self.events):
            if e.event_type == 'pageview':
                return e.page_url
        return None

    @property
    def page_flow(self):
        # Unika sidor i besoksordning (Startsida -> Tjanster -> Kontakt)
        flow = []
        for e in self.events:
            if e.event_type == 'pageview' and (not flow or flow[-1] != e.page_url):
                flow.append(e.page_url)
        return flow

    @property
    def last_action(self):
        return self.events[-1] if self.events else None


LEAD_STATUSES = ('ny', 'kontaktad', 'offert', 'vunnen', 'forlorad')
LEAD_STATUS_LABEL = {'ny': 'Ny', 'kontaktad': 'Kontaktad', 'offert': 'Offert skickad',
                     'vunnen': 'Vunnen', 'forlorad': 'Förlorad'}
LEAD_STATUS_CLS = {'ny': 'green', 'kontaktad': 'blue', 'offert': 'amber',
                   'vunnen': 'teal', 'forlorad': 'gray'}


class Lead(db.Model):
    """En namngiven forfragan (kontaktformular eller pris-kalkylator)."""
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(60))
    service_interest = db.Column(db.String(160))
    budget_range = db.Column(db.String(80))
    message = db.Column(db.Text)
    source = db.Column(db.String(40), default='kontakt')   # kontakt / kalkylator
    lead_score = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default='ny', nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    notes = db.relationship('LeadNote', backref='lead',
                            order_by='LeadNote.created_at.desc()',
                            cascade='all, delete-orphan', lazy='select')

    @property
    def status_label(self):
        return LEAD_STATUS_LABEL.get(self.status, self.status)

    @property
    def status_cls(self):
        return LEAD_STATUS_CLS.get(self.status, 'gray')


class LeadNote(db.Model):
    __tablename__ = 'lead_notes'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id', ondelete='CASCADE'),
                        nullable=False, index=True)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class VisitorEvent(db.Model):
    __tablename__ = 'visitor_events'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer,
                           db.ForeignKey('visitor_sessions.id', ondelete='CASCADE'),
                           nullable=False, index=True)
    event_type = db.Column(db.String(40), nullable=False)
    page_url = db.Column(db.String(255))
    element_text = db.Column(db.String(200))
    value = db.Column(db.String(60))          # t.ex. scroll-djup "75"
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
