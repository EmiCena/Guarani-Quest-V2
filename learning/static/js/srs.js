// learning/static/js/srs.js

// --- CSRF fallback ---
(function(){
  if (typeof window.getCSRFToken !== 'function') {
    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        for (const c of document.cookie.split(';')) {
          const cookie = c.trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }
    window.getCSRFToken = function () {
      return getCookie('csrftoken') ||
             (document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '');
    };
  }
})();

// --- State ---
let currentCard = null;
let reverseMode = false;
let srsState = {
  mode: "comfortable",
  new_limit: 15,
  new_shown_today: 0,
  allowed_new_today: 0,
  due_review_count: 0,
  new_available_count: 0
};

// --- UI helpers ---
function updateModeButtons() {
  ["beginner", "comfortable", "aggressive"].forEach(m => {
    const btn = document.getElementById(`mode-${m}`);
    if (!btn) return;
    btn.classList.toggle("active", srsState.mode === m);
  });
  const nc = document.getElementById("new-count");
  const nl = document.getElementById("new-limit");
  const dc = document.getElementById("due-count");
  if (nc) nc.textContent = srsState.new_shown_today ?? 0;
  if (nl) nl.textContent = srsState.new_limit ?? 0;
  if (dc) dc.textContent = srsState.due_review_count ?? 0;

  const gauge = document.getElementById("gauge");
  const text  = document.getElementById("gauge-text");
  const limit = srsState.new_limit || 1;
  const pct = Math.min(100, Math.round((srsState.new_shown_today / limit) * 100));
  if (gauge) gauge.style.setProperty("--val", pct);
  if (text)  text.textContent = pct + "%";
}

async function loadSrsState() {
  try {
    const r = await fetch("/learning/api/srs/state/", {
      method: "GET",
      headers: {"Accept": "application/json"},
      credentials: "same-origin"
    });
    if (r.ok) {
      const data = await r.json();
      srsState = Object.assign(srsState, data);
      updateModeButtons();
    }
  } catch (_) {}
}

window.setMode = async function(mode) {
  try {
    const r = await fetch("/learning/api/srs/set-mode/", {
      method: "POST",
      headers: {
        "Content-Type":"application/json",
        "X-CSRFToken": getCSRFToken(),
        "Accept": "application/json"
      },
      credentials: "same-origin",
      body: JSON.stringify({ mode })
    });
    if (r.ok) {
      const data = await r.json();
      srsState = Object.assign(srsState, data);
      updateModeButtons();
    } else {
      alert("No se pudo cambiar el modo.");
    }
  } catch (e) { console.error(e); }
};

window.toggleReverse = function() {
  reverseMode = !reverseMode;
  if (currentCard) {
    const front = document.getElementById("front");
    const back = document.getElementById("back");
    front.textContent = reverseMode ? currentCard.back_gn : currentCard.front_es;
    back.textContent  = reverseMode ? currentCard.front_es : (currentCard.back_gn || "(sin respuesta)");
    hideBack(); // vuelve al frente
  }
};

function showBack() {
  const flipCard = document.getElementById("flip-card");
  const grades = document.getElementById("grades");
  if (flipCard) flipCard.classList.add("flipped");
  if (grades) grades.style.display = "block";
}
function hideBack() {
  const flipCard = document.getElementById("flip-card");
  const grades = document.getElementById("grades");
  if (flipCard) flipCard.classList.remove("flipped");
  if (grades) grades.style.display = "none";
}

// --- SRS flow ---
async function srsInit() {
  await loadSrsState();
  try {
    const r = await fetch("/learning/api/srs/sync/", {
      method: "POST",
      headers: { "X-CSRFToken": getCSRFToken(), "Accept": "application/json" },
      credentials: "same-origin"
    });
    if (!r.ok) console.warn("SRS sync status:", r.status);
  } catch (e) { console.error("SRS sync error:", e); }

  // Click en la tarjeta = voltear
  const flipInner = document.getElementById("flip-inner");
  if (flipInner) {
    flipInner.addEventListener("click", (e) => {
      // los botones internos usan stopPropagation();
      srsShow();
    });
  }

  await srsNext();
}

