// learning/static/js/layout.js
(function(){
  const root = document.documentElement;
  const key = "sidebarState"; // 'expanded' | 'collapsed'
  // Apply saved state on desktop
  function applySaved() {
    const saved = localStorage.getItem(key) || "expanded";
    if (window.innerWidth > 900) {
      root.classList.toggle("sidebar-collapsed", saved === "collapsed");
    } else {
      root.classList.remove("sidebar-collapsed");
    }
  }
  applySaved();
  window.addEventListener("resize", applySaved);

  window.toggleSidebar = function() {
    const collapsed = root.classList.toggle("sidebar-collapsed");
    localStorage.setItem(key, collapsed ? "collapsed" : "expanded");
  };

  window.toggleSidebarMobile = function() {
    const state = root.getAttribute("data-sidebar-mobile");
    root.setAttribute("data-sidebar-mobile", state === "open" ? "closed" : "open");
  };
})();

(function highlightCurrentNav(){
  const path = location.pathname.replace(/\/+$/, "");
  document.querySelectorAll(".sidebar .nav-item").forEach(a => {
    const href = a.getAttribute("href").replace(/\/+$/, "");
    if (href && (path === href || path.startsWith(href + "/"))) {
      a.classList.add("active");
    }
  });
})();

(function commandPalette(){
  const map = [
    {label:"Dashboard", href:"/"},
    {label:"Glosario", href:"/learning/glossary/"},
    {label:"Estudiar (SRS)", href:"/learning/srs/study/"},
    {label:"Admin", href:"/admin/"},
  ];
  const root = document.getElementById("cmdk");
  const input = document.getElementById("cmdk-input");
  const list = document.getElementById("cmdk-list");
  let open = false, idx = 0;
  function render(q="") {
    const ql = q.toLowerCase();
    const items = map.filter(i => i.label.toLowerCase().includes(ql));
    list.innerHTML = items.map((i, k) => `<li class="${k===idx?'active':''}" data-href="${i.href}">${i.label}</li>`).join("");
  }
  function show() { root.setAttribute("aria-hidden","false"); open = true; idx = 0; input.value=""; render(""); input.focus(); }
  function hide() { root.setAttribute("aria-hidden","true"); open = false; }
  window.addEventListener("keydown", (e)=>{
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase()==="k") { e.preventDefault(); show(); }
    if (!open) return;
    if (e.key==="Escape") hide();
    if (e.key==="ArrowDown") { idx = Math.min(idx+1, list.children.length-1); render(input.value); }
    if (e.key==="ArrowUp")   { idx = Math.max(idx-1, 0); render(input.value); }
    if (e.key==="Enter") {
      const el = list.children[idx]; if (el) { location.href = el.dataset.href; hide(); }
    }
  });
  input?.addEventListener("input", ()=> render(input.value));
  list?.addEventListener("click", (e)=>{
    const li = e.target.closest("li"); if (li) { location.href = li.dataset.href; hide(); }
  });
  root?.addEventListener("click", (e)=> { if (e.target===root) hide(); });
})();