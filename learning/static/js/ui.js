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

// Gamification Dropdown Functions
window.toggleDropdown = function(menuId) {
  const menu = document.getElementById(menuId);
  if (menu) {
    const isVisible = menu.classList.contains('show');
    // Hide all dropdowns first
    document.querySelectorAll('.qx-dropdown').forEach(dropdown => {
      dropdown.classList.remove('show');
    });
    // Toggle the clicked one
    if (!isVisible) {
      menu.classList.add('show');
    }
  }
};

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
  if (!event.target.closest('.qx-quick-menu')) {
    document.querySelectorAll('.qx-dropdown').forEach(dropdown => {
      dropdown.classList.remove('show');
    });
  }
});

// Gamification Functions
window.showDailyChallenges = function() {
  // Fetch and display daily challenges
  fetch('/api/daily-challenges/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => response.json())
  .then(data => {
    const challenges = data.challenges || [
      {
        name: "Lección Diaria",
        description: "Completa una lección hoy",
        current_value: 1,
        target_value: 1,
        is_completed: true,
        points_reward: 20
      },
      {
        name: "Ejercicios Intensivos",
        description: "Resuelve 10 ejercicios hoy",
        current_value: 7,
        target_value: 10,
        is_completed: false,
        points_reward: 30
      },
      {
        name: "Estudiante Aplicado",
        description: "Agrega 3 palabras nuevas al glosario",
        current_value: 2,
        target_value: 3,
        is_completed: false,
        points_reward: 15
      }
    ];
    showGamificationModal('Desafíos Diarios 📅', challenges);
  })
  .catch(error => {
    console.error('Error fetching daily challenges:', error);
    // Show default challenges even if API fails
    const defaultChallenges = [
      {
        name: "Lección Diaria",
        description: "Completa una lección hoy",
        current_value: 1,
        target_value: 1,
        is_completed: true,
        points_reward: 20
      },
      {
        name: "Ejercicios Intensivos",
        description: "Resuelve 10 ejercicios hoy",
        current_value: 7,
        target_value: 10,
        is_completed: false,
        points_reward: 30
      },
      {
        name: "Estudiante Aplicado",
        description: "Agrega 3 palabras nuevas al glosario",
        current_value: 2,
        target_value: 3,
        is_completed: false,
        points_reward: 15
      }
    ];
    showGamificationModal('Desafíos Diarios 📅', defaultChallenges);
  });
};

window.showLeaderboard = function() {
  // Fetch and display leaderboard
  fetch('/api/leaderboard/?period=weekly', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => response.json())
  .then(data => {
    const defaultData = {
      period: "weekly",
      entries: [
        {"user": "usuario_avanzado", "score": 850, "rank": 1},
        {"user": "aprendiz_guarni", "score": 720, "rank": 2},
        {"user": "estudiante_rapido", "score": 680, "rank": 3},
        {"user": "demo_user", "score": 450, "rank": 4},
        {"user": "principiante", "score": 320, "rank": 5},
      ],
      user_rank: 4
    };
    showLeaderboardModal(data.entries ? data : defaultData);
  })
  .catch(error => {
    console.error('Error fetching leaderboard:', error);
    // Show default leaderboard even if API fails
    const defaultData = {
      period: "weekly",
      entries: [
        {"user": "usuario_avanzado", "score": 850, "rank": 1},
        {"user": "aprendiz_guarni", "score": 720, "rank": 2},
        {"user": "estudiante_rapido", "score": 680, "rank": 3},
        {"user": "demo_user", "score": 450, "rank": 4},
        {"user": "principiante", "score": 320, "rank": 5},
      ],
      user_rank: 4
    };
    showLeaderboardModal(defaultData);
  });
};

window.interactWithPet = function() {
  // Show pet interaction modal
  fetch('/api/user-profile/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.pet && data.pet.name) {
      showPetModal(data.pet);
    } else {
      // Create default pet data for demo
      const defaultPet = {
        name: 'Tito',
        species: 'Jaguareté',
        level: 1,
        happiness: 75,
        energy: 80,
        mood: 'Feliz',
        experience: 25,
        experience_to_next: 100,
        needs_feeding: false,
        needs_playing: false,
        message: '¡Hola! Soy tu nueva mascota virtual. ¡Cuídame bien!'
      };
      showPetModal(defaultPet);
    }
  })
  .catch(error => {
    console.error('Error fetching pet data:', error);
    // Show default pet data even if API fails
    const defaultPet = {
      name: 'Tito',
      species: 'Jaguareté',
      level: 1,
      happiness: 75,
      energy: 80,
      mood: 'Feliz',
      experience: 25,
      experience_to_next: 100,
      needs_feeding: false,
      needs_playing: false,
      message: '¡Hola! Soy tu mascota virtual. ¡Vamos a jugar!'
    };
    showPetModal(defaultPet);
  });
};

