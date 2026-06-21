(function () {
  const body = document.body;
  const nav = document.querySelector("[data-nav]");
  const toggle = document.querySelector("[data-menu-toggle]");
  const rain = document.querySelector("[data-binary-rain]");
  const bits = Array.from(document.querySelectorAll("[data-bit]"));
  const form = document.querySelector("[data-contact-form]");
  const consent = document.querySelector("[data-consent]");
  const submit = document.querySelector("[data-submit]");
  const note = document.querySelector("[data-form-note]");
  const caseButtons = document.querySelectorAll("[data-case]");

  if (rain) {
    const rows = [
      "1010101010101010",
      "0101010101010101",
      "1010101010101010",
      "0101010101010101",
      "1010101010101010",
      "0101010101010101",
      "1010101010101010",
      "0101010101010101",
      "1010101010101010"
    ];

    rain.innerHTML = rows.map((row, index) => {
      const opacity = Math.max(0.045, 0.24 - index * 0.022).toFixed(2);
      return `<span style="opacity:${opacity}">${row}</span>`;
    }).join("");
  }

  if (bits.length && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const calmPatterns = [
      "101010101010101010",
      "010101010101010101",
      "101010101010101010",
      "010101010101010101",
      "101010101010101010"
    ];
    let patternIndex = 0;

    const applyPattern = (pattern) => {
      bits.forEach((bit, index) => {
        window.setTimeout(() => {
          const value = pattern[index] || "0";
          bit.textContent = value;
          bit.classList.toggle("is-on", value === "1");
          bit.classList.toggle("is-off", value === "0");
          bit.classList.add("just-switched-on");
          window.setTimeout(() => bit.classList.remove("just-switched-on"), 900);
        }, index * 105);
      });
    };

    window.setInterval(() => {
      patternIndex = (patternIndex + 1) % calmPatterns.length;
      applyPattern(calmPatterns[patternIndex]);

      if (rain) {
        rain.querySelectorAll("span").forEach((row, index) => {
          row.style.opacity = String(Math.max(0.025, 0.105 - Math.abs((patternIndex % 3) - (index % 3)) * 0.018));
        });
      }
    }, 5200);
  }

  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = !nav.classList.contains("is-open");
      nav.classList.toggle("is-open", open);
      body.classList.toggle("menu-open", open);
      toggle.setAttribute("aria-expanded", String(open));
        toggle.setAttribute("aria-label", open ? "Stäng meny" : "Öppna meny");
    });

    nav.addEventListener("click", (event) => {
      if (event.target.matches("a")) {
        nav.classList.remove("is-open");
        body.classList.remove("menu-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Öppna meny");
      }
    });
  }

  if (consent && submit) {
    consent.addEventListener("change", () => {
      submit.disabled = !consent.checked;
    });
  }

  if (form && note) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      note.textContent = "Tack. Din förfrågan är skickad. Jag återkommer med nästa steg.";
      form.reset();
      if (submit) {
        submit.disabled = true;
      }
    });
  }

  const blogSearch = document.querySelector("[data-blog-search]");
  const blogGrid = document.querySelector("[data-blog-grid]");
  const blogEmpty = document.querySelector("[data-blog-empty]");

  if (blogSearch && blogGrid) {
    const blogCards = Array.from(blogGrid.querySelectorAll(".blog-card"));

    blogSearch.addEventListener("input", () => {
      const query = blogSearch.value.trim().toLowerCase();
      let visible = 0;

      blogCards.forEach((card) => {
        const title = (card.dataset.postTitle || card.textContent || "").toLowerCase();
        const match = title.includes(query);
        card.hidden = !match;
        if (match) visible += 1;
      });

      if (blogEmpty) {
        blogEmpty.hidden = visible !== 0;
      }
    });
  }

  caseButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const labels = {
        ghostymsg: "GhostyMsg",
        askhackers: "AskHackers",
        ai: "AI-system",
        automation: "Automation"
      };
      const label = labels[button.dataset.case] || "Case";
      button.textContent = `${label} valt`;
      window.setTimeout(() => {
        button.textContent = "Visa case";
      }, 1400);
    });
  });
})();
