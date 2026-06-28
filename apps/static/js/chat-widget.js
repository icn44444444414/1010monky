/* 1010monky chatt-widget. Pratar med det sakrade /api/chat-API:t.
   Anonymt: bara meddelandet kravs. Token + senast lasta id sparas lokalt sa
   traden lever mellan sidbyten. Renderar pa sender_type -> AI-svar (bot) dyker
   upp automatiskt nar AI aktiveras serverside, utan andring har. */
(function () {
  "use strict";
  var KEY = "1010monky_chat_conversation_id";
  var READ_KEY = "1010monky_chat_last_read";
  var POLL_OPEN = 3000, POLL_CLOSED = 12000;

  var token = null, lastId = 0, lastReadId = 0, lastSender = null;
  var pollTimer = null, isOpen = false, sending = false;
  var els = {};

  function $(id) { return document.getElementById(id); }
  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

  // Lankifiera URL:er sakert (texten ar redan escapead -> ingen XSS).
  function linkify(safe) {
    return safe.replace(/(https?:\/\/[^\s<]+)/g, function (u) {
      return '<a href="' + u + '" target="_blank" rel="noopener nofollow">' + u + '</a>';
    });
  }

  function fmtTime(iso) {
    try {
      var d = iso ? new Date(iso) : new Date();
      return d.toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" });
    } catch (e) { return ""; }
  }

  function api(path, opts) {
    return fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts))
      .then(function (r) { return r.json().catch(function () { return { success: false }; }); })
      .catch(function () { return { success: false, network: true }; });
  }

  var SENDERS = { visitor: "Du", admin: "Matias", bot: "Assistent" };

  function addMessage(m, opt) {
    var type = m.sender_type;
    if (type === "system") {
      var sys = document.createElement("div");
      sys.className = "mc-bubble mc-system";
      sys.textContent = m.body;
      els.body.appendChild(sys);
      lastSender = null;
      return scroll();
    }
    var side = type === "visitor" ? "visitor" : type === "bot" ? "bot" : "admin";
    var grouped = lastSender === type;

    var row = document.createElement("div");
    row.className = "mc-row mc-row-" + (side === "visitor" ? "visitor" : "in") + (grouped ? " mc-grouped" : "");

    var col = document.createElement("div");
    col.className = "mc-col";
    var bubble = document.createElement("div");
    bubble.className = "mc-bubble mc-" + side;
    bubble.innerHTML = linkify(esc(m.body));
    col.appendChild(bubble);
    var meta = document.createElement("div");
    meta.className = "mc-meta";
    meta.textContent = (side === "visitor" ? "" : SENDERS[type] + " · ") + fmtTime(m.created_at);
    col.appendChild(meta);
    row.appendChild(col);

    els.body.appendChild(row);
    lastSender = type;
    scroll();
  }

  function scroll() { els.body.scrollTop = els.body.scrollHeight; }
  function hideIntro() { if (els.intro) els.intro.style.display = "none"; }
  function announce(t) { if (els.live) els.live.textContent = t; }

  function render(messages) {
    var gotIncoming = false;
    messages.forEach(function (m) {
      if (m.id && m.id <= lastId) return;
      if (m.id) lastId = m.id;
      addMessage(m);
      if (m.sender_type === "admin" || m.sender_type === "bot") {
        gotIncoming = true;
        announce((SENDERS[m.sender_type] || "") + " skrev: " + m.body);
      }
    });
    if (gotIncoming && !isOpen) showUnread();
  }

  function showUnread() { els.launcher.classList.add("mc-attn"); }
  function clearUnread() {
    els.launcher.classList.remove("mc-attn");
    lastReadId = lastId;
    try { localStorage.setItem(READ_KEY, String(lastReadId)); } catch (e) {}
  }

  function open() {
    isOpen = true;
    els.panel.classList.add("mc-open");
    els.launcher.classList.add("mc-hidden");
    if (window.matchMedia("(max-width: 460px)").matches) document.body.classList.add("mc-noscroll");
    clearUnread();
    setTimeout(function () { els.input.focus(); }, 50);
    schedule();
    scroll();
  }
  function close() {
    isOpen = false;
    els.panel.classList.remove("mc-open");
    els.launcher.classList.remove("mc-hidden");
    document.body.classList.remove("mc-noscroll");
    schedule();
  }

  function setSending(on) {
    sending = on;
    els.send.disabled = on;
    els.send.classList.toggle("mc-loading", on);
  }
  function updateSendState() { if (!sending) els.send.disabled = !els.input.value.trim(); }

  function sendMessage(text) {
    text = (text || "").trim();
    if (!text || sending) return;
    if (els.hp.value) return; // honeypot
    els.input.value = ""; autoGrow(); updateSendState();
    hideIntro();
    addMessage({ sender_type: "visitor", body: text, created_at: new Date().toISOString() });
    setSending(true);

    if (!token) {
      api("/api/chat/start", { method: "POST", body: JSON.stringify({
        message: text, source_page: location.pathname, website: els.hp.value
      }) }).then(function (j) {
        setSending(false);
        if (j.success && j.conversation_token) {
          token = j.conversation_token;
          // Hoppa fram forbi vart eget meddelande sa pollningen inte ekar det.
          if (j.last_id && j.last_id > lastId) lastId = j.last_id;
          try { localStorage.setItem(KEY, token); } catch (e) {}
          schedule();
        } else {
          addMessage({ sender_type: "system", body: j.network ? "Ingen anslutning. Forsok igen." : (j.error || "Nagot gick fel.") });
        }
      });
    } else {
      api("/api/chat/message", { method: "POST", body: JSON.stringify({
        conversation_token: token, message: text, website: els.hp.value
      }) }).then(function (j) {
        setSending(false);
        // Hoppa fram forbi vart eget meddelande sa pollningen inte ekar det.
        if (j.success && j.message_id && j.message_id > lastId) lastId = j.message_id;
        if (!j.success && (j.error || j.network)) {
          addMessage({ sender_type: "system", body: j.network ? "Ingen anslutning. Forsok igen." : j.error });
        }
      });
    }
  }

  function poll() {
    if (!token) return;
    api("/api/chat/messages/" + encodeURIComponent(token) + "?after_id=" + lastId)
      .then(function (j) { if (j.success && j.messages) render(j.messages); });
  }
  function schedule() {
    if (pollTimer) clearInterval(pollTimer);
    if (!token) return;
    poll();
    pollTimer = setInterval(poll, isOpen ? POLL_OPEN : POLL_CLOSED);
  }

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
    els.hint = $("mc-hint");
    els.live = $("mc-live");
    if (!els.launcher) return;

    els.launcher.addEventListener("click", open);
    if (els.hint) {
      els.hint.addEventListener("click", open);
      els.hint.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
      });
    }
    els.close.addEventListener("click", close);
    els.send.addEventListener("click", function () { sendMessage(els.input.value); });
    els.input.addEventListener("input", function () { autoGrow(); updateSendState(); });
    els.input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(els.input.value); }
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && isOpen) close(); });
    Array.prototype.forEach.call(els.panel.querySelectorAll(".mc-chip"), function (chip) {
      chip.addEventListener("click", function () { sendMessage(chip.getAttribute("data-msg") || chip.textContent); });
    });
    updateSendState();

    try {
      token = localStorage.getItem(KEY) || null;
      lastReadId = parseInt(localStorage.getItem(READ_KEY) || "0", 10) || 0;
    } catch (e) {}
    if (token) {
      hideIntro();
      // full historik forst (renderar dolt), sen markera olasta
      api("/api/chat/messages/" + encodeURIComponent(token)).then(function (j) {
        if (j.success && j.messages) {
          j.messages.forEach(function (m) {
            if (m.id) lastId = m.id;
            addMessage(m);
          });
          var unread = j.messages.some(function (m) {
            return m.id > lastReadId && (m.sender_type === "admin" || m.sender_type === "bot");
          });
          if (unread) showUnread();
        }
        schedule();
      });
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