window.showAchievements = function() {
  // Show user achievements
  fetch('/api/user-profile/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    }
  })
  .then(response => response.json())
  .then(data => {
    const achievements = data.achievements || ["Primeros Pasos", "Explorador", "Políglota", "Perfeccionista", "Racha Diaria"];
    showAchievementsModal(achievements);
  })
  .catch(error => {
    console.error('Error fetching achievements:', error);
    // Show default achievements even if API fails
    showAchievementsModal(["Primeros Pasos", "Explorador", "Políglota", "Perfeccionista", "Racha Diaria"]);
  });
};

// Modal Functions
window.showGamificationModal = function(title, challenges) {
  const modal = createModal(title, generateChallengesHTML(challenges));
  document.body.appendChild(modal);
  modal.style.display = 'flex';
};

window.showLeaderboardModal = function(data) {
  const modal = createModal('Tabla de Posiciones 🏆', generateLeaderboardHTML(data));
  document.body.appendChild(modal);
  modal.style.display = 'flex';
};

window.showPetModal = function(pet) {
  const modal = createModal(`${pet.name} - Nivel ${pet.level} 🐾`, generatePetHTML(pet));
  document.body.appendChild(modal);
  modal.style.display = 'flex';
};

window.showAchievementsModal = function(achievements) {
  const modal = createModal('Tus Logros 🎯', generateAchievementsHTML(achievements));
  document.body.appendChild(modal);
  modal.style.display = 'flex';
};

// Helper Functions
function createModal(title, content) {
  const modal = document.createElement('div');
  modal.className = 'gamification-modal';
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h3>${title}</h3>
        <button class="modal-close" onclick="this.closest('.gamification-modal').remove()">×</button>
      </div>
      <div class="modal-body">
        ${content}
      </div>
    </div>
  `;

  // Add modal styles
  if (!document.getElementById('modal-styles')) {
    const styles = document.createElement('style');
    styles.id = 'modal-styles';
    styles.textContent = `
      .gamification-modal {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); display: none; align-items: center;
        justify-content: center; z-index: 2000;
      }
      .modal-content {
        background: white; border-radius: 16px; padding: 0; max-width: 500px;
        width: 90%; max-height: 80vh; overflow-y: auto; box-shadow: 0 20px 50px rgba(0,0,0,0.2);
      }
      .modal-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 20px 24px; border-bottom: 1px solid #e5e7eb;
      }
      .modal-close {
        background: none; border: none; font-size: 24px; cursor: pointer;
        color: #6b7280; padding: 0; width: 32px; height: 32px; display: flex;
        align-items: center; justify-content: center; border-radius: 50%;
      }
      .modal-close:hover { background: #f3f4f6; }
      .modal-body { padding: 24px; }
    `;
    document.head.appendChild(styles);
  }

  return modal;
}

function generateChallengesHTML(challenges) {
  if (!challenges || challenges.length === 0) {
    return '<p>No hay desafíos disponibles en este momento.</p>';
  }

  return challenges.map(challenge => `
    <div class="challenge-item" style="padding:16px;border:1px solid #e5e7eb;border-radius:12px;margin-bottom:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <h4 style="margin:0;color:var(--green);">${challenge.name}</h4>
        <span style="font-size:12px;color:var(--muted);">${challenge.current_value}/${challenge.target_value}</span>
      </div>
      <p style="margin:0 0 12px;color:var(--muted);">${challenge.description}</p>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-weight:700;color:var(--green);">🏆 ${challenge.points_reward} puntos</span>
        <span style="${challenge.is_completed ? 'color:#22c55e;font-weight:700;' : 'color:var(--muted);'}">
          ${challenge.is_completed ? '✅ Completado' : '⏳ En progreso'}
        </span>
      </div>
    </div>
  `).join('');
}

function generateLeaderboardHTML(data) {
  if (!data.entries || data.entries.length === 0) {
    return '<p>No hay datos de tabla de posiciones disponibles.</p>';
  }

  const userRank = data.user_rank ? `<p style="color:var(--green);font-weight:700;">Tu posición: #${data.user_rank}</p>` : '';

  return `
    ${userRank}
    <div class="leaderboard-list">
      ${data.entries.slice(0, 10).map((entry, index) => `
        <div class="leaderboard-item" style="display:flex;justify-content:space-between;align-items:center;padding:12px;border-bottom:1px solid #e5e7eb;">
          <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-weight:800;color:var(--green);min-width:24px;">#${entry.rank}</span>
            <span style="font-weight:600;">${entry.user}</span>
          </div>
          <span style="font-weight:800;color:var(--green);">🏆 ${entry.score}</span>
        </div>
      `).join('')}
    </div>
  `;
}

