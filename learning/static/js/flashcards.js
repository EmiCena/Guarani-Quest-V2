// learning/static/js/flashcards.js
// Flip cards + grabación y subida de audio real al glosario

// Fallback por si no existe getCSRFToken
(function(){
  if (typeof window.getCSRFToken !== 'function') {
    function getCookie(name) {
      let v=null;
      if(document.cookie && document.cookie!==''){
        for(const c of document.cookie.split(';')){
          const ck=c.trim();
          if(ck.startsWith(name+'=')){ v=decodeURIComponent(ck.substring(name.length+1)); break; }
        }
      }
      return v;
    }
    window.getCSRFToken = function(){
      return getCookie('csrftoken') || (document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')||'');
    }
  }
})();

// Búsqueda (si ui.js no está)
window.qxFilterGlossary = window.qxFilterGlossary || function(){
  const q=(document.getElementById('glossary-search')?.value||'').toLowerCase().trim();
  document.querySelectorAll('#flash-grid .flash').forEach(el=>{
    const es=el.getAttribute('data-es')||'', gn=el.getAttribute('data-gn')||'';
    el.style.display = (!q || es.includes(q) || gn.includes(q)) ? '' : 'none';
  });
};

// TTS (si no está en ui.js)
window.qxSpeak = window.qxSpeak || function(text){
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'es-ES';
    speechSynthesis.cancel(); speechSynthesis.speak(u);
  } catch(_) {}
};

// Grabación con MediaRecorder
const recState = {}; // id -> {stream, recorder, chunks:[], mime}

async function _getUserMedia(){
  return await navigator.mediaDevices.getUserMedia({audio:true});
}

window.startRec = async function(id){
  try{
    const stream = await _getUserMedia();
    const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" :
                 MediaRecorder.isTypeSupported("audio/ogg")  ? "audio/ogg"  : "";
    const mr = new MediaRecorder(stream, mime ? {mimeType:mime} : undefined);
    recState[id] = {stream, recorder:mr, chunks:[], mime: mime || "audio/webm"};
    mr.ondataavailable = e => { if(e.data?.size>0) recState[id].chunks.push(e.data); };
    mr.onstop = () => {
      const blob = new Blob(recState[id].chunks, {type: recState[id].mime});
      const url = URL.createObjectURL(blob);
      const prev = document.getElementById(`prev-${id}`);
      if(prev){ prev.src = url; prev.style.display="block"; }
      const hint = document.getElementById(`hint-${id}`);
      if(hint) hint.textContent = "Listo para subir";
    };
    mr.start();
    const hint = document.getElementById(`hint-${id}`);
    if(hint) hint.textContent = "Grabando…";
  }catch(e){
    alert("No se pudo acceder al micrófono. Usa Chrome/Edge y otorga permisos.");
    console.error(e);
  }
}

window.stopRec = function(id){
  const st = recState[id];
  if(st?.recorder && st.recorder.state !== "inactive"){ st.recorder.stop(); }
  if(st?.stream){ st.stream.getTracks().forEach(t=>t.stop()); }
}

window.saveRec = async function(id){
  const st = recState[id];
  if(!st || !st.chunks?.length){
    alert("Graba primero un audio."); return;
  }
  const blob = new Blob(st.chunks, {type: st.mime});
  const fd = new FormData();
  fd.append("audio", blob, `pron_${id}.${st.mime.includes("ogg")?"ogg":"webm"}`);

  const resp = await fetch(`/learning/api/glossary/${id}/upload-audio/`, {
    method: "POST",
    headers: {"X-CSRFToken": getCSRFToken()},
    credentials: "same-origin",
    body: fd
  });
  if(!resp.ok){ alert("No se pudo subir el audio."); return; }
  const data = await resp.json();
  const prev = document.getElementById(`prev-${id}`);
  if(prev){ prev.src = data.url; prev.style.display="block"; }
  const hint = document.getElementById(`hint-${id}`);
  if(hint) hint.textContent = "Subido ✅";
  // limpia estado
  recState[id] = null;
}