async function srsNext() {
  const front = document.getElementById("front");
  const back = document.getElementById("back");
  const notes = document.getElementById("notes");

  try {
    const r = await fetch("/learning/api/srs/next/", {
      method: "POST",
      headers: { "X-CSRFToken": getCSRFToken(), "Accept": "application/json" },
      credentials: "same-origin"
    });
    if (!r.ok) {
      if (front) front.textContent = `Error ${r.status}. ¿Sesión iniciada?`;
      hideBack();
      return;
    }
    const ct = r.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      if (front) front.textContent = "Respuesta no válida. Recarga e inicia sesión de nuevo.";
      hideBack();
      return;
    }
    const data = await r.json();

    // Update counters (por si mostramos nueva tarjeta)
    await loadSrsState();

    if (!data.card) {
      if (data.reason === "new_cap_reached") {
        if (front) front.textContent = "Límite diario de nuevas tarjetas alcanzado. Vuelve mañana o cambia el modo.";
      } else {
        if (front) front.textContent = "No hay tarjetas pendientes. Agrega palabras al Glosario y vuelve a sincronizar.";
      }
      if (back) back.textContent = "";
      if (notes) notes.style.display = "none";
      hideBack();
      currentCard = null;
      return;
    }

    currentCard = data.card;
    if (front) front.textContent = reverseMode ? currentCard.back_gn : currentCard.front_es;
    if (back)  back.textContent  = reverseMode ? currentCard.front_es : (currentCard.back_gn || "(sin respuesta)");
    if (notes) {
      notes.textContent = currentCard.notes ? "Notas: " + currentCard.notes : "";
      notes.style.display = currentCard.notes ? "block" : "none";
    }
    hideBack(); // empezamos mostrando el frente

  } catch (e) {
    console.error("SRS next error:", e);
    if (front) front.textContent = "No se pudo cargar. Revisa conexión o inicia sesión.";
    if (back) back.textContent = "";
    if (notes) notes.style.display = "none";
    hideBack();
  }
}

function srsShow() { showBack(); }

function confetti() {
  const colors = ["#7c3aed","#06b6d4","#22d3ee","#a78bfa","#10b981","#f59e0b","#ef4444"];
  for (let i=0;i<80;i++) {
    const d = document.createElement("div");
    d.className = "confetti-piece";
    d.style.left = (Math.random()*100) + "vw";
    d.style.background = colors[Math.floor(Math.random()*colors.length)];
    d.style.transform = `translateY(-20vh) rotate(${Math.random()*360}deg)`;
    d.style.animationDelay = (Math.random()*0.2)+"s";
    document.body.appendChild(d);
    setTimeout(()=> d.remove(), 1500);
  }
}

async function srsGrade(score) {
  if (!currentCard) return;
  try {
    const resp = await fetch("/learning/api/srs/grade/", {
      method: "POST",
      headers: {
        "Content-Type":"application/json",
        "X-CSRFToken": getCSRFToken(),
        "Accept": "application/json"
      },
      credentials: "same-origin",
      body: JSON.stringify({ card_id: currentCard.id, rating: score })
    });

    let data = {};
    try { data = await resp.json(); } catch(_) {}

    if (score >= 5) confetti();

    if (data && data.interval_days != null) {
      const msg = `Próxima en ${data.interval_days} día(s)`;
      toast(score >= 5 ? "¡Perfecto! " + msg : msg, score >= 5 ? "good" : "");
    }

    // Notificar mascota si está disponible
    if (typeof window.updateMascotFromRating === "function") {
      window.updateMascotFromRating(score);
    }

  } catch (e) {
    console.error("SRS grade error:", e);
  }
  await srsNext();
}

function srsSkip() { srsNext(); }

// --- Keyboard shortcuts ---
document.addEventListener("keydown", (e) => {
  const tag = (e.target && e.target.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea") return;

  if (e.code === "Space") { e.preventDefault(); srsShow(); }
  if ("012345".includes(e.key)) { srsGrade(parseInt(e.key, 10)); }
  if (e.key === "n" || e.key === "Enter") { srsSkip(); }
});

function toast(msg, kind="") {
  const c = document.getElementById("toasts"); if (!c) return;
  const d = document.createElement("div");
  d.className = "toast " + kind;
  d.textContent = msg;
  c.appendChild(d);
  setTimeout(()=> d.remove(), 2200);
}

// --- TTS helpers (frente/dorso) ---
function srsSpeakFront(){
  if (!window.ttsSpeak || !currentCard) return;
  const text = document.getElementById("front")?.textContent?.trim() || "";
  const lang = reverseMode ? "gn" : "es"; // en inverso, el frente es guaraní
  if (text) window.ttsSpeak(text, lang);
}
function srsSpeakBack(){
  if (!window.ttsSpeak || !currentCard) return;
  const text = document.getElementById("back")?.textContent?.trim() || "";
  const lang = reverseMode ? "es" : "gn"; // en normal, el dorso es guaraní
  if (text) window.ttsSpeak(text, lang);
}

// --- Expose globally for inline handlers ---
if (typeof window !== "undefined") {
  window.srsInit = srsInit;
  window.srsShow = srsShow;
  window.srsGrade = srsGrade;
  window.srsSkip = srsSkip;
  window.srsSpeakFront = srsSpeakFront;
  window.srsSpeakBack = srsSpeakBack;
}