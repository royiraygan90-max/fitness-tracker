/* ===== TOAST ===== */
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3100);
}

// Show flash messages from server
if (window.__flashMessages) {
  window.__flashMessages.forEach(([cat, msg]) => showToast(msg, cat));
}

/* ===== LOG FORM WIZARD ===== */
const typeRadios = document.querySelectorAll('input[name="workout_type"]');
const exerciseSection = document.getElementById('exercise-section');
const notesLabel = document.getElementById('notes-label');

function updateFormForType(type) {
  const isWorkout = type === 'workout_a' || type === 'workout_b';
  if (exerciseSection) {
    exerciseSection.style.display = isWorkout ? 'block' : 'none';
  }
  if (notesLabel) {
    notesLabel.textContent = isWorkout ? 'Step 4 — Notes' : 'Step 3 — Notes';
  }

  // Show/hide correct exercise list
  ['workout_a', 'workout_b'].forEach(t => {
    const el = document.getElementById(`exercises-${t}`);
    if (el) el.style.display = (type === t) ? 'block' : 'none';
  });
}

typeRadios.forEach(radio => {
  radio.addEventListener('change', () => updateFormForType(radio.value));
});

/* ===== EXERCISE CHECKBOXES ===== */
document.querySelectorAll('.ex-checkbox').forEach(checkbox => {
  checkbox.addEventListener('change', function () {
    const row = this.closest('.exercise-row');
    const inputs = row.querySelector('.exercise-inputs');
    if (inputs) inputs.style.display = this.checked ? 'flex' : 'none';
    row.classList.toggle('checked', this.checked);
  });
});

/* ===== DELETE CONFIRMATION ===== */
function confirmDelete(workoutId) {
  if (!confirm('Delete this workout? This cannot be undone.')) return;
  fetch(`/api/delete/${workoutId}`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        const el = document.getElementById(`workout-${workoutId}`);
        if (el) {
          el.style.transition = 'opacity 0.3s, transform 0.3s';
          el.style.opacity = '0';
          el.style.transform = 'translateX(20px)';
          setTimeout(() => el.remove(), 320);
        }
        showToast('Workout deleted');
      }
    })
    .catch(() => showToast('Failed to delete', 'error'));
}
