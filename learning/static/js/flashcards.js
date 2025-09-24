// learning/static/js/flashcards.js
(function(){
  // Click en tarjeta = flip (ignora controles internos)
  document.addEventListener("click", (e) => {
    if (e.target.closest("button, a, input, textarea, select, .no-flip, .actions, .rec-controls")) return;
    const card = e.target.closest(".flash");
    if (!card || !document.getElementById("flash-grid")?.contains(card)) return;
    card.classList.toggle("flipped");
  });

  // Voltear con Enter/Espacio cuando la tarjeta tiene foco
  document.addEventListener("keydown", (e) => {
    const el = e.target;
    if (!el || !el.classList?.contains("flash")) return;
    if (e.code === "Space" || e.key === "Enter") {
      e.preventDefault();
      el.classList.toggle("flipped");
    }
  });
})();