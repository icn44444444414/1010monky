import os
import ssl
import smtplib
from email.message import EmailMessage

from apps.pages import blueprint
from flask import render_template, request, jsonify
from jinja2 import TemplateNotFound

CONTACT_TO = os.getenv('CONTACT_TO', 'info@1010monky.se')
CONTACT_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'contact_submissions.log')
# Autentiserad SMTP (sätts i .env när vi valt sändmetod: Gmail app-lösenord, Zoho Mail Lite, Brevo, ...)
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
SMTP_FROM = os.getenv('SMTP_FROM') or SMTP_USER or CONTACT_TO


@blueprint.route('/')
def index():

    return render_template('pages/landing-web-studio.html', segment='index')


@blueprint.route('/api/contact', methods=['POST'])
def api_contact():
    data = request.form if request.form else (request.get_json(silent=True) or {})

    def field(key):
        return (data.get(key) or '').strip()

    # Honeypot: bots fyller i det dolda faltet -> latsas att det gick bra
    if field('website'):
        return jsonify(ok=True)

    name = field('name')
    email = field('email')
    phone = field('phone')
    company = field('company')
    message = field('message')
    try:
        services = data.getlist('services')
    except Exception:
        services = data.get('services') or []

    if not name or not email or not message:
        return jsonify(ok=False, error='Fyll i namn, e-post och meddelande.'), 400

    body = (
        "Nytt meddelande fran kontaktformularet pa 1010monky.se\n\n"
        f"Namn: {name}\n"
        f"E-post: {email}\n"
        f"Telefon: {phone or '-'}\n"
        f"Foretag: {company or '-'}\n"
        f"Tjanster: {', '.join(services) if services else '-'}\n\n"
        "Meddelande:\n"
        f"{message}\n"
    )

    # Backup: spara alltid lokalt sa inget tappas
    try:
        with open(CONTACT_LOG, 'a', encoding='utf-8') as fh:
            fh.write(body + "\n----------------------------------------\n")
    except Exception:
        pass

    # Ingen autentiserad SMTP konfigurerad an -> meddelandet ar sparat i loggen ovan
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        return jsonify(ok=True)

    msg = EmailMessage()
    msg['Subject'] = f'Webbforfragan fran {name}'
    msg['From'] = f'1010monky webb <{SMTP_FROM}>'
    msg['To'] = CONTACT_TO
    msg['Reply-To'] = email
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        return jsonify(ok=True)
    except Exception:
        return jsonify(ok=False, error='Kunde inte skicka just nu, forsok igen eller mejla info@1010monky.se.'), 500


@blueprint.route('/<template>')
def route_template(template):

    try:

        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/pages/FILE.html
        return render_template("pages/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('pages/error-404.html'), 404

    except:
        return render_template('pages/error-500.html'), 500


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
