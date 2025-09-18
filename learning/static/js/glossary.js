// learning/static/js/glossary.js
async function translateAndAdd() {
  const el = document.getElementById("gloss-source");
  const text = el.value.trim();
  if (!text) { alert("Ingresa un texto en español"); return; }
  const resp = await fetch("/learning/api/translate-and-add/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
    body: JSON.stringify({ source_text_es: text })
  });
  if (!resp.ok) { alert("Error al traducir"); return; }
  const data = await resp.json();
  const list = document.getElementById("glossary-list");
  const li = document.createElement("li");
  li.innerHTML = `<strong>${text}</strong> → ${data.translated_text_gn}`;
  list.prepend(li);
  el.value = "";
}

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