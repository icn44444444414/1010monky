"""
Mini-CRM: namngivna forfragningar (fran kontaktformular + pris-kalkylator).
Egen, fristaende del av analytics-modulen - latt att bygga vidare pa.

  create_lead()                              skapar en lead (anropas vid formularsvar)
  GET  /admin/forfragningar                  inkorg
  GET  /admin/forfragningar/<id>             detalj + status + anteckningar
  POST /admin/forfragningar/<id>/status      byt status
  POST /admin/forfragningar/<id>/note        lagg anteckning
"""
from flask import render_template, request, redirect, url_for, abort

from apps import db
from apps.analytics import blueprint
from apps.analytics.auth import admin_required
from apps.analytics.models import Lead, LeadNote, LEAD_STATUSES
from apps.chat.security import validate_csrf


def create_lead(name=None, email=None, phone=None, message=None,
                source='kontakt', service_interest=None, budget_range=None):
    """Sparar en forfragan. Anropas efter att ett formular skickats in.
    Far aldrig krascha det anropande flodet (try/except dar den anropas)."""
    lead = Lead(
        name=(name or '')[:120] or None,
        email=(email or '')[:255] or None,
        phone=(phone or '')[:60] or None,
        message=message,
        source=source[:40],
        service_interest=(service_interest or None) and service_interest[:160],
        budget_range=(budget_range or None) and budget_range[:80],
        status='ny',
    )
    db.session.add(lead)
    db.session.commit()
    return lead


@blueprint.route('/admin/forfragningar')
@admin_required
def crm_list():
    status = request.args.get('status')
    q = Lead.query
    if status in LEAD_STATUSES:
        q = q.filter_by(status=status)
    leads = q.order_by(Lead.created_at.desc()).all()
    counts = {s: Lead.query.filter_by(status=s).count() for s in LEAD_STATUSES}
    counts['all'] = Lead.query.count()
    return render_template('analytics/crm_list.html', leads=leads,
                           counts=counts, active_status=status or 'all',
                           statuses=LEAD_STATUSES)


@blueprint.route('/admin/forfragningar/<int:lead_id>')
@admin_required
def crm_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    return render_template('analytics/crm_lead.html', lead=lead, statuses=LEAD_STATUSES)


@blueprint.route('/admin/forfragningar/<int:lead_id>/status', methods=['POST'])
@admin_required
def crm_status(lead_id):
    if not validate_csrf():
        abort(400)
    lead = Lead.query.get_or_404(lead_id)
    new_status = request.form.get('status')
    if new_status not in LEAD_STATUSES:
        abort(400)
    lead.status = new_status
    db.session.commit()
    return redirect(url_for('analytics_blueprint.crm_lead', lead_id=lead.id))


@blueprint.route('/admin/forfragningar/<int:lead_id>/note', methods=['POST'])
@admin_required
def crm_note(lead_id):
    if not validate_csrf():
        abort(400)
    lead = Lead.query.get_or_404(lead_id)
    text = (request.form.get('note') or '').strip()
    if text:
        db.session.add(LeadNote(lead_id=lead.id, note=text[:2000]))
        db.session.commit()
    return redirect(url_for('analytics_blueprint.crm_lead', lead_id=lead.id))