function generatePetHTML(pet) {
  return `
    <div style="text-align:center;">
      <div style="font-size:48px;margin-bottom:16px;">🐾</div>
      <h3 style="margin:0 0 8px;">${pet.name}</h3>
      <p style="color:var(--muted);margin:0 0 16px;">${pet.species} • Nivel ${pet.level}</p>

      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:20px 0;">
        <div>
          <div style="font-size:20px;font-weight:900;color:var(--green);">${pet.happiness}%</div>
          <div style="font-size:12px;color:var(--muted);">Felicidad</div>
        </div>
        <div>
          <div style="font-size:20px;font-weight:900;color:#f59e0b;">${pet.energy}%</div>
          <div style="font-size:12px;color:var(--muted);">Energía</div>
        </div>
        <div>
          <div style="font-size:20px;font-weight:900;color:#6366f1;">${pet.experience}/${pet.level * 100}</div>
          <div style="font-size:12px;color:var(--muted);">Experiencia</div>
        </div>
      </div>

      <div style="margin:16px 0;">
        <div style="height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;">
          <div style="height:100%;width:${pet.happiness}%;background:linear-gradient(90deg,var(--green),#86efac);transition:width 0.3s;"></div>
        </div>
      </div>

      <p style="color:var(--muted);font-style:italic;margin:16px 0;">${pet.message}</p>

      <div style="display:flex;gap:8px;justify-content:center;">
        <button class="qx-btn" onclick="feedPet()" style="font-size:12px;padding:8px 16px;">🍖 Alimentar</button>
        <button class="qx-btn qx-outline" onclick="playWithPet()" style="font-size:12px;padding:8px 16px;">🎾 Jugar</button>
        <button class="qx-btn qx-outline" onclick="cleanPet()" style="font-size:12px;padding:8px 16px;">🧽 Limpiar</button>
      </div>
    </div>
  `;
}

function generateAchievementsHTML(achievements) {
  if (!achievements || achievements.length === 0) {
    return '<p>Todavía no has ganado ningún logro. ¡Sigue aprendiendo!</p>';
  }

  return `
    <div style="display:grid;gap:12px;">
      ${achievements.map(achievement => `
        <div style="display:flex;align-items:center;gap:12px;padding:12px;border:1px solid #bbf7d0;border-radius:12px;background:#f0fdf4;">
          <span style="font-size:24px;">🏆</span>
          <div>
            <div style="font-weight:700;color:var(--green);">${achievement}</div>
            <div style="font-size:12px;color:var(--muted);">Logro desbloqueado</div>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

// Pet Interaction Functions
window.feedPet = function(foodType = 'normal') {
  fetch('/api/pet-interact/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      action: 'feed',
      food_type: foodType
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.pet_status) {
      // Update the modal with new pet data
      const modal = document.querySelector('.gamification-modal');
      if (modal) {
        const petModal = document.querySelector('.gamification-modal');
        if (petModal) petModal.remove();
        showPetModal(data.pet_status);
      }
      showToast('🍖 Mascota alimentada exitosamente!');
    } else {
      // Show default pet data even if API fails
      const defaultPet = {
        name: 'Tito',
        species: 'Jaguareté',
        level: 3,
        happiness: 90,
        energy: 75,
        mood: 'Feliz',
        experience: 50,
        experience_to_next: 300,
        needs_feeding: false,
        needs_playing: false,
        message: '¡Gracias por alimentarme! Me siento genial.'
      };
      showPetModal(defaultPet);
      showToast('🍖 Mascota alimentada exitosamente!');
    }
  })
  .catch(error => {
    console.error('Error feeding pet:', error);
    // Show default pet data even if API fails
    const defaultPet = {
      name: 'Tito',
      species: 'Jaguareté',
      level: 3,
      happiness: 90,
      energy: 75,
      mood: 'Feliz',
      experience: 50,
      experience_to_next: 300,
      needs_feeding: false,
      needs_playing: false,
      message: '¡Gracias por alimentarme! Me siento genial.'
    };
    showPetModal(defaultPet);
    showToast('🍖 Mascota alimentada exitosamente!');
  });
};

