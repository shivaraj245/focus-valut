let isTracking = true;

document.addEventListener('DOMContentLoaded', async () => {
  await loadStatus();
  await loadSettings();
  
  setInterval(loadStatus, 2000);
  
  document.getElementById('toggleBtn').addEventListener('click', toggleTracking);
  document.getElementById('settingsBtn').addEventListener('click', showSettings);
  document.getElementById('closeSettings').addEventListener('click', hideSettings);
  document.getElementById('saveSettings').addEventListener('click', saveSettings);
  document.getElementById('dashboardBtn').addEventListener('click', openDashboard);
});

async function loadStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });
    
    isTracking = response.isTracking;
    
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const toggleBtn = document.getElementById('toggleBtn');
    
    if (isTracking) {
      statusDot.classList.remove('paused');
      statusText.textContent = 'Tracking Active';
      toggleBtn.textContent = 'Pause Tracking';
      toggleBtn.classList.add('btn-primary');
      toggleBtn.classList.remove('btn-secondary');
    } else {
      statusDot.classList.add('paused');
      statusText.textContent = 'Tracking Paused';
      toggleBtn.textContent = 'Resume Tracking';
      toggleBtn.classList.remove('btn-primary');
      toggleBtn.classList.add('btn-secondary');
    }
    
    if (response.currentTab) {
      document.getElementById('tabTitle').textContent = response.currentTab.title || 'Untitled';
      document.getElementById('tabDomain').textContent = response.currentTab.domain;
      
      const duration = Math.floor((Date.now() - response.currentTab.startTime) / 1000);
      document.getElementById('tabDuration').textContent = formatDuration(duration);
    } else {
      document.getElementById('tabTitle').textContent = 'No active page';
      document.getElementById('tabDomain').textContent = '';
      document.getElementById('tabDuration').textContent = '';
    }
    
    if (response.lastSync) {
      const timeSince = Math.floor((Date.now() - response.lastSync) / 1000);
      document.getElementById('syncStatus').textContent = `Last sync: ${formatDuration(timeSince)} ago`;
    }
    
    document.getElementById('queuedEvents').textContent = `${response.queuedEvents} queued`;
    
    await loadTodayStats();
    
  } catch (error) {
    console.error('Error loading status:', error);
  }
}

async function loadTodayStats() {
  try {
    const settings = await chrome.storage.local.get(['apiUrl', 'userId']);
    const apiUrl = settings.apiUrl || 'http://localhost:8000/api';
    const userId = settings.userId || 1;
    
    const today = new Date().toISOString().split('T')[0];
    
    const response = await fetch(`${apiUrl}/analytics/${userId}/daily?date=${today}`);
    
    if (response.ok) {
      const data = await response.json();
      document.getElementById('todayEvents').textContent = data.total_events || 0;
      document.getElementById('learningTime').textContent = formatMinutes(data.learning_time_minutes || 0);
    }
  } catch (error) {
    console.log('Could not load stats (backend may be offline)');
  }
}

async function toggleTracking() {
  const response = await chrome.runtime.sendMessage({ type: 'TOGGLE_TRACKING' });
  isTracking = response.isTracking;
  await loadStatus();
}

function showSettings() {
  document.getElementById('settingsPanel').style.display = 'block';
}

function hideSettings() {
  document.getElementById('settingsPanel').style.display = 'none';
}

async function loadSettings() {
  const settings = await chrome.storage.local.get(['apiUrl', 'userId']);
  document.getElementById('apiUrl').value = settings.apiUrl || 'http://localhost:8000/api';
  document.getElementById('userId').value = settings.userId || 1;
}

async function saveSettings() {
  const apiUrl = document.getElementById('apiUrl').value;
  const userId = parseInt(document.getElementById('userId').value);
  
  await chrome.runtime.sendMessage({
    type: 'UPDATE_SETTINGS',
    settings: { apiUrl, userId }
  });
  
  hideSettings();
  
  const notification = document.createElement('div');
  notification.textContent = 'Settings saved!';
  notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #10b981; color: white; padding: 12px 20px; border-radius: 8px; font-weight: 600; z-index: 1000;';
  document.body.appendChild(notification);
  
  setTimeout(() => notification.remove(), 2000);
}

function openDashboard() {
  chrome.storage.local.get(['apiUrl'], (settings) => {
    const dashboardUrl = (settings.apiUrl || 'http://localhost:8000').replace('/api', '');
    chrome.tabs.create({ url: `${dashboardUrl.replace(':8000', ':3000')}` });
  });
}

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function formatMinutes(minutes) {
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
