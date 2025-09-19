// learning/static/js/glossary.js
async function translateAndAdd() {
  const el = document.getElementById("gloss-source");
  const text = el.value.trim();
  if (!text) { alert("Ingresa un texto en español"); return; }

  try {
    const resp = await fetch("/learning/api/translate-and-add/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
      body: JSON.stringify({ source_text_es: text })
    });

    // If server rejected, fallback to manual prompt
    if (!resp.ok) {
      return await manualPromptAndAdd(text);
    }

    const data = await resp.json();

    // If the server signals fallback, prompt manual
    if (data.fallback) {
      return await manualPromptAndAdd(text);
    }

    // Success path: translation returned and saved
    addGlossaryListItem(text, data.translated_text_gn);
    el.value = "";
  } catch (e) {
    // Network or JSON parse issue -> manual fallback
    await manualPromptAndAdd(text);
  }
}

async function manualPromptAndAdd(textEs) {
  const manual = prompt("No se pudo traducir automáticamente.\nIngresa la traducción en guaraní para:\n\n" + textEs);
  if (!manual || !manual.trim()) return;
  const gn = manual.trim();

  const resp = await fetch("/learning/api/glossary/add/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
    body: JSON.stringify({ source_text_es: textEs, translated_text_gn: gn, notes: "" })
  });
  if (resp.ok) {
    addGlossaryListItem(textEs, gn);
    const el = document.getElementById("gloss-source");
    if (el) el.value = "";
  } else {
    alert("No se pudo guardar la entrada.");
  }
}

function addGlossaryListItem(es, gn) {
  const list = document.getElementById("glossary-list");
  if (!list) return;
  const li = document.createElement("li");
  li.innerHTML = `<strong>${es}</strong> → ${gn}`;
  list.prepend(li);
}

// Existing helpers for exercises (unchanged)
window.submitFillBlank = async function (id) {
  const root = document.getElementById(`fillblank-${id}`);
  const input = root.querySelector("input[name='answer']");
  const answer = input.value.trim();
  const resp = await fetch("/learning/api/exercises/fillblank/", {
    method: "POST",
    headers: {"Content-Type":"application/json","X-CSRFToken": getCSRFToken()},
    body: JSON.stringify({ exercise_id: id, answer })
  });
  const data = await resp.json();
  root.querySelector(".feedback").innerHTML = `Puntaje: ${data.score.toFixed(1)}% ${data.is_correct ? "✅" : "❌"}`;
}

window.submitMCQ = async function (id) {
  const root = document.getElementById(`mcq-${id}`);
  const selected = root.querySelector(`input[name='mcq-${id}']:checked`);
  if (!selected) { alert("Selecciona una opción"); return; }
  const resp = await fetch("/learning/api/exercises/mcq/", {
    method: "POST",
    headers: {"Content-Type":"application/json","X-CSRFToken": getCSRFToken()},
    body: JSON.stringify({ exercise_id: id, selected_key: selected.value })
  });
  const data = await resp.json();
  root.querySelector(".feedback").innerHTML = `Puntaje: ${data.score.toFixed(1)}% ${data.is_correct ? "✅" : "❌"}`;
}

window.submitMatching = async function (id) {
  const root = document.getElementById(`matching-${id}`);
  const selects = root.querySelectorAll("select.match-right");
  const pairs = [];
  selects.forEach(s => {
    pairs.push({ left: s.dataset.left, right: s.value });
  });
  const resp = await fetch("/learning/api/exercises/matching/", {
    method: "POST",
    headers: {"Content-Type":"application/json","X-CSRFToken": getCSRFToken()},
    body: JSON.stringify({ exercise_id: id, pairs })
  });
  const data = await resp.json();
  root.querySelector(".feedback").innerHTML = `Correctas: ${data.correct}/${data.total} — Puntaje: ${data.score?.toFixed ? data.score.toFixed(1) : ''}%`;
}

// Optional: manual add quick action (kept from earlier)
window.addManual = async function () {
  const es = document.getElementById("manual-es").value.trim();
  const gn = document.getElementById("manual-gn").value.trim();
  if (!es || !gn) { alert("Completa Español y Guaraní"); return; }
  const resp = await fetch("/learning/api/glossary/add/", {
    method: "POST",
    headers: {"Content-Type":"application/json","X-CSRFToken": getCSRFToken()},
    body: JSON.stringify({ source_text_es: es, translated_text_gn: gn, notes: "" })
  });
  if (!resp.ok) { alert("No se pudo agregar."); return; }
  addGlossaryListItem(es, gn);
  document.getElementById("manual-es").value = "";
  document.getElementById("manual-gn").value = "";
};