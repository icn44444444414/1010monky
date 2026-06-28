/* Pris-kalkylator. Priserna ligger i config-objekten nedan – andra HAR sa
   speglar de era riktiga priser. Baspaket = exakta priser, tillval = spann. */
(function () {
  "use strict";

  var TYPES = {
    enkel:     { lo: 5000,  hi: 5000,  label: 'Enkel sida (one-page)' },
    foretag:   { lo: 12000, hi: 12000, label: 'Företagssida (4–6 sidor)' },
    premium:   { lo: 28000, hi: 28000, label: 'Premium skräddarsydd (8–12 sidor)' },
    avancerat: { lo: 45000, hi: 80000, label: 'Webbapp / avancerat' }
  };
  var ADDONS = {
    shop:      { lo: 15000, hi: 30000, label: 'Webbshop / e-handel' },
    bokning:   { lo: 8000,  hi: 20000, label: 'Bokningssystem' },
    portal:    { lo: 10000, hi: 25000, label: 'Inloggning / kundportal' },
    flersprak: { lo: 4000,  hi: 8000,  label: 'Flerspråkig (sv + fi)' },
    blogg:     { lo: 3000,  hi: 6000,  label: 'Blogg / nyheter' },
    seo:       { lo: 3000,  hi: 8000,  label: 'Fördjupad SEO' },
    copy:      { lo: 3000,  hi: 7000,  label: 'Copywriting / text' }
  };
  var CARE = {
    none:    { m: 0,    label: 'Inget' },
    basic:   { m: 690,  label: 'Care Basic' },
    growth:  { m: 1200, label: 'Care Growth' },
    premium: { m: 2000, label: 'Care Premium' }
  };

  var form = document.getElementById('calc');
  if (!form) return;
  var estEl = document.getElementById('calc-est');
  var monthlyEl = document.getElementById('calc-monthly');
  var statusEl = document.getElementById('calc-status');
  var submitBtn = document.getElementById('calc-submit');

  function kr(n) { return n.toLocaleString('sv-SE') + ' kr'; }

  function selection() {
    return {
      type: form.querySelector('input[name=type]:checked').value,
      addons: Array.prototype.map.call(form.querySelectorAll('input[name=addon]:checked'), function (i) { return i.value; }),
      care: form.querySelector('input[name=care]:checked').value
    };
  }

  function compute() {
    var s = selection();
    var lo = TYPES[s.type].lo, hi = TYPES[s.type].hi;
    s.addons.forEach(function (a) { lo += ADDONS[a].lo; hi += ADDONS[a].hi; });
    return { lo: lo, hi: hi, m: CARE[s.care].m, s: s };
  }

  function render() {
    var r = compute();
    estEl.textContent = r.lo === r.hi ? kr(r.lo) : (kr(r.lo) + ' – ' + kr(r.hi));
    monthlyEl.textContent = r.m ? ('· + ' + kr(r.m) + '/mån') : '';
    Array.prototype.forEach.call(form.querySelectorAll('.calc-opt'), function (l) {
      l.classList.toggle('is-selected', l.querySelector('input').checked);
    });
  }

  form.addEventListener('change', render);
  render();

  function status(msg, ok) {
    statusEl.style.display = 'block';
    statusEl.textContent = msg;
    statusEl.style.color = ok ? 'var(--text-secondary)' : 'var(--c-danger)';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = document.getElementById('c-name').value.trim();
    var email = document.getElementById('c-email').value.trim();
    var phone = document.getElementById('c-phone').value.trim();
    var extra = document.getElementById('c-msg').value.trim();
    var hp = form.querySelector('[name=website]').value;
    if (!name || !email) { status('Fyll i namn och e-post.', false); return; }

    var r = compute();
    var price = r.lo === r.hi ? kr(r.lo) : (kr(r.lo) + '–' + kr(r.hi));
    var msg = 'Prisförslag via kalkylatorn:\n'
      + 'Typ: ' + TYPES[r.s.type].label + '\n'
      + 'Tillval: ' + (r.s.addons.length ? r.s.addons.map(function (a) { return ADDONS[a].label; }).join(', ') : 'inga') + '\n'
      + 'Underhåll: ' + CARE[r.s.care].label + '\n'
      + 'Uppskattat: ' + price + ' ex moms' + (r.m ? (' + ' + kr(r.m) + '/mån') : '') + '\n'
      + (extra ? ('\n' + extra) : '');

    submitBtn.disabled = true;
    status('Skickar…', true);
    fetch('/api/contact', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, email: email, phone: phone, message: msg, website: hp })
    })
      .then(function (res) { return res.json(); })
      .then(function (j) {
        if (j.ok) {
          submitBtn.textContent = 'Skickat ✓';
          status('Tack! Jag återkommer med ett exakt förslag.', true);
        } else {
          submitBtn.disabled = false;
          status(j.error || 'Något gick fel. Försök igen.', false);
        }
      })
      .catch(function () { submitBtn.disabled = false; status('Ingen anslutning. Försök igen.', false); });
  });
})();
