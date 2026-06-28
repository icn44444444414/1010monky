"""
Lead score. Raknar fram hur "het" en besokare ar utifran beteende.
Poangen lagras pa VisitorSession.lead_score och raknas om vid varje event.

Vikter (ur roadmappen, lite utbyggt):
  startsida +1, tjanstesida +5, prissida +10, portfolio +3, kontaktsida +8,
  bloggsida +2, djup scroll (>=75%) +3, kontakt-CTA-klick +20, oppnade chatten
  +25, borjade formular +5, skickade formular +50, aterbesok (annan dag) +15.
Maxas till 100 sa /100-visningen stammer.
"""
CONTACT_WORDS = ('offert', 'kontakt', 'boka', 'ring', 'prata med matias', 'begär')
CHAT_WORDS = ('chatta med', 'öppna chatten', 'chatt')


def score_session(s):
    pages = set()
    contact_click = chat = form_start = form_submit = deep_scroll = False

    for e in s.events:
        if e.event_type == 'pageview' and e.page_url:
            pages.add(e.page_url)
        elif e.event_type == 'click':
            t = (e.element_text or '').lower()
            if any(w in t for w in CHAT_WORDS):
                chat = True
            elif any(w in t for w in CONTACT_WORDS):
                contact_click = True
        elif e.event_type == 'chat_open':
            chat = True
        elif e.event_type == 'form_start':
            form_start = True
        elif e.event_type == 'form_submit':
            form_submit = True
        elif e.event_type == 'scroll':
            try:
                if int(e.value or 0) >= 75:
                    deep_scroll = True
            except (TypeError, ValueError):
                pass

    score = 0
    for p in pages:
        if p == '/':
            score += 1
        elif p.startswith('/services'):
            score += 5
        elif p == '/pricing':
            score += 10
        elif p.startswith('/portfolio'):
            score += 3
        elif p.startswith('/contacts'):
            score += 8
        elif p.startswith('/blogg'):
            score += 2

    if deep_scroll:
        score += 3
    if contact_click:
        score += 20
    if chat:
        score += 25
    if form_start:
        score += 5
    if form_submit:
        score += 50
    if s.first_seen and s.last_seen and s.last_seen.date() != s.first_seen.date():
        score += 15

    return min(score, 100)


def status_label(score):
    if score >= 70:
        return ('Het', 'red')
    if score >= 40:
        return ('Intresserad', 'amber')
    if score >= 15:
        return ('Nyfiken', 'blue')
    return ('Ny', 'gray')
