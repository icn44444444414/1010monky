/* 1010monky chatt-widget. Pratar med det sakrade /api/chat-API:t.
   Anonymt: bara meddelandet kravs. Token sparas lokalt sa traden lever
   mellan sidbyten. Renderar pa sender_type -> AI-svar (bot) dyker upp
   automatiskt nar AI aktiveras serverside, utan andring har. */
(function () {
  "use strict";
  var KEY = "1010monky_chat_conversation_id";
  var token = null, lastId = 0, pollTimer = null, started = false;

  var els = {};
  function $(id) { return document.getElementById(id); }

  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

  function api(path, opts) {
    return fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts))
      .then(function (r) { return r.json().catch(function () { return { success: false }; }); });
  }

  function open() {
    els.panel.classList.add("mc-open");
    els.launcher.classList.add("mc-hidden");
    els.input.focus();
    if (token) startPolling();
  }
  function close() {
    els.panel.classList.remove("mc-open");
    els.launcher.classList.remove("mc-hidden");
    stopPolling();
  }

  function addBubble(m) {
    var wrap = document.createElement("div");
    if (m.sender_type === "system") {
      wrap.className = "mc-bubble mc-system";
      wrap.textContent = m.body;
    } else {
      wrap.className = "mc-bubble mc-" + (m.sender_type === "visitor" ? "visitor" : m.sender_type === "bot" ? "bot" : "admin");
      wrap.innerHTML = esc(m.body);
    }
    els.body.appendChild(wrap);
    els.body.scrollTop = els.body.scrollHeight;
  }

  function render(messages) {
    messages.forEach(function (m) {
      if (m.id && m.id <= lastId) return;
      if (m.id) lastId = m.id;
      addBubble(m);
    });
  }

  function hideIntro() { if (els.intro) els.intro.style.display = "none"; }

  function sendMessage(text) {
    text = (text || "").trim();
    if (!text) return;
    if (els.hp.value) return; // honeypot ifyllt -> tyst
    els.input.value = "";
    autoGrow();

    if (!token) {
      // forsta meddelandet -> starta konversation
      addBubble({ sender_type: "visitor", body: text });
      hideIntro();
      api("/api/chat/start", { method: "POST", body: JSON.stringify({
        message: text, source_page: location.pathname, website: els.hp.value
      }) }).then(function (j) {
        if (j.success && j.conversation_token) {
          token = j.conversation_token;
          try { localStorage.setItem(KEY, token); } catch (e) {}
          started = true;
          startPolling();
        } else {
          addBubble({ sender_type: "system", body: j.error || "Nagot gick fel. Forsok igen." });
        }
      });
    } else {
      addBubble({ sender_type: "visitor", body: text });
      api("/api/chat/message", { method: "POST", body: JSON.stringify({
        conversation_token: token, message: text, website: els.hp.value
      }) }).then(function (j) {
        if (!j.success && j.error) addBubble({ sender_type: "system", body: j.error });
      });
    }
  }

  function poll() {
    if (!token) return;
    api("/api/chat/messages/" + encodeURIComponent(token) + "?after_id=" + lastId)
      .then(function (j) { if (j.success && j.messages) render(j.messages); });
  }
  function startPolling() {
    if (pollTimer) return;
    poll();
    pollTimer = setInterval(poll, 3000);
  }
  function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  function autoGrow() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 110) + "px";
  }

  function init() {
    els.launcher = $("monky-chat-launcher");
    els.panel = $("monky-chat-panel");
    els.body = $("mc-body");
    els.input = $("mc-input");
    els.send = $("mc-send");
    els.close = $("mc-close");
    els.intro = $("mc-intro");
    els.hp = $("mc-hp");
    if (!els.launcher) return;

    els.hint = $("mc-hint");
    els.launcher.addEventListener("click", open);
    if (els.hint) {
      els.hint.addEventListener("click", open);
      els.hint.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
      });
    }
    els.close.addEventListener("click", close);
    els.send.addEventListener("click", function () { sendMessage(els.input.value); });
    els.input.addEventListener("input", autoGrow);
    els.input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(els.input.value); }
    });
    Array.prototype.forEach.call(document.querySelectorAll("#monky-chat-panel .mc-chip"), function (chip) {
      chip.addEventListener("click", function () { sendMessage(chip.getAttribute("data-msg") || chip.textContent); });
    });

    // aterstall tidigare konversation
    try { token = localStorage.getItem(KEY) || null; } catch (e) {}
    if (token) { hideIntro(); poll(); }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
