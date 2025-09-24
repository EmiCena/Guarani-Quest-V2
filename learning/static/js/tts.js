// learning/static/js/tts.js
(function(){
  function pickVoiceFor(lang) {
    const voices = (window.speechSynthesis?.getVoices?.() || []);
    const lc = (lang || "").toLowerCase();
    let v = voices.find(v => v.lang?.toLowerCase().startsWith(lc));
    if (!v && lc.startsWith("gn")) {
      v = voices.find(v => /guaran[ií]/i.test(v.name || ""));
    }
    return v || null;
  }

  function speakWeb(text, lang) {
    return new Promise((resolve, reject) => {
      if (!("speechSynthesis" in window)) return reject(new Error("No speechSynthesis"));
      const u = new SpeechSynthesisUtterance(text);
      const v = pickVoiceFor(lang);
      if (v) { u.voice = v; u.lang = v.lang; } else if (lang) { u.lang = lang; }
      u.rate = 0.95;
      u.onend = resolve;
      u.onerror = reject;
      speechSynthesis.speak(u);
    });
  }

  async function ttsSpeak(text, lang = "gn", preset = "suave") {
    if (!text) return;
    try {
      if (speechSynthesis && speechSynthesis.onvoiceschanged != null) {
        await new Promise(r => setTimeout(r, 50));
      }
      const v = pickVoiceFor(lang);
      if (v) { await speakWeb(text, lang); return; }
    } catch (_) {}

    const url = `/learning/api/tts/?lang=${encodeURIComponent(lang)}&preset=${encodeURIComponent(preset)}&text=${encodeURIComponent(text)}`;
    const audio = new Audio(url);
    try { await audio.play(); } catch (e) { console.error("TTS play error", e); }
  }

  window.ttsSpeak = ttsSpeak;

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".tts-btn");
    if (!btn) return;
    const text = btn.dataset.ttsText || btn.textContent.trim();
    const lang = btn.dataset.ttsLang || "gn";
    const preset = btn.dataset.ttsPreset || "suave";
    if (text) ttsSpeak(text, lang, preset);
  });
})();