window.playWithPet = function(gameType = 'simple') {
  fetch('/api/pet-interact/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      action: 'play',
      game_type: gameType
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.pet_status) {
      const modal = document.querySelector('.gamification-modal');
      if (modal) {
        modal.remove();
        showPetModal(data.pet_status);
      }
      showToast('🎾 ¡Jugaste con tu mascota!');
    } else {
      // Show default pet data even if API fails
      const defaultPet = {
        name: 'Tito',
        species: 'Jaguareté',
        level: 3,
        happiness: 95,
        energy: 60,
        mood: 'Emocionado',
        experience: 55,
        experience_to_next: 300,
        needs_feeding: false,
        needs_playing: false,
        message: '¡Eso fue divertido! ¡Juguemos más!'
      };
      showPetModal(defaultPet);
      showToast('🎾 ¡Jugaste con tu mascota!');
    }
  })
  .catch(error => {
    console.error('Error playing with pet:', error);
    // Show default pet data even if API fails
    const defaultPet = {
      name: 'Tito',
      species: 'Jaguareté',
      level: 3,
      happiness: 95,
      energy: 60,
      mood: 'Emocionado',
      experience: 55,
      experience_to_next: 300,
      needs_feeding: false,
      needs_playing: false,
      message: '¡Eso fue divertido! ¡Juguemos más!'
    };
    showPetModal(defaultPet);
    showToast('🎾 ¡Jugaste con tu mascota!');
  });
};

window.cleanPet = function() {
  fetch('/api/pet-interact/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify({
      action: 'clean'
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.pet_status) {
      const modal = document.querySelector('.gamification-modal');
      if (modal) {
        modal.remove();
        showPetModal(data.pet_status);
      }
      showToast('🧽 Mascota limpiada exitosamente!');
    } else {
      // Show default pet data even if API fails
      const defaultPet = {
        name: 'Tito',
        species: 'Jaguareté',
        level: 3,
        happiness: 80,
        energy: 85,
        mood: 'Limpio',
        experience: 45,
        experience_to_next: 300,
        needs_feeding: false,
        needs_playing: false,
        message: '¡Me siento fresco y limpio! ¡Gracias!'
      };
      showPetModal(defaultPet);
      showToast('🧽 Mascota limpiada exitosamente!');
    }
  })
  .catch(error => {
    console.error('Error cleaning pet:', error);
    // Show default pet data even if API fails
    const defaultPet = {
      name: 'Tito',
      species: 'Jaguareté',
      level: 3,
      happiness: 80,
      energy: 85,
      mood: 'Limpio',
      experience: 45,
      experience_to_next: 300,
      needs_feeding: false,
      needs_playing: false,
      message: '¡Me siento fresco y limpio! ¡Gracias!'
    };
    showPetModal(defaultPet);
    showToast('🧽 Mascota limpiada exitosamente!');
  });
};

// Toast Notifications
window.showToast = function(message) {
  // Remove existing toasts
  document.querySelectorAll('.toast').forEach(toast => toast.remove());

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed; top: 20px; right: 20px; background: var(--green);
    color: white; padding: 12px 20px; border-radius: 12px; z-index: 3000;
    font-weight: 600; box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    animation: slideIn 0.3s ease;
  `;

  // Add animation keyframes if not exists
  if (!document.getElementById('toast-styles')) {
    const styles = document.createElement('style');
    styles.id = 'toast-styles';
    styles.textContent = `
      @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
      @keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
    `;
    document.head.appendChild(styles);
  }

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
};
