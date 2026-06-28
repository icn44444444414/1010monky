/* 1010monky analytics + cookie-samtycke (Live Analytics Light).
   Inget laddas eller spars forran besokaren valt "Tillat statistik".
   Anonymt: en token i localStorage, ingen PII. */
(function () {
  "use strict";
  var CONSENT_KEY = "1010monky_consent";
  var TOKEN_KEY = "1010monky_analytics_token";
  var banner = document.getElementById("cookie-consent");

  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  function showBanner() { if (banner) banner.hidden = false; }
  function hideBanner() { if (banner) banner.hidden = true; }

  function setConsent(value) {
    set(CONSENT_KEY, value);
    hideBanner();
    if (value === "granted") enable();
  }

  // Lat sidfoten oppna samtycket igen (aterkalleligt)
  window.monkyOpenConsent = showBanner;

  if (banner) {
    var allow = banner.querySelector("[data-consent-allow]");
    var deny = banner.querySelector("[data-consent-deny]");
    if (allow) allow.addEventListener("click", function () { setConsent("granted"); });
    if (deny) deny.addEventListener("click", function () { setConsent("denied"); });
  }

  var consent = get(CONSENT_KEY);
  if (consent === "granted") enable();
  else if (consent !== "denied") showBanner();

  function enable() { loadGA(); startTracking(); }

  // ---- Google Analytics (laddas forst efter samtycke) ----
  function loadGA() {
    var id = window.MONKY_GA_ID;
    if (!id || window.__monkyGA) return;
    window.__monkyGA = true;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + id;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", id);
  }

  // ---- Egen anonym spårning ----
  var token = get(TOKEN_KEY);
  var started = false;

  function send(type, extra) {
    var body = { type: type, url: location.pathname, consent: true, token: token };
    if (extra) for (var k in extra) body[k] = extra[k];
    fetch("/api/analytics/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      keepalive: true
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.token && j.token !== token) { token = j.token; set(TOKEN_KEY, token); }
      })
      .catch(function () {});
  }

  function startTracking() {
    if (started) return;
    started = true;

    send("pageview", { title: document.title.slice(0, 120) });

    // Klick pa knappar/lankar (fangar CTA + chatt-oppning via aria-label)
    document.addEventListener("click", function (e) {
      var el = e.target.closest("a, button, [role=button]");
      if (!el) return;
      var text = (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 80);
      if (text) send("click", { text: text });
    }, true);

    // Scroll-djup 25/50/75/100 %
    var marks = [25, 50, 75, 100], hit = {};
    window.addEventListener("scroll", function () {
      var doc = document.documentElement;
      var height = doc.scrollHeight - window.innerHeight;
      if (height <= 0) return;
      var pct = (window.scrollY / height) * 100;
      for (var i = 0; i < marks.length; i++) {
        var m = marks[i];
        if (pct >= m && !hit[m]) { hit[m] = 1; send("scroll", { value: String(m) }); }
      }
    }, { passive: true });

    // Formulär: forsta tangenttryck + skickat
    var formStarted = false;
    document.addEventListener("input", function (e) {
      if (!formStarted && e.target.closest("form")) { formStarted = true; send("form_start"); }
    }, true);
    document.addEventListener("submit", function () { send("form_submit"); }, true);
  }
})();
