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

  // Gauge
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
  // refresh current view
  if (currentCard) {
    const front = document.getElementById("front");
    const back = document.getElementById("back");
    front.textContent = reverseMode ? currentCard.back_gn : currentCard.front_es;
    back.textContent  = reverseMode ? currentCard.front_es : (currentCard.back_gn || "(sin respuesta)");
    back.style.display = "none";
    document.getElementById("grades").style.display = "none";
  }
};

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
  await srsNext();
}

async function srsNext() {
  const front = document.getElementById("front");
  const back = document.getElementById("back");
  const notes = document.getElementById("notes");
  const grades = document.getElementById("grades");
  try {
    const r = await fetch("/learning/api/srs/next/", {
      method: "POST",
      headers: { "X-CSRFToken": getCSRFToken(), "Accept": "application/json" },
      credentials: "same-origin"
    });
    if (!r.ok) {
      front.textContent = `Error ${r.status}. ¿Sesión iniciada?`;
      [back, notes, grades].forEach(el => el && (el.style.display = "none"));
      return;
    }
    const ct = r.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      front.textContent = "Respuesta no válida. Recarga la página e inicia sesión de nuevo.";
      [back, notes, grades].forEach(el => el && (el.style.display = "none"));
      return;
    }
    const data = await r.json();

    // Update state counters (e.g., when a new card is shown)
    await loadSrsState();

    if (!data.card) {
      if (data.reason === "new_cap_reached") {
        front.textContent = "Límite diario de nuevas tarjetas alcanzado. Vuelve mañana o cambia el modo.";
      } else {
        front.textContent = "No hay tarjetas pendientes. Agrega palabras al Glosario y vuelve a sincronizar.";
      }
      [back, notes, grades].forEach(el => el && (el.style.display = "none"));
      currentCard = null;
      return;
    }
    currentCard = data.card;
    front.textContent = reverseMode ? currentCard.back_gn : currentCard.front_es;
    back.textContent  = reverseMode ? currentCard.front_es : (currentCard.back_gn || "(sin respuesta)");
    notes.textContent = currentCard.notes ? "Notas: " + currentCard.notes : "";
    back.style.display = "none";
    notes.style.display = currentCard.notes ? "block" : "none";
    grades.style.display = "none";
  } catch (e) {
    console.error("SRS next error:", e);
    front.textContent = "No se pudo cargar. Revisa tu conexión o vuelve a iniciar sesión.";
    [back, notes, grades].forEach(el => el && (el.style.display = "none"));
  }
}

function srsShow() {
  if (!currentCard) return;
  document.getElementById("back").style.display = "block";
  document.getElementById("grades").style.display = "block";
}

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
    await resp.json().catch(()=> ({}));
    if (score >= 5) confetti();
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

if (resp.ok) {
  const data = await resp.json().catch(()=> ({}));
  if (data.interval_days != null) {
    const msg = `Próxima en ${data.interval_days} día(s)`;
    toast(score >= 5 ? "¡Perfecto! " + msg : msg, score >= 5 ? "good" : "");
  }
}