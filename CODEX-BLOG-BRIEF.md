# Blogg-brief för Codex (senior skribent + SEO)

Skriven av Claude åt Matias. Mål: bloggtexter som rankar på Google OCH konverterar
småföretagare i Sverige/Finland till kunder hos 1010monky. Köpintention först,
inte trafik för trafikens skull.

## Roll
Agera som senior content-skribent + SEO-copywriter med 25 års erfarenhet. Research
varje ämne på nätet och backa påståenden med **riktiga, aktuella (2026) siffror och
källor** — gör texten mer användbar än konkurrenternas (konkreta tal, exempel,
prisspann, Matias egen erfarenhet). Hitta ALDRIG på statistik; länka/citera riktiga
källor (Google Search Central, PTS/IMY, branschundersökningar). Lova inte resultat.

## Röst (ABSOLUT ingen AI-känsla — viktigast av allt)
Matias skriver i **första person, vardaglig svenska**. Härma hans befintliga inlägg.
- INGA tankstreck (—), inga utropstecken, ingen marknadsförings-floskel.
- Inga "vi är stolta / grymt / älskar / Omöjligt? Vi fixar det".
- Inte AI-strukturen med massa fet-punktlistor. Korta, ärliga stycken. Konkret.
- Referera hans riktiga projekt ärligt: **GhostyMsg = Node.js (INTE Flask/Python)**,
  AskHackers = Flask/Python. Skriv aldrig att GhostyMsg är byggt i Python.
- Skriv som en hantverkare som förklarar, inte som en säljare. Matias läser igenom
  och justerar till sist, så håll det nära hans ton.

## Format (sajten är BOOTSTRAP-FRI nu)
- Nya inlägg ska vara **vanilla**: `{% extends 'layouts/clean.html' %}`, använd
  designsystemet (`.container`, `.section`, `.prose`, `.eyebrow`, `.lead`, `.btn`).
- Använd INTE `layouts/base.html` (det är gamla Bootstrap-temat).
- 1 `<h1>`, sedan `<h2>/<h3>`. Avsluta med en FAQ + en CTA till `/kontakt`.
- Bloggen är just nu "under byggnad" (routen `/blogg/<slug>` visar under-byggnad-
  sidan för ALLA slugs). Skriv inläggen färdiga; av-grindning + listning är ett
  separat steg vi koordinerar när 2–3 inlägg är klara.

## SEO per inlägg
- 1 primärt sökord + 2–3 sekundära. Bestäm sökintention (info / jämförelse / köp / lokal).
- `<title>` under 60 tecken (suffixet `| 1010monky` läggs på automatiskt i layouten).
- meta description ~150–155 tecken, en pitch (inte torr beskrivning).
- Intern länkning med beskrivande ankartext till de RENA URL:erna (nya, live):
  `/tjanster`, `/priser`, `/kontakt`, `/portfolio`, och ett case
  (`/portfolio/ghostymsg` eller `/portfolio/askhackers`) där det passar.
- Lägg `BlogPosting` + `FAQPage` JSON-LD (FAQ:n måste matcha synligt innehåll).
- Ren slug, t.ex. `/blogg/professionell-hemsida-vad-ingar`.

## Planen (rekommendation)
Skapa hellre **en i taget med hög kvalitet** än 4 på en gång (batch = AI-känsla).
Börja med de två högsta köpintention-ämnena nedan, pausa och låt Matias läsa, fortsätt.

**Ta bort dessa 6 (svagast köpintention / generiska / drar DIY-folk):**
`tillganglighet-ar-lag`, `farg-och-typografi`, `hero-sektion-som-konverterar`,
`misstag-i-kontaktformular`, `chatt-app-python-flask`, `tappar-besokare-tre-sekunder`.

**Behåll dessa 6 (starkast köp/lokal/unikt):**
`vad-kostar-en-webbplats`, `wordpress-eller-skraddarsytt`, `lokal-seo-smaforetag`,
`chatt-app-pris`, `fran-besokare-till-kund`, `snabb-mobilsajt`.
(De är fortfarande Bootstrap — konvertera till vanilla när bloggen ska av-grindas.)

## Ämnen att skriva (köpintention, fyller luckor som de behållna inte täcker)
1. **"Vad ingår i en professionell hemsida?"** — kw: *professionell hemsida*. Intent: köp/beslut.
   Vinkel: vad du faktiskt får, billig vs proffsig, vad som kostar och varför. Länk → /priser, /tjanster.
2. **"Behöver mitt företag en ny hemsida?"** — kw: *ny hemsida företag*. Intent: medvetenhet → beslut.
   Vinkel: konkreta tecken (långsam, ej mobilanpassad, syns inte i Google, ser gammal ut). Länk → /tjanster, /kontakt.
3. **"Vad kan ett litet företag automatisera?"** — kw: *automation småföretag*. Intent: info → kommersiell.
   Vinkel: hans automation-tjänst, konkreta exempel (formulär→CRM, påminnelser, bokning). Låg konkurrens.
4. **"WordPress eller Wix för företag?"** — kw: *wordpress eller wix*. Intent: jämförelse. Hög volym.

Rekommenderad start: #1 och #2 (högst köpintention), en i taget.

## Arbetsordning (koordinering med Claude)
- Jobba på egen branch, t.ex. `codex/blog`. Rör bara `apps/templates/pages/blog/*`
  (och ev. `blog-grid.html` om listningen ska byggas). 
- Rör INTE Claudes SEO-/strukturfiler: `apps/pages/i18n.py`, `apps/pages/routes.py`
  (URL-routing/redirects), `apps/templates/layouts/clean.html`.
- Pusha ofta, små commits, tydliga meddelanden. Pull senaste main före merge.
