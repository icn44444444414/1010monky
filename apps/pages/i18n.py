"""
Tvasprakighet (sv/fi). Svenska ligger pa roten, finska under /fi/ med egna,
sokordsvanliga slugs. En central karta kopplar ihop sv- och fi-versionen av
varje sida, sa hreflang, sprakvaxlare och routing alltid pekar ratt.

PAGES[key] = (sv-path, fi-path, mall)
"""

PAGES = {
    'home':      ('/',            '/fi',             'landing-web-studio.html'),
    'services':  ('/tjanster',    '/fi/palvelut',    'services-v1.html'),
    'pricing':   ('/priser',      '/fi/hinnasto',    'pricing.html'),
    'about':     ('/om-oss',      '/fi/meista',      'about-agency.html'),
    'portfolio': ('/portfolio',   '/fi/portfolio',   'portfolio-grid-v1.html'),
    'contact':   ('/kontakt',     '/fi/yhteystiedot','contacts-v1.html'),
    'calc':      ('/priskalkylator', '/fi/hintalaskuri','priskalkylator.html'),
    'blog':      ('/blogg',       '/fi/blogi',       None),
    'terms':     ('/villkor',     '/fi/ehdot',       'villkor.html'),
    'privacy':   ('/integritetspolicy', '/fi/tietosuoja', 'integritetspolicy.html'),
}

# Snabb uppslagning fi-path -> (key, mall)
FI_ROUTES = {fi.lstrip('/'): (key, tpl) for key, (sv, fi, tpl) in PAGES.items() if tpl}

BASE = 'https://1010monky.se'


def page_for(path):
    """Returnerar (key, lang) for en given sokvag, annars (None, 'sv'/'fi')."""
    p = path.rstrip('/') or '/'
    is_fi = p == '/fi' or p.startswith('/fi/')
    for key, (sv, fi, tpl) in PAGES.items():
        if p == sv.rstrip('/') or (sv == '/' and p == '/'):
            return key, 'fi' if is_fi else 'sv'
        if p == fi.rstrip('/'):
            return key, 'fi'
    return None, ('fi' if is_fi else 'sv')


def urls_for(path):
    """Ger (sv_url, fi_url, has_fi, lang) for sprakvaxlare + hreflang."""
    key, lang = page_for(path)
    if key:
        sv, fi, tpl = PAGES[key]
        return BASE + sv, BASE + fi, True, lang
    # Sida utan finsk tvilling: bara sv, ingen hreflang fi
    return BASE + (path.rstrip('/') or '/'), None, False, lang


# --- Chrome-oversattningar (meny, sidfot, knappar) ---
T = {
    'nav_services':   ('Tjänster', 'Palvelut'),
    'nav_portfolio':  ('Portfolio', 'Portfolio'),
    'nav_pricing':    ('Priser', 'Hinnasto'),
    'nav_about':      ('Om oss', 'Meistä'),
    'nav_blog':       ('Blogg', 'Blogi'),
    'nav_contact':    ('Kontakt', 'Yhteystiedot'),
    'home':           ('Hem', 'Etusivu'),
    'foot_tagline':   ('Liten webbstudio i Sverige och Finland – en utvecklare och en designer. WordPress och skräddarsydd kod, med fokus på tydliga och snabba webbplatser.',
                       'Pieni verkkostudio Ruotsissa ja Suomessa – yksi kehittäjä ja yksi suunnittelija. WordPress ja räätälöity koodi, selkeät ja nopeat sivustot edellä.'),
    'foot_pages':     ('Sidor', 'Sivut'),
    'foot_contact':   ('Kontakt', 'Yhteystiedot'),
    'foot_contact_us':('Kontakta oss', 'Ota yhteyttä'),
    'foot_rights':    ('Alla rättigheter förbehållna.', 'Kaikki oikeudet pidätetään.'),
    'foot_terms':     ('Villkor', 'Ehdot'),
    'foot_privacy':   ('Integritetspolicy', 'Tietosuoja'),
    'foot_cookies':   ('Cookies', 'Evästeet'),
    'start_project':  ('Starta projekt', 'Aloita projekti'),
}


def t(lang, key):
    pair = T.get(key)
    if not pair:
        return key
    return pair[1] if lang == 'fi' else pair[0]
