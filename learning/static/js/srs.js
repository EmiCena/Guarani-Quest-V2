// learning/static/js/srs.js
// SRS UI con loader y modo "pills" – sin await fuera de async

// --- CSRF fallback ---
(function(){
  if (typeof window.getCSRFToken !== 'function') {
    function getCookie(name){
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
      return getCookie('csrftoken') ||
             (document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')||'');
    };
  }
})();

// --- Estado global mínimo ---
let currentCard = null;
let reverseMode = false;
let srsState = { mode:"comfortable", new_limit:15, new_shown_today:0, allowed_new_today:0, due_review_count:0, new_available_count:0 };

// --- Loader ---
let loaderTimer = 0, loaderElapsed = 0, loaderMsgStep = 0;
function startLoader(title){
  const L = document.getElementById("srs-loader");
  if(!L) return;
  document.getElementById("loader-title").textContent = title || "Cargando tarjetas…";
  document.getElementById("loader-sub").innerHTML = "Esto puede tardar algunos segundos la primera vez.";
  L.classList.remove("hidden");
  loaderElapsed = 0; loaderMsgStep = 0;
  clearInterval(loaderTimer);
  loaderTimer = setInterval(function(){
    loaderElapsed += 700;
    if(loaderElapsed > 2500 && loaderMsgStep < 1){
      document.getElementById("loader-sub").textContent = "Preparando tu sesión (puede tardar ~3–5s).";
      loaderMsgStep = 1;
    }
    if(loaderElapsed > 6000 && loaderMsgStep < 2){
      document.getElementById("loader-sub").innerHTML = 'Si no avanza, <a href="#" onclick="srsNext(true)">reintenta</a>.';
      loaderMsgStep = 2;
    }
  },700);
}
function stopLoader(){
  clearInterval(loaderTimer);
  const L = document.getElementById("srs-loader");
  if(L) L.classList.add("hidden");
}

// --- UI helpers ---
function updateModeButtons(){
  ["beginner","comfortable","aggressive"].forEach(function(m){
    const b = document.getElementById("mode-"+m);
    if(b) b.classList.toggle("active", srsState.mode === m);
  });
  const nc=document.getElementById("new-count"), nl=document.getElementById("new-limit"), dc=document.getElementById("due-count");
  if(nc) nc.textContent = srsState.new_shown_today || 0;
  if(nl) nl.textContent = srsState.new_limit || 0;
  if(dc) dc.textContent = srsState.due_review_count || 0;

  // Gauge
  const g=document.getElementById("gauge"), t=document.getElementById("gauge-text");
  const limit = srsState.new_limit || 1;
  const pct = Math.min(100, Math.round((srsState.new_shown_today/limit)*100));
  if(g) g.style.setProperty("--val", pct);
  if(t) t.textContent = pct + "%";
}

async function loadSrsState(){
  try{
    const r = await fetch("/learning/api/srs/state/", {
      method:"GET", headers:{"Accept":"application/json"}, credentials:"same-origin"
    });
    if(r.ok){
      const data = await r.json();
      srsState = Object.assign(srsState, data);
      updateModeButtons();
    }
  }catch(_){}
}

// --- API helpers ---
async function srsSync(){
  try{
    const r = await fetch("/learning/api/srs/sync/", {
      method:"POST", headers:{"X-CSRFToken":getCSRFToken(),"Accept":"application/json"},
      credentials:"same-origin"
    });
    if(!r.ok){ console.warn("sync", r.status); }
  }catch(e){ console.warn("sync error", e); }
}

// --- Control de modo / reverso (sin await en top-level) ---
window.setMode = function(mode){
  (async function(){
    try{
      const r = await fetch("/learning/api/srs/set-mode/", {
        method:"POST",
        headers:{"Content-Type":"application/json","X-CSRFToken":getCSRFToken(),"Accept":"application/json"},
        credentials:"same-origin",
        body: JSON.stringify({ mode: mode })
      });
      if(r.ok){
        const data = await r.json();
        srsState = Object.assign(srsState, data);
        updateModeButtons();
        await srsNext(true);
      }
    }catch(e){ console.error(e); }
  })();
};

window.toggleReverse = function(){
  reverseMode = !reverseMode;
  if(currentCard){
    const f=document.getElementById("front");
    const b=document.getElementById("back");
    f.textContent = reverseMode ? currentCard.back_gn : currentCard.front_es;
    b.textContent = reverseMode ? currentCard.front_es : (currentCard.back_gn || "(sin respuesta)");
    document.getElementById("back").style.display="none";
    document.getElementById("grades").style.display="none";
  }
};

// --- Flujo SRS ---
window.srsInit = function(){
  (async function(){
    startLoader("Preparando tu sesión…");
    await loadSrsState();
    await srsSync();
    await srsNext();
  })();
};

window.srsNext = function(forceRetry){
  return (async function(){
    startLoader(forceRetry ? "Reintentando…" : "Buscando tu próxima tarjeta…");
    const f=document.getElementById("front"), b=document.getElementById("back"), n=document.getElementById("notes"), g=document.getElementById("grades");
    try{
      const r = await fetch("/learning/api/srs/next/", {
        method:"POST",
        headers:{"X-CSRFToken":getCSRFToken(),"Accept":"application/json"},
        credentials:"same-origin"
      });
      stopLoader();
      if(!r.ok){
        if(f) f.textContent = "Error "+r.status+". ¿Sesión iniciada?";
        [b,n,g].forEach(function(el){ if(el) el.style.display="none"; });
        return;
      }
      const ct = r.headers.get("content-type") || "";
      if(!ct.includes("application/json")){
        if(f) f.textContent = "Respuesta no válida. Recarga la página e inicia sesión.";
        [b,n,g].forEach(function(el){ if(el) el.style.display="none"; });
        return;
      }
      const data = await r.json();
      await loadSrsState();

      if(!data.card){
        if(data.reason === "new_cap_reached"){
          if(f) f.textContent = "Límite diario de nuevas tarjetas alcanzado. Vuelve mañana o cambia el modo.";
        } else {
          if(f) f.innerHTML = 'No hay tarjetas pendientes. Agrega palabras al Glosario o <a href="#" onclick="srsNext(true)">reintenta</a>.';
        }
        [b,n,g].forEach(function(el){ if(el) el.style.display="none"; });
        currentCard = null;
        return;
      }

      currentCard = data.card;
      if(f) f.textContent = reverseMode ? currentCard.back_gn : currentCard.front_es;
      if(b) b.textContent = reverseMode ? currentCard.front_es : (currentCard.back_gn || "(sin respuesta)");
      if(n){
        n.textContent = currentCard.notes ? "Notas: " + currentCard.notes : "";
        n.style.display = currentCard.notes ? "block" : "none";
      }
      if(b) b.style.display = "none";
      if(g) g.style.display = "none";
    }catch(e){
      stopLoader();
      console.error("next err", e);
      if(f) f.innerHTML = 'No se pudo cargar. Revisa tu conexión o <a href="#" onclick="srsNext(true)">reintenta</a>.';
      [b,n,g].forEach(function(el){ if(el) el.style.display="none"; });
    }
  })();
};

window.srsShow = function(){
  if(!currentCard) return;
  document.getElementById("back").style.display="block";
  document.getElementById("grades").style.display="flex";
};

window.srsGrade = function(score){
  (async function(){
    if(!currentCard) return;
    try{
      const r = await fetch("/learning/api/srs/grade/", {
        method:"POST",
        headers:{"Content-Type":"application/json","X-CSRFToken":getCSRFToken(),"Accept":"application/json"},
        credentials:"same-origin",
        body: JSON.stringify({ card_id: currentCard.id, rating: score })
      });
      // consume respuesta para cerrar la conexión; ignora contenido
      try { await r.json(); } catch(_){}
    }catch(e){ console.error("grade", e); }
    await srsNext();
  })();
};

window.srsSkip = function(){ srsNext(); };

// Shortcuts
document.addEventListener("keydown", function(e){
  const tag=(e.target && e.target.tagName || "").toLowerCase();
  if(tag==="input"||tag==="textarea") return;
  if(e.code==="Space"){ e.preventDefault(); srsShow(); }
  if("012345".includes(e.key)){ srsGrade(parseInt(e.key,10)); }
  if(e.key==="n" || e.key==="Enter"){ srsSkip(); }
});