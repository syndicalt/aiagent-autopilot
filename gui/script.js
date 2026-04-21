// In Tauri v2 with withGlobalTauri, the API is available on window.__TAURI__
const { invoke } = window.__TAURI__.core;

const statusBadge = document.getElementById('status-badge');
const smartSortBadge = document.getElementById('smart-sort-badge');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnUndo = document.getElementById('btn-undo');
const btnRefresh = document.getElementById('btn-refresh');
const actionList = document.getElementById('action-list');

async function updateStatus() {
  try {
    const running = await invoke('get_agent_status');
    if (running) {
      statusBadge.textContent = 'Running';
      statusBadge.classList.add('running');
      btnStart.disabled = true;
      btnStop.disabled = false;
    } else {
      statusBadge.textContent = 'Stopped';
      statusBadge.classList.remove('running');
      btnStart.disabled = false;
      btnStop.disabled = true;
    }
  } catch (e) {
    console.error('Status error:', e);
  }
}

async function updateSmartSortStatus() {
  try {
    const ready = await invoke('get_smart_sort_status');
    if (ready) {
      smartSortBadge.textContent = 'Smart Sort: Ready';
      smartSortBadge.classList.add('ready');
    } else {
      smartSortBadge.textContent = 'Smart Sort: Offline';
      smartSortBadge.classList.remove('ready');
    }
  } catch (e) {
    console.error('Smart sort status error:', e);
  }
}

async function loadActions() {
  try {
    const actions = await invoke('get_recent_actions', { limit: 20 });
    actionList.innerHTML = '';

    if (!actions || actions.length === 0) {
      actionList.innerHTML = '<li class="empty">No actions yet.</li>';
      btnUndo.disabled = true;
      return;
    }

    btnUndo.disabled = false;

    for (const a of actions) {
      const li = document.createElement('li');
      li.innerHTML = `
        <div class="action-meta">
          <span class="action-name">${escapeHtml(a.original_name)}</span>
          <span class="action-detail">${formatTime(a.timestamp)}</span>
        </div>
        <span class="action-cat">${escapeHtml(a.category)}</span>
      `;
      actionList.appendChild(li);
    }
  } catch (e) {
    console.error('Actions error:', e);
    actionList.innerHTML = '<li class="empty">Error loading actions.</li>';
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

btnStart.addEventListener('click', async () => {
  btnStart.disabled = true;
  try {
    const msg = await invoke('start_agent');
    console.log(msg);
  } catch (e) {
    alert('Failed to start: ' + e);
  }
  await updateStatus();
});

btnStop.addEventListener('click', async () => {
  btnStop.disabled = true;
  try {
    const msg = await invoke('stop_agent');
    console.log(msg);
  } catch (e) {
    alert('Failed to stop: ' + e);
  }
  await updateStatus();
});

btnUndo.addEventListener('click', async () => {
  btnUndo.disabled = true;
  try {
    const msg = await invoke('undo_last');
    console.log(msg);
    await loadActions();
  } catch (e) {
    alert('Undo failed: ' + e);
    btnUndo.disabled = false;
  }
});

btnRefresh.addEventListener('click', loadActions);

// Poll every 3 seconds
setInterval(() => {
  updateStatus();
  loadActions();
  updateSmartSortStatus();
}, 3000);

// Initial load
updateStatus();
loadActions();
updateSmartSortStatus();
