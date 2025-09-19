// learning/static/js/exercises.js

async function postJSON(url, payload){
  const resp = await fetch(url, {
    method: "POST",
    headers: {"Content-Type":"application/json","X-CSRFToken": getCSRFToken()},
    credentials: "same-origin",
    body: JSON.stringify(payload)
  });
  return resp;
}

window.submitDragDrop = async function(id){
  const root = document.getElementById(`drag-${id}`);
  const drop = root.querySelector(`#drop-${id}`);
  const chips = Array.from(drop.querySelectorAll(".chip"));
  const order = chips.map(c=>c.textContent.trim());
  const r = await postJSON("/learning/api/exercises/dragdrop/", { exercise_id:id, order });
  const data = await r.json();
  root.querySelector(".feedback").innerHTML =
    r.ok ? `Puntaje: ${data.score.toFixed(1)}% (${data.correct_positions}/${data.total})`
         : `Error (${r.status})`;
}

window.submitListening = async function(id){
  const root = document.getElementById(`listen-${id}`);
  const sel = root.querySelector(`input[name="listen-${id}"]:checked`);
  if(!sel){ alert("Selecciona una opción"); return; }
  const r = await postJSON("/learning/api/exercises/listening/", { exercise_id:id, selected_key: sel.value });
  const data = await r.json();
  root.querySelector(".feedback").innerHTML =
    r.ok ? `Puntaje: ${data.score.toFixed(0)}% ${data.is_correct ? "✅" : "❌"}`
         : `Error (${r.status})`;
}

window.submitTranslation = async function(id){
  const root = document.getElementById(`trans-${id}`);
  const ans = root.querySelector(`#ans-${id}`).value.trim();
  if(!ans){ alert("Escribe tu respuesta"); return; }
  const r = await postJSON("/learning/api/exercises/translation/", { exercise_id:id, answer: ans });
  const data = await r.json();
  root.querySelector(".feedback").innerHTML =
    r.ok ? `Puntaje: ${data.score.toFixed(1)}% ${data.is_correct ? "✅" : "❌"}`
         : `Error (${r.status})`;
}