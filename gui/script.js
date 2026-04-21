// In Tauri v2 with withGlobalTauri, the API is available on window.__TAURI__
const { invoke } = window.__TAURI__.core;

const statusBadge = document.getElementById('status-badge');
const smartSortBadge = document.getElementById('smart-sort-badge');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnUndo = document.getElementById('btn-undo');
const btnRefresh = document.getElementById('btn-refresh');
const muteSwitch = document.getElementById('mute-switch');
const muteSwitchLabel = document.getElementById('mute-switch-label');
const btnLogs = document.getElementById('btn-logs');
const btnHideLogs = document.getElementById('btn-hide-logs');
const logsSection = document.getElementById('logs-section');
const logOutput = document.getElementById('log-output');
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
      smartSortBadge.textContent = 'Smart Sort: Local';
      smartSortBadge.classList.add('ready');
    } else {
      smartSortBadge.textContent = 'Smart Sort: Setting up...';
      smartSortBadge.classList.remove('ready');
    }
  } catch (e) {
    console.error('Smart sort status error:', e);
  }
}

async function updateMuteStatus() {
  try {
    const muted = await invoke('get_notifications_muted');
    muteSwitch.checked = muted;
  } catch (e) {
    console.error('Mute status error:', e);
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

muteSwitch.addEventListener('change', async () => {
  try {
    const muted = await invoke('toggle_notifications');
    muteSwitch.checked = muted;
  } catch (e) {
    alert('Failed to toggle notifications: ' + e);
    // Revert on error
    const current = await invoke('get_notifications_muted').catch(() => false);
    muteSwitch.checked = current;
  }
});

// Poll every 3 seconds
setInterval(() => {
  updateStatus();
  loadActions();
  updateSmartSortStatus();
}, 3000);

btnLogs.addEventListener('click', async () => {
  try {
    const logs = await invoke('get_agent_logs');
    logOutput.textContent = logs;
    logsSection.style.display = 'block';
  } catch (e) {
    console.error('Logs error:', e);
  }
});

btnHideLogs.addEventListener('click', () => {
  logsSection.style.display = 'none';
});

// Initial load
updateStatus();
loadActions();
updateSmartSortStatus();
updateMuteStatus();
loadRules();

// =====================
// Rules Engine UI
// =====================
let rules = [];

const btnAddRule = document.getElementById('btn-add-rule');
const rulesList = document.getElementById('rules-list');
const btnSaveRules = document.getElementById('btn-save-rules');
const testFilename = document.getElementById('test-filename');
const btnTestRules = document.getElementById('btn-test-rules');
const testResults = document.getElementById('test-results');

function createEmptyRule() {
  return {
    id: crypto.randomUUID(),
    name: 'New Rule',
    enabled: true,
    conditions: [{ field: 'extension', operator: 'equals', value: '' }],
    action: { type: 'move_to', target: '' }
  };
}

async function loadRules() {
  try {
    rules = await invoke('get_rules');
    if (!Array.isArray(rules)) rules = [];
    renderRules();
  } catch (e) {
    console.error('Rules error:', e);
  }
}

function renderRules() {
  rulesList.innerHTML = '';
  if (rules.length === 0) {
    rulesList.innerHTML = '<div class="empty-state">No rules yet. Click + Add Rule to create one.</div>';
    return;
  }
  rules.forEach((rule, index) => {
    const card = document.createElement('div');
    card.className = 'rule-card';
    card.dataset.index = index;

    // Header
    const header = document.createElement('div');
    header.className = 'rule-header';

    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.className = 'rule-name';
    nameInput.value = rule.name || '';
    nameInput.placeholder = 'Rule name';
    nameInput.addEventListener('input', () => {
      rules[index].name = nameInput.value;
    });

    const enabledLabel = document.createElement('label');
    enabledLabel.className = 'rule-enabled';
    const enabledBox = document.createElement('input');
    enabledBox.type = 'checkbox';
    enabledBox.checked = rule.enabled !== false;
    enabledBox.addEventListener('change', () => {
      rules[index].enabled = enabledBox.checked;
    });
    enabledLabel.appendChild(enabledBox);
    enabledLabel.appendChild(document.createTextNode('Enabled'));

    const delBtn = document.createElement('button');
    delBtn.className = 'rule-delete';
    delBtn.textContent = '×';
    delBtn.title = 'Delete rule';
    delBtn.addEventListener('click', () => {
      rules.splice(index, 1);
      renderRules();
    });

    header.appendChild(nameInput);
    header.appendChild(enabledLabel);
    header.appendChild(delBtn);

    // Conditions
    const condsTitle = document.createElement('div');
    condsTitle.className = 'conditions-title';
    condsTitle.textContent = 'Conditions (all must match)';

    const condsContainer = document.createElement('div');
    (rule.conditions || []).forEach((cond, cidx) => {
      const row = document.createElement('div');
      row.className = 'condition-row';

      const fieldSel = document.createElement('select');
      fieldSel.className = 'form-control cond-field';
      ['filename', 'extension', 'path', 'mime_type', 'size'].forEach(f => {
        const opt = document.createElement('option');
        opt.value = f;
        opt.textContent = f;
        fieldSel.appendChild(opt);
      });
      fieldSel.value = cond.field || 'filename';
      fieldSel.addEventListener('change', () => {
        rules[index].conditions[cidx].field = fieldSel.value;
      });

      const opSel = document.createElement('select');
      opSel.className = 'form-control cond-op';
      const ops = [
        ['equals', 'equals'],
        ['contains', 'contains'],
        ['starts_with', 'starts with'],
        ['ends_with', 'ends with'],
        ['matches_regex', 'matches regex'],
        ['greater_than', '>'],
        ['less_than', '<']
      ];
      ops.forEach(([val, label]) => {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = label;
        opSel.appendChild(opt);
      });
      opSel.value = cond.operator || 'equals';
      opSel.addEventListener('change', () => {
        rules[index].conditions[cidx].operator = opSel.value;
      });

      const valInput = document.createElement('input');
      valInput.type = 'text';
      valInput.className = 'form-control cond-value';
      valInput.value = cond.value || '';
      valInput.placeholder = 'value';
      valInput.addEventListener('input', () => {
        rules[index].conditions[cidx].value = valInput.value;
      });

      const remBtn = document.createElement('button');
      remBtn.className = 'cond-remove';
      remBtn.textContent = '×';
      remBtn.title = 'Remove condition';
      remBtn.addEventListener('click', () => {
        rules[index].conditions.splice(cidx, 1);
        renderRules();
      });

      row.appendChild(fieldSel);
      row.appendChild(opSel);
      row.appendChild(valInput);
      row.appendChild(remBtn);
      condsContainer.appendChild(row);
    });

    const addCondBtn = document.createElement('button');
    addCondBtn.className = 'btn-add-cond';
    addCondBtn.textContent = '+ Add condition';
    addCondBtn.addEventListener('click', () => {
      rules[index].conditions = rules[index].conditions || [];
      rules[index].conditions.push({ field: 'extension', operator: 'equals', value: '' });
      renderRules();
    });

    // Action
    const actionDiv = document.createElement('div');
    actionDiv.className = 'rule-action';

    const actionRow = document.createElement('div');
    actionRow.className = 'action-row';

    const actionType = document.createElement('select');
    actionType.className = 'form-control action-type';
    [['move_to', 'Move to'], ['skip', 'Skip']].forEach(([val, label]) => {
      const opt = document.createElement('option');
      opt.value = val;
      opt.textContent = label;
      actionType.appendChild(opt);
    });
    actionType.value = (rule.action && rule.action.type) || 'move_to';
    actionType.addEventListener('change', () => {
      rules[index].action = rules[index].action || {};
      rules[index].action.type = actionType.value;
      renderRules();
    });

    actionRow.appendChild(actionType);

    if (actionType.value === 'move_to') {
      const targetInput = document.createElement('input');
      targetInput.type = 'text';
      targetInput.className = 'form-control action-target';
      targetInput.value = (rule.action && rule.action.target) || '';
      targetInput.placeholder = 'Category name';
      targetInput.addEventListener('input', () => {
        rules[index].action = rules[index].action || {};
        rules[index].action.target = targetInput.value;
      });
      actionRow.appendChild(targetInput);
    }

    actionDiv.appendChild(actionRow);

    // Controls (up/down)
    const controls = document.createElement('div');
    controls.className = 'rule-controls';

    const upBtn = document.createElement('button');
    upBtn.textContent = '↑ Up';
    upBtn.disabled = index === 0;
    upBtn.addEventListener('click', () => {
      if (index > 0) {
        [rules[index], rules[index - 1]] = [rules[index - 1], rules[index]];
        renderRules();
      }
    });

    const downBtn = document.createElement('button');
    downBtn.textContent = '↓ Down';
    downBtn.disabled = index === rules.length - 1;
    downBtn.addEventListener('click', () => {
      if (index < rules.length - 1) {
        [rules[index], rules[index + 1]] = [rules[index + 1], rules[index]];
        renderRules();
      }
    });

    controls.appendChild(upBtn);
    controls.appendChild(downBtn);

    card.appendChild(header);
    card.appendChild(condsTitle);
    card.appendChild(condsContainer);
    card.appendChild(addCondBtn);
    card.appendChild(actionDiv);
    card.appendChild(controls);

    rulesList.appendChild(card);
  });
}

btnAddRule.addEventListener('click', () => {
  rules.push(createEmptyRule());
  renderRules();
});

btnSaveRules.addEventListener('click', async () => {
  for (const rule of rules) {
    if (!rule.name || !rule.name.trim()) {
      alert('All rules must have a name.');
      return;
    }
    if (rule.action && rule.action.type === 'move_to' && (!rule.action.target || !rule.action.target.trim())) {
      alert('Rule "' + rule.name + '" needs a target category.');
      return;
    }
    // Normalize extension values: strip leading dots so ".pdf" becomes "pdf"
    for (const cond of rule.conditions || []) {
      if (cond.field === 'extension' && cond.value) {
        cond.value = cond.value.replace(/^\.+/, '');
      }
    }
  }
  try {
    await invoke('save_rules', { rules });
    alert('Rules saved.');
  } catch (e) {
    alert('Failed to save rules: ' + e);
  }
});

btnTestRules.addEventListener('click', async () => {
  const name = testFilename.value.trim();
  if (!name) {
    testResults.innerHTML = '<div class="test-result-item unmatched"><span class="match-icon">○</span> Enter a filename to test.</div>';
    return;
  }
  try {
    const results = await invoke('test_rules', { fileName: name, rules });
    testResults.innerHTML = '';
    results.forEach((matched, idx) => {
      const rule = rules[idx];
      const div = document.createElement('div');
      div.className = 'test-result-item ' + (matched ? 'matched' : 'unmatched');
      div.innerHTML = '<span class="match-icon">' + (matched ? '✓' : '○') + '</span>' + escapeHtml(rule.name || 'Unnamed');
      testResults.appendChild(div);
    });
  } catch (e) {
    testResults.innerHTML = '<div class="test-result-item unmatched"><span class="match-icon">!</span> Error: ' + escapeHtml(String(e)) + '</div>';
  }
});
