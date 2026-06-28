/* Prisräknare som quiz-modul.
 *
 * En enda källa: CONFIG nedan driver BÅDE vyn OCH uträkningen, så priser och
 * etiketter aldrig glider isär. Flödet är ett quiz: en fråga i taget, framåt/
 * tillbaka, och priset avslöjas på sista steget tillsammans med lead-formuläret.
 * Tvåspråkig (sv/fi). Helt fristående – montera var som helst:
 *
 *   <div data-price-calculator></div>                      (auto, språk = <html lang>)
 *   PriceCalculator.mount(el, { lang: 'fi', lead: false })  (manuellt)
 *
 * Baspaket = exakta priser, tillval och avancerat = spann. Ändra HÄR.
 */
(function (window, document) {
  "use strict";

  // --- En källa för allt: paket, tillval, underhåll ---
  var CONFIG = {
    types: [
      { key: 'enkel',     lo: 5000,  hi: 5000,
        label: { sv: 'Enkel sida',            fi: 'Yksinkertainen sivu' },
        sub:   { sv: 'One-page, 1 sida',      fi: 'Yhden sivun sivusto' } },
      { key: 'foretag',   lo: 12000, hi: 12000, popular: true,
        label: { sv: 'Företagssida',          fi: 'Yrityssivusto' },
        sub:   { sv: '4–6 sidor, WordPress',  fi: '4–6 sivua, WordPress' } },
      { key: 'premium',   lo: 28000, hi: 28000,
        label: { sv: 'Premium skräddarsydd',  fi: 'Premium, räätälöity' },
        sub:   { sv: '8–12 sidor, unik design', fi: '8–12 sivua, oma design' } },
      { key: 'avancerat', lo: 45000, hi: 80000,
        label: { sv: 'Webbapp / avancerat',   fi: 'Verkkosovellus / vaativa' },
        sub:   { sv: 'Bokning, portal, dashboard', fi: 'Varaus, portaali, hallinta' } }
    ],
    addons: [
      { key: 'shop',      lo: 15000, hi: 30000,
        label: { sv: 'Webbshop / e-handel',   fi: 'Verkkokauppa' } },
      { key: 'bokning',   lo: 8000,  hi: 20000,
        label: { sv: 'Bokningssystem',        fi: 'Varausjärjestelmä' } },
      { key: 'portal',    lo: 10000, hi: 25000,
        label: { sv: 'Inloggning / kundportal', fi: 'Kirjautuminen / asiakasportaali' } },
      { key: 'flersprak', lo: 4000,  hi: 8000,
        label: { sv: 'Flerspråkig (sv + fi)', fi: 'Monikielinen (sv + fi)' } },
      { key: 'blogg',     lo: 3000,  hi: 6000,
        label: { sv: 'Blogg / nyheter',       fi: 'Blogi / uutiset' } },
      { key: 'seo',       lo: 3000,  hi: 8000,
        label: { sv: 'Fördjupad SEO',         fi: 'Syvempi hakukoneoptimointi' } },
      { key: 'copy',      lo: 3000,  hi: 7000,
        label: { sv: 'Copywriting / text',    fi: 'Tekstien kirjoitus' } }
    ],
    care: [
      { key: 'none',    m: 0,
        label: { sv: 'Inget',         fi: 'Ei mitään' },
        sub:   { sv: 'Jag sköter det själv', fi: 'Hoidan sen itse' } },
      { key: 'basic',   m: 690,  label: { sv: 'Care Basic',   fi: 'Care Basic' } },
      { key: 'growth',  m: 1200, label: { sv: 'Care Growth',  fi: 'Care Growth' } },
      { key: 'premium', m: 2000, label: { sv: 'Care Premium', fi: 'Care Premium' } }
    ]
  };

  // Quiz-stegen (i ordning). Sista steget är resultatet.
  var STEPS = [
    { id: 'type',   group: 'types',  input: 'radio'    },
    { id: 'addons', group: 'addons', input: 'checkbox' },
    { id: 'care',   group: 'care',   input: 'radio'    }
  ];

  // --- Texter i gränssnittet ---
  var UI = {
    step_type:    { sv: 'Vilken typ av webbplats?',      fi: 'Minkä tyyppinen sivusto?' },
    step_type_h:  { sv: 'Välj det som ligger närmast – du kan ändra sen.', fi: 'Valitse lähin vaihtoehto – voit muuttaa myöhemmin.' },
    step_addons:  { sv: 'Något extra?',                  fi: 'Jotain lisää?' },
    step_addons_h:{ sv: 'Välj inget, ett eller flera.',  fi: 'Valitse ei mitään, yksi tai useampi.' },
    step_care:    { sv: 'Vill du ha månadsunderhåll?',   fi: 'Haluatko kuukausittaisen ylläpidon?' },
    step_care_h:  { sv: 'Efter lansering – helt valfritt.', fi: 'Julkaisun jälkeen – täysin vapaaehtoista.' },
    popular:      { sv: 'Populärast',                    fi: 'Suosituin' },
    step_of:      { sv: 'Steg {a} av {b}',               fi: 'Vaihe {a} / {b}' },
    back:         { sv: '← Tillbaka',                    fi: '← Takaisin' },
    next:         { sv: 'Nästa →',                       fi: 'Seuraava →' },
    show_price:   { sv: 'Visa mitt pris →',              fi: 'Näytä hintani →' },
    restart:      { sv: 'Börja om',                      fi: 'Aloita alusta' },
    modal_title:  { sv: 'Räkna ut ditt pris',            fi: 'Laske hintasi' },
    modal_close:  { sv: 'Stäng',                         fi: 'Sulje' },
    result_eyebrow:{ sv: 'Ditt prisförslag',            fi: 'Hinta-arviosi' },
    result_label: { sv: 'Ungefärligt pris',             fi: 'Arvioitu hinta' },
    est_vat:      { sv: 'ex. moms',                      fi: 'ilman alv.' },
    per_month:    { sv: '/mån',                          fi: '/kk' },
    from:         { sv: 'från ',                         fi: 'alkaen ' },
    sum_type:     { sv: 'Typ',                           fi: 'Tyyppi' },
    sum_addons:   { sv: 'Tillval',                       fi: 'Lisät' },
    sum_care:     { sv: 'Underhåll',                     fi: 'Ylläpito' },
    sum_none:     { sv: 'Inga',                          fi: 'Ei mitään' },
    lead_title:   { sv: 'Få ett exakt förslag',         fi: 'Pyydä tarkka ehdotus' },
    lead_intro:   { sv: 'Lämna dina uppgifter så återkommer jag med ett skarpt pris. Inget köp.',
                    fi: 'Jätä yhteystietosi niin palaan tarkalla hinnalla. Ei ostopakkoa.' },
    f_name:       { sv: 'Namn',                          fi: 'Nimi' },
    f_email:      { sv: 'E-post',                        fi: 'Sähköposti' },
    f_phone:      { sv: 'Telefon (valfritt)',            fi: 'Puhelin (valinnainen)' },
    f_extra:      { sv: 'Något mer jag bör veta? (valfritt)', fi: 'Jotain muuta mitä minun pitäisi tietää? (valinnainen)' },
    submit:       { sv: 'Få exakt prisförslag',          fi: 'Pyydä tarkka arvio' },
    sending:      { sv: 'Skickar…',                      fi: 'Lähetetään…' },
    sent:         { sv: 'Skickat ✓',                     fi: 'Lähetetty ✓' },
    thanks:       { sv: 'Tack! Jag återkommer med ett exakt förslag.', fi: 'Kiitos! Palaan tarkalla ehdotuksella.' },
    err_fill:     { sv: 'Fyll i namn och e-post.',       fi: 'Täytä nimi ja sähköposti.' },
    err_generic:  { sv: 'Något gick fel. Försök igen.',  fi: 'Jokin meni pieleen. Yritä uudelleen.' },
    err_conn:     { sv: 'Ingen anslutning. Försök igen.', fi: 'Ei yhteyttä. Yritä uudelleen.' }
  };

  var STYLE_ID = 'pc-style';
  var CSS =
    '.pc{--pc-accent:var(--accent,#448C74)}' +
    '.pc-head{margin-bottom:var(--space-5)}' +
    '.pc-bar{height:6px;border-radius:999px;background:rgba(0,0,0,.08);overflow:hidden}' +
    '[data-bs-theme=dark] .pc-bar,[data-theme=dark] .pc-bar{background:rgba(255,255,255,.12)}' +
    '.pc-bar-fill{height:100%;width:0;background:var(--pc-accent);border-radius:999px;transition:width .35s cubic-bezier(.4,0,.2,1)}' +
    '.pc-step-of{display:block;font-size:var(--text-sm);color:var(--text-muted);margin-top:var(--space-3)}' +
    '.pc-q{font-family:var(--font-display);font-size:var(--text-2xl);font-weight:var(--fw-bold);letter-spacing:var(--tracking-tight);margin:var(--space-2) 0 4px}' +
    '.pc-q-help{color:var(--text-secondary);margin-bottom:var(--space-5)}' +
    '.pc-step{display:none}' +
    '.pc-step.is-active{display:block;animation:pc-fade .3s ease}' +
    '@keyframes pc-fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}' +
    '.pc-nav{display:flex;justify-content:space-between;align-items:center;gap:var(--space-3);margin-top:var(--space-6)}' +
    '.pc-nav .pc-spacer{flex:1}' +
    '.pc-result-price{font-family:var(--font-display);font-size:clamp(2.4rem,7vw,3.6rem);font-weight:var(--fw-bold);letter-spacing:var(--tracking-tight);line-height:1.05;margin:4px 0}' +
    '.pc-result-note{color:var(--text-muted);font-size:var(--text-sm)}' +
    '.pc-summary{list-style:none;padding:0;margin:var(--space-5) 0 0;border-top:1px solid var(--border);}' +
    '.pc-summary li{display:flex;justify-content:space-between;gap:var(--space-4);padding:var(--space-3) 0;border-bottom:1px solid var(--border);font-size:var(--text-sm)}' +
    '.pc-summary .pc-sum-k{color:var(--text-secondary)}' +
    '.pc-summary .pc-sum-v{font-weight:var(--fw-semibold);text-align:right}' +
    '.pc-restart{background:none;border:0;color:var(--text-muted);cursor:pointer;font:inherit;font-size:var(--text-sm);text-decoration:underline;padding:0}' +
    /* Modal-lage */
    '.pc-modal{position:fixed;inset:0;z-index:1000;display:none;align-items:flex-start;justify-content:center;padding:5vh 16px;overflow-y:auto;background:rgba(20,23,26,.55);-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px)}' +
    '.pc-modal.is-open{display:flex}' +
    '.pc-modal-dialog{background:var(--surface);width:100%;max-width:660px;box-shadow:var(--shadow-xl);position:relative;animation:pc-pop .25s ease}' +
    '@keyframes pc-pop{from{opacity:0;transform:translateY(14px) scale(.98)}to{opacity:1;transform:none}}' +
    '.pc-modal-head{display:flex;align-items:center;justify-content:space-between;gap:var(--space-4);padding:var(--space-5) var(--space-5) 0}' +
    '.pc-modal-title{font-family:var(--font-display);font-weight:var(--fw-bold);font-size:var(--text-lg)}' +
    '.pc-modal-close{background:none;border:0;font-size:1.6rem;line-height:1;cursor:pointer;color:var(--text-muted);padding:2px 8px}' +
    '.pc-modal-close:hover{color:var(--text-primary)}' +
    '.pc-modal-body{padding:var(--space-5)}' +
    'body.pc-lock{overflow:hidden}';

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement('style');
    s.id = STYLE_ID; s.textContent = CSS;
    document.head.appendChild(s);
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function PriceCalculator(root, opts) {
    opts = opts || {};
    this.root = root;
    this.lang = opts.lang === 'fi' ? 'fi' : 'sv';
    this.lead = opts.lead !== false;
    this.locale = this.lang === 'fi' ? 'fi-FI' : 'sv-SE';
    this.step = 0;                 // 0..STEPS.length (sista = resultat)
    injectStyle();
    this.render();
    this.wire();
    this.go(0);
  }

  var P = PriceCalculator.prototype;

  P.t = function (key, vars) {
    var pair = UI[key], s = pair ? pair[this.lang] : key;
    if (vars) for (var k in vars) s = s.replace('{' + k + '}', vars[k]);
    return s;
  };
  P.num = function (n) { return n.toLocaleString(this.locale); };
  P.kr = function (n) { return this.num(n) + ' kr'; };
  P.find = function (key) {
    function f(g, k) { for (var i = 0; i < CONFIG[g].length; i++) if (CONFIG[g][i].key === k) return CONFIG[g][i]; }
    return f('types', key) || f('addons', key) || f('care', key);
  };

  // --- Markup ---
  P.optionHtml = function (group, o, type) {
    var lang = this.lang, name = type === 'checkbox' ? 'addon' : (group === 'types' ? 'type' : 'care');
    var checked = (group === 'types' && o.key === 'enkel') || (group === 'care' && o.key === 'none') ? ' checked' : '';
    var title = esc(o.label[lang]);
    if (o.popular) title += ' <em class="calc-tag">' + esc(this.t('popular')) + '</em>';
    var sub = o.sub ? '<span class="calc-opt-sub">' + esc(o.sub[lang]) + '</span>' : '';
    var price = '';
    if (group === 'types') price = '<span class="calc-opt-price">' + (o.lo === o.hi ? this.kr(o.lo) : this.t('from') + this.kr(o.lo)) + '</span>';
    else if (group === 'addons') price = '<span class="calc-opt-price">+' + this.num(o.lo) + '–' + this.num(o.hi) + '</span>';
    else if (o.m) price = '<span class="calc-opt-price">' + this.kr(o.m) + this.t('per_month') + '</span>';
    return '<label class="calc-opt"><input type="' + type + '" name="' + name + '" value="' + o.key + '"' + checked + '>' +
      '<span class="calc-opt-body"><span class="calc-opt-title">' + title + '</span>' + sub + price + '</span></label>';
  };

  P.stepHtml = function (def, i) {
    var self = this;
    var opts = CONFIG[def.group].map(function (o) { return self.optionHtml(def.group, o, def.input); }).join('');
    return '<div class="pc-step" data-step="' + i + '">' +
      '<h2 class="pc-q">' + esc(this.t('step_' + def.id)) + '</h2>' +
      '<p class="pc-q-help">' + esc(this.t('step_' + def.id + '_h')) + '</p>' +
      '<div class="calc-grid">' + opts + '</div>' +
    '</div>';
  };

  P.resultHtml = function () {
    var i = STEPS.length;
    var lead = this.lead ? (
      '<div class="card" style="margin-top:var(--space-6)">' +
        '<h3 class="h4" style="margin-bottom:var(--space-2)">' + esc(this.t('lead_title')) + '</h3>' +
        '<p class="text-secondary" style="margin-bottom:var(--space-5)">' + esc(this.t('lead_intro')) + '</p>' +
        '<div class="grid grid-2" style="gap:var(--space-4)">' +
          '<div class="field"><label class="label" for="pc-name">' + esc(this.t('f_name')) + '</label><input class="input" id="pc-name" name="name" required></div>' +
          '<div class="field"><label class="label" for="pc-email">' + esc(this.t('f_email')) + '</label><input class="input" id="pc-email" name="email" type="email" required></div>' +
        '</div>' +
        '<div class="field" style="margin-top:var(--space-4)"><label class="label" for="pc-phone">' + esc(this.t('f_phone')) + '</label><input class="input" id="pc-phone" name="phone" type="tel"></div>' +
        '<div class="field" style="margin-top:var(--space-4)"><label class="label" for="pc-extra">' + esc(this.t('f_extra')) + '</label><textarea class="textarea" id="pc-extra" name="extra" rows="3"></textarea></div>' +
        '<input type="text" name="website" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true">' +
        '<div style="margin-top:var(--space-5)"><button class="btn btn-primary btn-lg" type="submit" data-pc-submit>' + esc(this.t('submit')) + '</button></div>' +
        '<p data-pc-status class="text-secondary" style="margin-top:var(--space-4);display:none"></p>' +
      '</div>'
    ) : '';
    return '<div class="pc-step" data-step="' + i + '">' +
      '<span class="eyebrow">' + esc(this.t('result_eyebrow')) + '</span>' +
      '<div class="calc-estimate" style="margin-top:var(--space-3)"><div>' +
        '<span class="calc-est-label">' + esc(this.t('result_label')) + '</span>' +
        '<span class="pc-result-price" data-pc-value></span>' +
        '<span class="pc-result-note">' + esc(this.t('est_vat')) + ' <span data-pc-monthly></span></span>' +
      '</div></div>' +
      '<ul class="pc-summary" data-pc-summary></ul>' +
      lead +
    '</div>';
  };

  P.render = function () {
    this.root.classList.add('pc');
    var steps = '';
    for (var i = 0; i < STEPS.length; i++) steps += this.stepHtml(STEPS[i], i);
    this.root.innerHTML =
      '<form data-pc-form novalidate>' +
        '<div class="pc-head">' +
          '<div class="pc-bar"><div class="pc-bar-fill" data-pc-fill></div></div>' +
          '<span class="pc-step-of" data-pc-stepof></span>' +
        '</div>' +
        steps +
        this.resultHtml() +
        '<div class="pc-nav">' +
          '<button type="button" class="btn btn-ghost" data-pc-back>' + esc(this.t('back')) + '</button>' +
          '<span class="pc-spacer"></span>' +
          '<button type="button" class="btn btn-primary" data-pc-next>' + esc(this.t('next')) + '</button>' +
        '</div>' +
      '</form>';

    this.form = this.root.querySelector('[data-pc-form]');
    this.fill = this.root.querySelector('[data-pc-fill]');
    this.stepOf = this.root.querySelector('[data-pc-stepof]');
    this.backBtn = this.root.querySelector('[data-pc-back]');
    this.nextBtn = this.root.querySelector('[data-pc-next]');
    this.panels = this.root.querySelectorAll('.pc-step');
    this.valueEl = this.root.querySelector('[data-pc-value]');
    this.monthlyEl = this.root.querySelector('[data-pc-monthly]');
    this.summaryEl = this.root.querySelector('[data-pc-summary]');
  };

  // --- Beräkning ---
  P.selection = function () {
    var f = this.form;
    return {
      type: f.querySelector('input[name=type]:checked').value,
      addons: Array.prototype.map.call(f.querySelectorAll('input[name=addon]:checked'), function (i) { return i.value; }),
      care: f.querySelector('input[name=care]:checked').value
    };
  };
  P.compute = function () {
    var self = this, sel = this.selection(), t = this.find(sel.type), lo = t.lo, hi = t.hi;
    sel.addons.forEach(function (a) { var o = self.find(a); lo += o.lo; hi += o.hi; });
    return { lo: lo, hi: hi, m: this.find(sel.care).m, sel: sel };
  };
  P.priceText = function (r) { return r.lo === r.hi ? this.kr(r.lo) : (this.kr(r.lo) + ' – ' + this.kr(r.hi)); };

  // --- Navigering ---
  P.go = function (n) {
    var last = STEPS.length;
    this.step = Math.max(0, Math.min(last, n));
    for (var i = 0; i < this.panels.length; i++) this.panels[i].classList.toggle('is-active', i === this.step);
    this.markSelected();

    var atResult = this.step === last;
    // Progress: frågorna fyller baren, resultatet = 100%
    var ratio = atResult ? 1 : (this.step / last);
    this.fill.style.width = Math.round(ratio * 100) + '%';
    this.stepOf.textContent = atResult ? '' : this.t('step_of', { a: this.step + 1, b: last });

    this.backBtn.style.visibility = this.step === 0 ? 'hidden' : 'visible';
    this.nextBtn.style.display = atResult ? 'none' : '';
    // Sista frågan: knappen avslöjar priset
    this.nextBtn.textContent = this.step === last - 1 ? this.t('show_price') : this.t('next');

    if (atResult) this.showResult();
  };

  P.markSelected = function () {
    Array.prototype.forEach.call(this.form.querySelectorAll('.calc-opt'), function (l) {
      l.classList.toggle('is-selected', l.querySelector('input').checked);
    });
  };

  P.showResult = function () {
    var r = this.compute();
    this.valueEl.textContent = this.priceText(r);
    this.monthlyEl.textContent = r.m ? ('· + ' + this.kr(r.m) + this.t('per_month')) : '';
    var t = this.find(r.sel.type);
    var addons = r.sel.addons.length
      ? r.sel.addons.map(this.find.bind(this)).map(function (o) { return o.label[this.lang]; }, this).join(', ')
      : this.t('sum_none');
    var care = this.find(r.sel.care).label[this.lang];
    this.summaryEl.innerHTML =
      '<li><span class="pc-sum-k">' + esc(this.t('sum_type')) + '</span><span class="pc-sum-v">' + esc(t.label[this.lang]) + '</span></li>' +
      '<li><span class="pc-sum-k">' + esc(this.t('sum_addons')) + '</span><span class="pc-sum-v">' + esc(addons) + '</span></li>' +
      '<li><span class="pc-sum-k">' + esc(this.t('sum_care')) + '</span><span class="pc-sum-v">' + esc(care) + '</span></li>';
  };

  // Sammanfattning till mejlet – alltid svenska (det är inkorgen som läser)
  P.mailSummary = function (r) {
    var t = this.find(r.sel.type);
    var addons = r.sel.addons.length ? r.sel.addons.map(this.find).map(function (o) { return o.label.sv; }).join(', ') : 'inga';
    var price = r.lo === r.hi ? this.num(r.lo) + ' kr' : (this.num(r.lo) + '–' + this.num(r.hi) + ' kr');
    return 'Prisförslag via kalkylatorn:\n' +
      'Typ: ' + t.label.sv + '\n' +
      'Tillval: ' + addons + '\n' +
      'Underhåll: ' + this.find(r.sel.care).label.sv + '\n' +
      'Uppskattat: ' + price + ' ex moms' + (r.m ? (' + ' + this.num(r.m) + ' kr/mån') : '');
  };

  P.status = function (msg, ok) {
    if (!this.statusEl) return;
    this.statusEl.style.display = 'block';
    this.statusEl.textContent = msg;
    this.statusEl.style.color = ok ? 'var(--text-secondary)' : 'var(--c-danger)';
  };

  P.wire = function () {
    var self = this, last = STEPS.length;

    this.nextBtn.addEventListener('click', function () { self.go(self.step + 1); });
    this.backBtn.addEventListener('click', function () { self.go(self.step - 1); });

    // Enkelval (radio) känns som quiz: hoppa fram automatiskt efter val
    this.form.addEventListener('change', function (e) {
      self.markSelected();
      var input = e.target;
      if (input && input.type === 'radio' && self.step < last) {
        setTimeout(function () { self.go(self.step + 1); }, 260);
      }
    });

    if (!this.lead) return;
    this.statusEl = this.root.querySelector('[data-pc-status]');
    this.submitBtn = this.root.querySelector('[data-pc-submit]');

    this.form.addEventListener('submit', function (e) {
      e.preventDefault();
      var get = function (n) { var el = self.form.querySelector('[name=' + n + ']'); return el ? el.value.trim() : ''; };
      var name = get('name'), email = get('email');
      if (!name || !email) { self.status(self.t('err_fill'), false); return; }
      var r = self.compute(), extra = get('extra');
      var msg = self.mailSummary(r) + (extra ? ('\n\n' + extra) : '');
      self.submitBtn.disabled = true;
      self.status(self.t('sending'), true);
      fetch('/api/contact', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, email: email, phone: get('phone'), message: msg, website: get('website') })
      })
        .then(function (res) { return res.json(); })
        .then(function (j) {
          if (j.ok) { self.submitBtn.textContent = self.t('sent'); self.status(self.t('thanks'), true); }
          else { self.submitBtn.disabled = false; self.status(j.error || self.t('err_generic'), false); }
        })
        .catch(function () { self.submitBtn.disabled = false; self.status(self.t('err_conn'), false); });
    });
  };

  function docLang() { return (document.documentElement.getAttribute('lang') || 'sv').slice(0, 2); }

  // Oppna quizen i en modal (overlay). Frasch instans varje gang.
  function openModal(opts) {
    opts = opts || {};
    injectStyle();
    var lang = opts.lang === 'fi' ? 'fi' : (opts.lang || docLang());
    var tr = function (k) { var p = UI[k]; return p ? p[lang === 'fi' ? 'fi' : 'sv'] : k; };

    var modal = document.createElement('div');
    modal.className = 'pc-modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.innerHTML =
      '<div class="pc-modal-dialog">' +
        '<div class="pc-modal-head">' +
          '<span class="pc-modal-title">' + esc(tr('modal_title')) + '</span>' +
          '<button type="button" class="pc-modal-close" aria-label="' + esc(tr('modal_close')) + '">&times;</button>' +
        '</div>' +
        '<div class="pc-modal-body"><div class="pc-mount"></div></div>' +
      '</div>';
    document.body.appendChild(modal);
    document.body.classList.add('pc-lock');
    new PriceCalculator(modal.querySelector('.pc-mount'), { lang: lang, lead: true });
    // Visa direkt (ingen rAF - den fyrar inte i bakgrundsflikar). Dialogens
    // entré-animation (pc-pop) spelas ändå när den ritas ut.
    modal.classList.add('is-open');

    function close() {
      modal.classList.remove('is-open');
      document.body.classList.remove('pc-lock');
      document.removeEventListener('keydown', onKey);
      setTimeout(function () { if (modal.parentNode) modal.parentNode.removeChild(modal); }, 220);
    }
    function onKey(e) { if (e.key === 'Escape') close(); }
    modal.querySelector('.pc-modal-close').addEventListener('click', close);
    modal.addEventListener('click', function (e) { if (e.target === modal) close(); });
    document.addEventListener('keydown', onKey);
    return { close: close };
  }

  // Publikt API
  var api = {
    config: CONFIG,
    mount: function (el, opts) { return new PriceCalculator(el, opts); },
    openModal: openModal
  };

  function boot() {
    var lang = docLang();
    // Inbäddade kalkylatorer (t.ex. /priskalkylator-sidan)
    Array.prototype.forEach.call(document.querySelectorAll('[data-price-calculator]'), function (el) {
      if (el.dataset.pcMounted) return;
      el.dataset.pcMounted = '1';
      api.mount(el, { lang: el.getAttribute('data-lang') || lang, lead: el.getAttribute('data-lead') !== 'false' });
    });
    // Knappar som öppnar quizen i en modal: [data-price-calculator-open]
    document.addEventListener('click', function (e) {
      var btn = e.target.closest ? e.target.closest('[data-price-calculator-open]') : null;
      if (!btn) return;
      e.preventDefault();
      openModal({ lang: btn.getAttribute('data-lang') || docLang() });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  window.PriceCalculator = api;
})(window, document);
