// learning/static/js/pronunciation.js
// Browser-only speaking practice using the Web Speech API (Chrome/Edge).
// No cloud keys needed. Scores are heuristic and saved to the backend.

(function ensureCSRF() {
  if (typeof window.getCSRFToken !== "function") {
    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== "") {
        for (const c of document.cookie.split(";")) {
          const cookie = c.trim();
          if (cookie.substring(0, name.length + 1) === name + "=") {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }
    window.getCSRFToken = function () {
      return getCookie("csrftoken") ||
        (document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "");
    };
  }
})();

const PRONUN_LANG_KEY = "pronunLang";
const SUPPORTED_LANGS = ["es-ES", "es-MX", "es-AR"]; // tweak as you prefer

function getSavedLang() {
  const saved = localStorage.getItem(PRONUN_LANG_KEY);
  return SUPPORTED_LANGS.includes(saved) ? saved : "es-ES";
}
function setSavedLang(lang) {
  if (SUPPORTED_LANGS.includes(lang)) localStorage.setItem(PRONUN_LANG_KEY, lang);
}

function normalizeText(s) {
  return (s || "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // strip accents
    .toLowerCase()
    .replace(/[^a-záéíóúñãẽĩõũ’' ]/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}
function levenshteinRatio(a, b) {
  a = normalizeText(a); b = normalizeText(b);
  if (!a && !b) return 100; if (!a || !b) return 0;
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost);
    }
  }
  const dist = dp[m][n];
  return Math.max(0, Math.min(100, 100 * (1 - dist / Math.max(m, n))));
}
function completenessScore(hyp, ref) {
  const r = normalizeText(ref).split(" ").filter(Boolean);
  const hset = new Set(normalizeText(hyp).split(" ").filter(Boolean));
  if (!r.length) return 100;
  let hit = 0; r.forEach(w => { if (hset.has(w)) hit++; });
  return (hit / r.length) * 100;
}

function updateUI(id, acc, flu, comp) {
  const elA = document.getElementById(`acc-${id}`);
  const elF = document.getElementById(`flu-${id}`);
  const elC = document.getElementById(`comp-${id}`);
  const bar = document.getElementById(`bar-${id}`);
  if (elA) elA.textContent = acc.toFixed(1);
  if (elF) elF.textContent = flu.toFixed(1);
  if (elC) elC.textContent = comp.toFixed(1);
  const overall = (acc + flu + comp) / 3;
  if (bar) bar.style.width = `${overall.toFixed(0)}%`;
}

async function persistAttempt(id, referenceText, acc, flu, comp) {
  try {
    await fetch("/learning/api/pronunciation/attempt/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
      credentials: "same-origin",
      body: JSON.stringify({
        exercise_id: parseInt(id),
        expected_text: referenceText,
        accuracy_score: acc,
        fluency_score: flu,
        completeness_score: comp,
        prosody_score: 0
      })
    });
  } catch (e) {
    console.warn("Persist attempt failed", e);
  }
}

// Map of exerciseId -> { rec, startAt, lastFinal, interim }
const active = {};

function getLangFor(exerciseId) {
  // if there's a select on this card, use it; else use saved
  const sel = document.getElementById(`lang-${exerciseId}`);
  const val = sel?.value || getSavedLang();
  setSavedLang(val);
  return val;
}

window.startPronunciation = function (exerciseId, referenceText) {
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Rec) {
    alert("Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge.");
    return;
  }
  if (active[exerciseId]?.rec) return; // already running

  const rec = new Rec();
  rec.lang = getLangFor(exerciseId);
  rec.interimResults = true;
  rec.continuous = true;

  const tStart = Date.now();
  let lastFinal = "";
  let lastInterim = "";

  const transcriptEl = document.getElementById(`live-${exerciseId}`);
  if (transcriptEl) { transcriptEl.textContent = ""; transcriptEl.classList.add("listening"); }

  rec.onresult = async (event) => {
    lastInterim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i];
      if (res.isFinal) lastFinal += " " + res[0].transcript;
      else lastInterim += res[0].transcript;
    }
    const spoken = (lastFinal + " " + lastInterim).trim();
    if (transcriptEl) transcriptEl.textContent = spoken;

    if (!spoken) return;

    // Live scoring (non-final will bounce a bit, that’s fine)
    const acc = levenshteinRatio(spoken, referenceText);
    const comp = completenessScore(spoken, referenceText);
    // Fluency proxy: combine accuracy with pace (char/time)
    const secs = Math.max(1, (Date.now() - tStart) / 1000);
    const pace = Math.min(1, normalizeText(spoken).length / Math.max(10, normalizeText(referenceText).length));
    const flu = Math.max(0, Math.min(100, acc * 0.6 + pace * 40));
    updateUI(exerciseId, acc, flu, comp);

    // Save only on final chunks (to avoid spamming)
    if (event.results[event.results.length - 1].isFinal) {
      await persistAttempt(exerciseId, referenceText, acc, flu, comp);
    }
  };

  rec.onerror = (e) => {
    console.warn("Speech error:", e?.error);
    if (transcriptEl) transcriptEl.classList.remove("listening");
  };
  rec.onend = () => {
    if (transcriptEl) transcriptEl.classList.remove("listening");
    active[exerciseId] = null;
  };

  active[exerciseId] = { rec, startAt: tStart, lastFinal, lastInterim };
  rec.start();
};

window.stopPronunciation = function (exerciseId) {
  const handle = active[exerciseId];
  if (handle?.rec) {
    try {
      handle.rec.stop();
    } catch (_) {}
    active[exerciseId] = null;
  }
};