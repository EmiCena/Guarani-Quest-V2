// Active menu highlight
(function(){
  const path = location.pathname.replace(/\/+$/,'');
  document.querySelectorAll('.qx-menu a').forEach(a=>{
    const href=(a.getAttribute('href')||'').replace(/\/+$/,'');
    if(href && (path===href || path.startsWith(href+'/') || (href==='/' && path==='/'))) a.classList.add('active');
  });
})();

// Mobile menu toggle
window.qxToggleMenu = function(){
  const r=document.documentElement;
  r.classList.toggle('qx-menu-open');
};

// Glossary search filter
window.qxFilterGlossary = function(){
  const q=(document.getElementById('glossary-search')?.value||'').toLowerCase().trim();
  document.querySelectorAll('#glossary-list .card').forEach(el=>{
    const es=el.getAttribute('data-es')||'', gn=el.getAttribute('data-gn')||'';
    el.style.display = (!q || es.includes(q) || gn.includes(q)) ? '' : 'none';
  });
};

// Simple TTS (Spanish voice as fallback)
window.qxSpeak = function(text){
  try{
    const u=new SpeechSynthesisUtterance(text);
    u.lang='es-ES';
    speechSynthesis.cancel(); speechSynthesis.speak(u);
  }catch(e){ console.warn('TTS not available'); }
};