/* 1010monky – publik chatt-widget. Självständig, inga beroenden.
   Pratar med /api/chat/send + /api/chat/poll. Besökaren får en token som
   sparas i localStorage (konversationen lever kvar mellan besök). Polling. */
(function () {
  if (window.__monkyChat) { return; }
  window.__monkyChat = true;

  var SEND = '/api/chat/send';
  var POLL = '/api/chat/poll';
  var KEY = 'monky_chat_token';
  var GREETING = 'Hej! Skriv din fråga så svarar jag så snart jag kan. Oftast inom en arbetsdag.';

  var token = '';
  try { token = localStorage.getItem(KEY) || ''; } catch (e) {}
  var open = false;
  var timer = null;
  var seen = 0;

  var css = '' +
    '.mc-btn{position:fixed;right:20px;bottom:20px;z-index:2147483000;width:58px;height:58px;border-radius:50%;border:0;cursor:pointer;background:#448C74;color:#fff;box-shadow:0 6px 20px rgba(20,23,26,.28);display:flex;align-items:center;justify-content:center;transition:transform .15s ease}' +
    '.mc-btn:hover{transform:translateY(-2px)}' +
    '.mc-btn .mc-dot{position:absolute;top:-2px;right:-2px;min-width:20px;height:20px;line-height:20px;border-radius:10px;background:#d63939;color:#fff;font-size:11px;font-weight:700;text-align:center;padding:0 5px;box-shadow:0 0 0 2px #fff}' +
    '.mc-panel{position:fixed;right:20px;bottom:88px;z-index:2147483000;width:360px;max-width:calc(100vw - 32px);height:520px;max-height:calc(100vh - 120px);background:#fff;border-radius:16px;box-shadow:0 12px 40px rgba(20,23,26,.25);display:none;flex-direction:column;overflow:hidden;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}' +
    '.mc-panel.mc-on{display:flex}' +
    '.mc-head{background:#14171a;color:#fff;padding:16px 18px;display:flex;align-items:center;gap:10px}' +
    '.mc-head .mc-av{width:36px;height:36px;border-radius:50%;background:#448C74;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px}' +
    '.mc-head h4{margin:0;font-size:15px;font-weight:600}' +
    '.mc-head p{margin:1px 0 0;font-size:11.5px;color:rgba(255,255,255,.65)}' +
    '.mc-head .mc-x{margin-left:auto;background:none;border:0;color:rgba(255,255,255,.7);cursor:pointer;font-size:20px;line-height:1;padding:4px}' +
    '.mc-msgs{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:9px;background:#f5f7fb}' +
    '.mc-m{max-width:80%;padding:9px 12px;border-radius:13px;font-size:13.5px;line-height:1.45;word-wrap:break-word}' +
    '.mc-m.v{align-self:flex-end;background:#448C74;color:#fff;border-bottom-right-radius:3px}' +
    '.mc-m.a{align-self:flex-start;background:#fff;color:#1e2633;border:1px solid #e6e7eb;border-bottom-left-radius:3px}' +
    '.mc-m .mc-t{display:block;font-size:10px;margin-top:4px;opacity:.6}' +
    '.mc-form{display:flex;gap:8px;padding:12px;border-top:1px solid #e6e7eb;background:#fff}' +
    '.mc-form input{flex:1;font:inherit;font-size:13.5px;padding:10px 12px;border:1px solid #e6e7eb;border-radius:10px;outline:none;color:#1e2633}' +
    '.mc-form input:focus{border-color:#448C74}' +
    '.mc-form button{border:0;border-radius:10px;background:#448C74;color:#fff;font-weight:600;font-size:13px;padding:0 14px;cursor:pointer}' +
    '.mc-credit{text-align:center;font-size:10px;color:#7e8896;padding:6px}';

  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  var btn = document.createElement('button');
  btn.className = 'mc-btn';
  btn.setAttribute('aria-label', 'Chatta med oss');
  btn.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.4 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8A8.4 8.4 0 0 1 12.5 3 8.4 8.4 0 0 1 21 11.5z"/></svg><span class="mc-dot" style="display:none">1</span>';

  var panel = document.createElement('div');
  panel.className = 'mc-panel';
  panel.innerHTML = '' +
    '<div class="mc-head"><div class="mc-av">10</div><div><h4>Chatta med 1010monky</h4><p>Vi svarar så snart vi kan</p></div><button class="mc-x" aria-label="Stäng">&times;</button></div>' +
    '<div class="mc-msgs" id="mc-msgs"></div>' +
    '<form class="mc-form" id="mc-form"><input id="mc-input" type="text" placeholder="Skriv ett meddelande…" autocomplete="off" maxlength="2000"><button type="submit">Skicka</button></form>' +
    '<div class="mc-credit">Drivs av 1010monky</div>';

  document.body.appendChild(panel);
  document.body.appendChild(btn);

  var msgsEl = panel.querySelector('#mc-msgs');
  var input = panel.querySelector('#mc-input');
  var dot = btn.querySelector('.mc-dot');

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function time(iso) { if (!iso) return ''; var d = new Date(iso); return d.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' }); }

  function render(messages) {
    if (!messages || !messages.length) {
      msgsEl.innerHTML = '<div class="mc-m a">' + esc(GREETING) + '</div>';
      return;
    }
    msgsEl.innerHTML = messages.map(function (m) {
      var who = m.from === 'visitor' ? 'v' : 'a';
      return '<div class="mc-m ' + who + '">' + esc(m.text) + '<span class="mc-t">' + time(m.at) + '</span></div>';
    }).join('');
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function updateDot(messages) {
    var adminCount = (messages || []).filter(function (m) { return m.from === 'admin'; }).length;
    if (!open && adminCount > seen) { dot.style.display = ''; dot.textContent = adminCount - seen; }
  }

  function poll() {
    if (!token) { return; }
    fetch(POLL + '?token=' + encodeURIComponent(token), { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (open) { render(d.messages); seen = (d.messages || []).filter(function (m) { return m.from === 'admin'; }).length; dot.style.display = 'none'; }
        else { updateDot(d.messages); }
      }).catch(function () {});
  }

  function send(text) {
    fetch(SEND, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: token, text: text, page: location.pathname }) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.token) { token = d.token; try { localStorage.setItem(KEY, token); } catch (e) {} }
        render(d.messages);
        seen = (d.messages || []).filter(function (m) { return m.from === 'admin'; }).length;
      }).catch(function () {});
  }

  function openPanel() {
    open = true; panel.classList.add('mc-on'); dot.style.display = 'none';
    if (token) { poll(); } else { render([]); }
    input.focus();
    if (!timer) { timer = setInterval(poll, 5000); }
  }
  function closePanel() { open = false; panel.classList.remove('mc-on'); }

  btn.addEventListener('click', function () { open ? closePanel() : openPanel(); });
  panel.querySelector('.mc-x').addEventListener('click', closePanel);
  panel.querySelector('#mc-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var t = input.value.trim(); if (!t) { return; }
    input.value = '';
    // optimistisk rendering
    var bubble = document.createElement('div'); bubble.className = 'mc-m v'; bubble.textContent = t; msgsEl.appendChild(bubble); msgsEl.scrollTop = msgsEl.scrollHeight;
    send(t);
  });

  // Bakgrundspoll var 25:e sek för olästa-bricka även när panelen är stängd
  setInterval(function () { if (!open && token) { poll(); } }, 25000);
})();
