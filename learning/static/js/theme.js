// learning/static/js/theme.js
(function () {
  const key = "theme";
  const root = document.documentElement;

  function setIcon(theme) {
    const btn = document.getElementById("theme-toggle");
    if (btn) btn.textContent = theme === "dark" ? "☀️" : "🌙";
  }

  // Lee el actual (definido en el preload)
  const initial = root.getAttribute("data-theme") || "light";
  setIcon(initial);

  // Toggle
  window.toggleTheme = function () {
    const current = root.getAttribute("data-theme") || "light";
    const next = current === "light" ? "dark" : "light";
    root.setAttribute("data-theme", next);
    localStorage.setItem(key, next);
    setIcon(next);
  };
})();