"""
Admin-/backend-vy for chatten.

Skyddad med ett enkelt sessionsbaserat losenord (env ADMIN_PASSWORD, default
ett dev-losenord). Inget anvandarregister behovs for en enmansbyra - en
losenordsgrind racker for MVP. Skarps vid behov senare.

Routes:
  GET  /admin/login              inloggningsformular
  POST /admin/login              logga in
  GET  /admin/logout             logga ut
  GET  /admin/chat               inbox (lista konversationer)
  GET  /admin/chat/<id>          en trad + svarsfalt
  POST /admin/chat/<id>/reply    svara som admin
  POST /admin/chat/<id>/status   byt status (open/closed/spam/new)
"""
from functools import wraps

from flask import (render_template, request, redirect, url_for,
                   session, abort, flash)

from apps import db
from apps.chat import blueprint
from apps.chat.models import ChatConversation, ChatMessage, CONV_STATUSES
from apps.chat.security import (
    verify_admin_password, rate_limit, validate_csrf, client_ip, log_suspicious,
)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('chat_admin'):
            return redirect(url_for('chat_blueprint.admin_login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ---- Auth ----

@blueprint.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        # Brute force-skydd: max 8 forsok per IP och 10 minuter.
        if not rate_limit(f'login:{client_ip()}', 8, 600):
            log_suspicious('login_throttle')
            flash('For manga forsok. Vanta nagra minuter.', 'danger')
            return render_template('chat/admin_login.html'), 429

        if verify_admin_password(request.form.get('password')):
            # Forhindra session fixation: nollstall innan vi satter admin-flagga.
            session.clear()
            session['chat_admin'] = True
            session.permanent = True
            nxt = request.args.get('next') or url_for('chat_blueprint.admin_inbox')
            # Oppen-redirect-skydd: bara interna sokvagar tillats.
            if not (nxt.startswith('/') and not nxt.startswith('//')):
                nxt = url_for('chat_blueprint.admin_inbox')
            return redirect(nxt)

        log_suspicious('login_fail')
        flash('Fel losenord.', 'danger')
    return render_template('chat/admin_login.html')


@blueprint.route('/admin/logout')
def admin_logout():
    session.pop('chat_admin', None)
    return redirect(url_for('chat_blueprint.admin_login'))


# ---- Inbox ----

@blueprint.route('/admin/chat')
@admin_required
def admin_inbox():
    status = request.args.get('status')
    q = ChatConversation.query
    if status in CONV_STATUSES:
        q = q.filter_by(status=status)
    conversations = q.order_by(ChatConversation.updated_at.desc()).all()

    counts = {s: ChatConversation.query.filter_by(status=s).count()
              for s in CONV_STATUSES}
    counts['all'] = ChatConversation.query.count()

    return render_template('chat/admin_inbox.html',
                           conversations=conversations,
                           counts=counts,
                           active_status=status or 'all')


# ---- En trad ----

@blueprint.route('/admin/chat/<int:conversation_id>')
@admin_required
def admin_thread(conversation_id):
    conv = ChatConversation.query.get_or_404(conversation_id)
    # Markera besoksmeddelanden som lasta nar admin oppnar traden.
    changed = False
    for m in conv.messages:
        if m.sender_type == 'visitor' and not m.is_read:
            m.is_read = True
            changed = True
    if changed:
        db.session.commit()
    return render_template('chat/admin_thread.html',
                           conv=conv, statuses=CONV_STATUSES)


@blueprint.route('/admin/chat/<int:conversation_id>/reply', methods=['POST'])
@admin_required
def admin_reply(conversation_id):
    if not validate_csrf():
        abort(400)
    conv = ChatConversation.query.get_or_404(conversation_id)
    body = (request.form.get('body') or '').strip()
    if body:
        db.session.add(ChatMessage(conversation_id=conv.id,
                                   sender_type='admin', body=body, is_read=True))
        conv.touch()
        if conv.status == 'new':
            conv.status = 'open'
        db.session.commit()
    return redirect(url_for('chat_blueprint.admin_thread',
                            conversation_id=conv.id))


@blueprint.route('/admin/chat/<int:conversation_id>/status', methods=['POST'])
@admin_required
def admin_status(conversation_id):
    if not validate_csrf():
        abort(400)
    conv = ChatConversation.query.get_or_404(conversation_id)
    new_status = request.form.get('status')
    if new_status not in CONV_STATUSES:
        abort(400)
    conv.status = new_status
    conv.touch()
    db.session.commit()
    return redirect(url_for('chat_blueprint.admin_thread',
                            conversation_id=conv.id))
