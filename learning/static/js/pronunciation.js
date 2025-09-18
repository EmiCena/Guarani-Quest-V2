// learning/static/js/pronunciation.js
let recognizers = {}; // key: exerciseId

async function getAzureToken() {
  const resp = await fetch("/learning/api/azure/token/");
  if (!resp.ok) throw new Error("No se pudo obtener el token de Azure");
  return await resp.json();
}

window.startPronunciation = async function(exerciseId, referenceText) {
  if (!window.SpeechSDK) { alert("Speech SDK no cargado"); return; }
  if (recognizers[exerciseId]) { return; }

  const { token, region } = await getAzureToken();
  const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);
  // If gn-PY isn't supported by your Azure resource, es-ES is a reasonable fallback
  speechConfig.speechRecognitionLanguage = "es-ES";

  const pronConfig = new SpeechSDK.PronunciationAssessmentConfig(
    referenceText,
    SpeechSDK.PronunciationAssessmentGradingSystem.HundredMark,
    SpeechSDK.PronunciationAssessmentGranularity.Phoneme,
    true
  );

  const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
  const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
  pronConfig.applyTo(recognizer);

  const elAcc = document.getElementById(`acc-${exerciseId}`);
  const elFlu = document.getElementById(`flu-${exerciseId}`);
  const elComp = document.getElementById(`comp-${exerciseId}`);
  const bar = document.getElementById(`bar-${exerciseId}`);

  recognizer.recognized = async (s, e) => {
    if (e.result && e.result.properties) {
      const json = e.result.properties.getProperty(SpeechSDK.PropertyId.SpeechServiceResponse_JsonResult);
      try {
        const obj = JSON.parse(json);
        const pa = obj.NBest && obj.NBest[0] && obj.NBest[0].PronunciationAssessment;
        if (pa) {
          const acc = pa.AccuracyScore || 0;
          const flu = pa.FluencyScore || 0;
          const comp = pa.CompletenessScore || 0;
          elAcc.textContent = acc.toFixed(1);
          elFlu.textContent = flu.toFixed(1);
          elComp.textContent = comp.toFixed(1);
          const overall = (acc + flu + comp) / 3;
          bar.style.width = `${overall.toFixed(0)}%`;

          await fetch("/learning/api/pronunciation/attempt/", {
            method: "POST",
            headers: {"Content-Type":"application/json", "X-CSRFToken": getCSRFToken()},
            body: JSON.stringify({
              exercise_id: parseInt(exerciseId),
              expected_text: referenceText,
              accuracy_score: acc,
              fluency_score: flu,
              completeness_score: comp,
              prosody_score: 0.0
            })
          });
        }
      } catch (_) {}
    }
  };

  recognizer.canceled = (s, e) => {
    console.warn("Canceled:", e);
  };
  recognizer.sessionStopped = (s, e) => {
    recognizers[exerciseId] = null;
  };

  recognizers[exerciseId] = recognizer;
  recognizer.startContinuousRecognitionAsync();
};

window.stopPronunciation = function(exerciseId) {
  const recognizer = recognizers[exerciseId];
  if (recognizer) {
    recognizer.stopContinuousRecognitionAsync(
      () => { recognizers[exerciseId] = null; },
      (err) => { console.error(err); recognizers[exerciseId] = null; }
    );
  }
};