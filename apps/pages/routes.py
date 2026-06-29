import os
import ssl
import smtplib
import hmac
from functools import wraps
from email.message import EmailMessage

from apps.pages import blueprint
from flask import render_template, request, jsonify, Response, redirect, session
from jinja2 import TemplateNotFound

# Losenord for sidor under arbete (styleguide m.m.). Satt i .env pa servern.
WIP_PASSWORD = os.getenv('WIP_PASSWORD', 'monky-wip-2026')


def wip_unlocked():
    """Sant om besokaren last upp WIP-laget (via session eller Basic Auth)."""
    if session.get('wip_unlocked'):
        return True
    auth = request.authorization
    return bool(auth and hmac.compare_digest(auth.password or '', WIP_PASSWORD))


def wip_protected(view):
    """Grind for sidor som inte ska visas for kund an. En lyckad inloggning
    sparas i sessionen sa man slipper forlita sig pa att webblasaren skickar
    Basic Auth-headern vidare till alla sokvagar."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not wip_unlocked():
            return Response(
                'Inloggning kravs.', 401,
                {'WWW-Authenticate': 'Basic realm="1010monky under arbete"'})
        session['wip_unlocked'] = True
        return view(*args, **kwargs)
    return wrapper

SITE_URL = 'https://1010monky.se'

# Indexerbara sidor for sitemap (utan tema-skrap/felsidor/tom blogg)
SITEMAP_PATHS = [
    ('/', '1.0'),
    ('/tjanster', '0.9'),
    ('/priser', '0.9'),
    ('/priskalkylator', '0.8'),
    ('/tjanster/wordpress-hemsida', '0.8'),
    ('/blogg', '0.6'),
    ('/blogg/professionell-hemsida-vad-ingar', '0.6'),
    ('/portfolio', '0.7'),
    ('/portfolio/ghostymsg', '0.6'),
    ('/portfolio/askhackers', '0.6'),
    ('/om-oss', '0.6'),
    ('/kontakt', '0.8'),
    ('/villkor', '0.3'),
    ('/integritetspolicy', '0.3'),
    # Finska versioner (sv/fi kopplas via hreflang i sidhuvudet)
    ('/fi', '0.9'),
    ('/fi/palvelut', '0.8'),
    ('/fi/palvelut/wordpress-sivusto', '0.8'),
    ('/fi/hinnasto', '0.8'),
    ('/fi/hintalaskuri', '0.7'),
    ('/fi/portfolio', '0.6'),
    ('/fi/meista', '0.5'),
    ('/fi/yhteystiedot', '0.7'),
    ('/fi/ehdot', '0.3'),
    ('/fi/tietosuoja', '0.3'),
    # Endast publicerade vanilla-blogginlagg ligger i sitemap.
]

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


@blueprint.route('/blogg')
def blog_index():
    return render_template('pages/blog-grid.html', segment='blog')


BLOG_POSTS = {
    'professionell-hemsida-vad-ingar': 'professionell-hemsida-vad-ingar.html',
}


@blueprint.route('/blogg/<slug>')
def blog_post(slug):
    tpl = BLOG_POSTS.get(slug)
    if not tpl:
        return render_template('pages/error-404.html'), 404
    return render_template('pages/blog/' + tpl, segment='blog')


@blueprint.route('/robots.txt')
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    return Response(body, mimetype='text/plain')


@blueprint.route('/sitemap.xml')
def sitemap_xml():
    urls = "".join(
        f"  <url><loc>{SITE_URL}{path}</loc><priority>{prio}</priority></url>\n"
        for path, prio in SITEMAP_PATHS
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}"
        "</urlset>\n"
    )
    return Response(xml, mimetype='application/xml')


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

    # Spara som forfragan i mini-CRM (far aldrig stoppa kontaktflodet)
    try:
        from apps.analytics.crm import create_lead
        src = 'kalkylator' if message.startswith('Prisförslag via kalkylatorn') else 'kontakt'
        create_lead(name=name, email=email, phone=phone, message=message, source=src,
                    service_interest=(', '.join(services) if services else None))
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


@blueprint.route('/bygg')
@wip_protected
def bygg():
    # Upplasningsdorr under under-byggnad-laget: lyckad inloggning -> hela sajten.
    return redirect('/')


from apps.pages.i18n import urls_for, t as _t, FI_ROUTES, PAGES


@blueprint.app_context_processor
def inject_i18n():
    """Ger alla mallar: lang, sv_url, fi_url, has_fi, tr() och nav_url()."""
    sv_url, fi_url, has_fi, lang = urls_for(request.path)

    def nav_url(key):
        sv, fi, tpl = PAGES.get(key, ('/', '/fi', None))
        return fi if lang == 'fi' else sv

    return {'lang': lang, 'sv_url': sv_url, 'fi_url': fi_url, 'has_fi': has_fi,
            'tr': (lambda k: _t(lang, k)), 'nav_url': nav_url}


@blueprint.route('/fi')
def fi_home():
    return render_template('pages/landing-web-studio.html', segment='index')


@blueprint.route('/fi/<path:sub>')
def fi_page(sub):
    entry = FI_ROUTES.get('fi/' + sub)
    if entry:
        key, tpl = entry
        return render_template('pages/' + tpl, segment=key)
    if sub == 'blogi':
        return render_template('pages/blog-grid.html', segment='blog')
    return render_template('pages/error-404.html'), 404


@blueprint.route('/styleguide')
@wip_protected
def styleguide():
    return render_template('pages/styleguide.html', segment='styleguide')


# --- Rena, sokordsvanliga URL:er (SEO) -> samma mallar som forr ---
CLEAN_ROUTES = {
    '/tjanster':              ('services-v1.html', 'services'),
    '/priser':                ('pricing.html', 'pricing'),
    '/portfolio':             ('portfolio-grid-v1.html', 'portfolio'),
    '/portfolio/ghostymsg':   ('portfolio-single-v1.html', 'portfolio'),
    '/portfolio/askhackers':  ('portfolio-single-askhackers.html', 'portfolio'),
    '/kontakt':               ('contacts-v1.html', 'contact'),
    '/om-oss':                ('about-agency.html', 'about'),
    '/tjanster/wordpress-hemsida': ('services/wordpress-hemsida.html', 'services'),
}
# Gamla tema-slugs -> ny ren URL (301, behaller lankkraften)
LEGACY_REDIRECTS = {
    '/services-v1': '/tjanster',
    '/pricing': '/priser',
    '/portfolio-grid-v1': '/portfolio',
    '/portfolio-single-v1': '/portfolio/ghostymsg',
    '/portfolio-single-askhackers': '/portfolio/askhackers',
    '/contacts-v1': '/kontakt',
    '/about-agency': '/om-oss',
}


def _clean_view(tpl, segment):
    return render_template('pages/' + tpl, segment=segment)


for _url, (_tpl, _seg) in CLEAN_ROUTES.items():
    blueprint.add_url_rule(
        _url, 'clean_' + _tpl.replace('.html', '').replace('-', '_').replace('/', '_'),
        (lambda t=_tpl, s=_seg: _clean_view(t, s)))


@blueprint.route('/<template>')
def route_template(template):

    # 301 fran gamla tema-slugs (/services-v1 osv) till de rena URL:erna
    legacy = LEGACY_REDIRECTS.get('/' + template)
    if legacy:
        return redirect(legacy, code=301)

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
