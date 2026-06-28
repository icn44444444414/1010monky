/* Sidans egna interaktioner. Just nu: tillganglig mobilmeny. */
(function () {
  "use strict";
  var toggle = document.querySelector("[data-menu-toggle]");
  var nav = document.getElementById("main-nav");
  if (!toggle || !nav) return;

  function setOpen(open) {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.setAttribute("aria-label", open ? "Stäng meny" : "Öppna meny");
  }

  toggle.addEventListener("click", function () {
    setOpen(toggle.getAttribute("aria-expanded") !== "true");
  });

  // Stang nar man valjer en lank eller trycker Escape
  nav.addEventListener("click", function (e) {
    if (e.target.closest("a")) setOpen(false);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") setOpen(false);
  });
})();
