/* ============================================================
   1010monky — scroll-reveal + grön scroll-progress (KIKAB-stil)
   Opt-in via .reveal-ready på <html> så sidan funkar utan JS.
   ============================================================ */
(function () {
  "use strict";

  var root = document.documentElement;
  root.classList.add("reveal-ready");

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var els = [];

  function mark(el) {
    if (el && !el.classList.contains("monky-reveal")) {
      el.classList.add("monky-reveal");
      els.push(el);
    }
  }

  // Fristående sektionsrubriker (inte de som ligger i ett grid – dem sköter kolumnen)
  document.querySelectorAll("main h1, main h2").forEach(function (h) {
    if (h.closest(".swiper, .navbar, footer, .modal, .row")) return;
    mark(h);
  });

  // Grid-kolumner: avslöja en i taget, staggrade per rad
  document.querySelectorAll("main .row").forEach(function (row) {
    if (row.closest(".swiper, .navbar, footer")) return;
    var i = 0;
    Array.prototype.forEach.call(row.children, function (col) {
      if (col.nodeType !== 1) return;
      if (col.closest(".swiper")) return;
      col.style.setProperty("--reveal-delay", (i % 6) * 70 + "ms");
      mark(col);
      i++;
    });
  });

  if (reduced || !("IntersectionObserver" in window)) {
    els.forEach(function (el) { el.classList.add("is-visible"); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("is-visible");
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.12 });
    els.forEach(function (el) { io.observe(el); });
  }

  // Grön scroll-progress längst upp
  var bar = document.createElement("div");
  bar.className = "scroll-progress";
  bar.setAttribute("aria-hidden", "true");
  document.body.appendChild(bar);

  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      var y = window.scrollY || window.pageYOffset;
      var docH = document.documentElement.scrollHeight - window.innerHeight;
      var ratio = docH > 0 ? Math.min(y / docH, 1) : 0;
      bar.style.transform = "scaleX(" + ratio + ")";
      ticking = false;
    });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  onScroll();
})();
