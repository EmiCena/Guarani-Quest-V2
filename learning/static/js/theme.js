// learning/static/js/theme.js
(function () {
  const key = "theme";
  const root = document.documentElement;
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const initial = localStorage.getItem(key) || (prefersDark ? "dark" : "light");
  root.setAttribute("data-theme", initial);

  function setIcon(next) {
    const a = document.getElementById("theme-toggle");
    const b = document.getElementById("theme-toggle-top");
    const icon = next === "dark" ? "☀️" : "🌙";
    if (a) a.textContent = icon;
    if (b) b.textContent = icon;
  }
  setIcon(initial);

  window.toggleTheme = function() {
    const current = root.getAttribute("data-theme") || "light";
    const next = current === "light" ? "dark" : "light";
    root.setAttribute("data-theme", next);
    localStorage.setItem(key, next);
    setIcon(next);
  };
})();