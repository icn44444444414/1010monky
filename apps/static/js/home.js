/* Framsidans interaktioner (vanilla, inget ramverk):
   - "Branscher & utvalda projekt": accordion som byter synkad bild
   - "Vår kompetens": slider med föregående/nästa-knappar */
(function () {
  "use strict";

  // Accordion + synkad bild
  var items = document.querySelectorAll('.ind-item');
  if (items.length) {
    Array.prototype.forEach.call(items, function (btn) {
      btn.addEventListener('click', function () {
        Array.prototype.forEach.call(items, function (b) {
          b.classList.remove('is-open');
          b.setAttribute('aria-expanded', 'false');
        });
        btn.classList.add('is-open');
        btn.setAttribute('aria-expanded', 'true');
        var target = btn.getAttribute('data-ind');
        Array.prototype.forEach.call(document.querySelectorAll('.ind-pane'), function (p) {
          p.classList.toggle('is-active', p.id === target);
        });
      });
    });
  }

  // Kompetens-slider: bläddra ett kort i taget
  var track = document.querySelector('[data-skill-track]');
  if (track) {
    var stepWidth = function () {
      var card = track.querySelector('.skill-card');
      var gap = parseInt(getComputedStyle(track).columnGap || getComputedStyle(track).gap, 10) || 16;
      return card ? card.getBoundingClientRect().width + gap : 300;
    };
    var prev = document.querySelector('[data-skill-prev]');
    var next = document.querySelector('[data-skill-next]');
    // Ingen behavior-flagga: CSS scroll-behavior:smooth sköter animationen.
    if (prev) prev.addEventListener('click', function () { track.scrollBy({ left: -stepWidth() }); });
    if (next) next.addEventListener('click', function () { track.scrollBy({ left: stepWidth() }); });
  }
})();
