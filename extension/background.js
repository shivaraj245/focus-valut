const API_BASE_URL = 'http://localhost:8000/api';
const TRACKING_INTERVAL = 30000; // 30 seconds
const IDLE_THRESHOLD = 60; // seconds

let currentTab = null;
let tabStartTime = null;
let isTracking = true;
let userId = 1; // Default user, should be set via login

const activeTabData = new Map();

chrome.runtime.onInstalled.addListener(() => {
  console.log('FocusVault Extension Installed');
  
  chrome.storage.local.set({
    isTracking: true,
    userId: 1,
    apiUrl: API_BASE_URL
  });
  
  chrome.alarms.create('trackingAlarm', { periodInMinutes: 0.5 });
});

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  await handleTabChange(activeInfo.tabId);
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.active) {
    await handleTabChange(tabId);
  }
});

chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) {
    await saveCurrentTabData();
    currentTab = null;
  } else {
    const [tab] = await chrome.tabs.query({ active: true, windowId: windowId });
    if (tab) {
      await handleTabChange(tab.id);
    }
  }
});

async function handleTabChange(tabId) {
  const settings = await chrome.storage.local.get(['isTracking']);
  if (!settings.isTracking) return;
  
  await saveCurrentTabData();
  
  const tab = await chrome.tabs.get(tabId);
  
  if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
    currentTab = null;
    return;
  }
  
  currentTab = {
    id: tab.id,
    url: tab.url,
    title: tab.title,
    domain: new URL(tab.url).hostname,
    startTime: Date.now()
  };
  
  tabStartTime = Date.now();
}

async function saveCurrentTabData() {
  if (!currentTab || !tabStartTime) return;
  
  const duration = Math.floor((Date.now() - tabStartTime) / 1000);
  
  if (duration < 5) return;
  
  const eventData = {
    url: currentTab.url,
    title: currentTab.title,
    domain: currentTab.domain,
    duration_seconds: duration,
    hour_of_day: new Date().getHours()
  };
  
  await sendEventToBackend(eventData);
  
  currentTab = null;
  tabStartTime = null;
}

async function sendEventToBackend(eventData) {
  try {
    const settings = await chrome.storage.local.get(['userId', 'apiUrl']);
    const apiUrl = settings.apiUrl || API_BASE_URL;
    const userId = settings.userId || 1;
    
    const response = await fetch(`${apiUrl}/events/${userId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(eventData)
    });
    
    if (response.ok) {
      const result = await response.json();
      console.log('Event tracked:', result);
      
      await chrome.storage.local.set({
        lastSync: Date.now(),
        lastEvent: eventData
      });
      
      chrome.runtime.sendMessage({
        type: 'EVENT_TRACKED',
        data: result
      }).catch(() => {});
      
    } else {
      console.error('Failed to track event:', response.statusText);
      await queueOfflineEvent(eventData);
    }
  } catch (error) {
    console.error('Error sending event:', error);
    await queueOfflineEvent(eventData);
  }
}

async function queueOfflineEvent(eventData) {
  const { offlineQueue = [] } = await chrome.storage.local.get('offlineQueue');
  offlineQueue.push({
    ...eventData,
    timestamp: Date.now()
  });
  
  if (offlineQueue.length > 100) {
    offlineQueue.shift();
  }
  
  await chrome.storage.local.set({ offlineQueue });
}

async function syncOfflineEvents() {
  const { offlineQueue = [] } = await chrome.storage.local.get('offlineQueue');
  
  if (offlineQueue.length === 0) return;
  
  console.log(`Syncing ${offlineQueue.length} offline events`);
  
  const synced = [];
  
  for (const event of offlineQueue) {
    try {
      await sendEventToBackend(event);
      synced.push(event);
    } catch (error) {
      break;
    }
  }
  
  if (synced.length > 0) {
    const remaining = offlineQueue.filter(e => !synced.includes(e));
    await chrome.storage.local.set({ offlineQueue: remaining });
  }
}

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'trackingAlarm') {
    await syncOfflineEvents();
    
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (activeTab && currentTab && activeTab.id === currentTab.id) {
      console.log('Still tracking:', currentTab.domain);
    }
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_STATUS') {
    chrome.storage.local.get(['isTracking', 'lastSync', 'lastEvent', 'offlineQueue'], (data) => {
      sendResponse({
        isTracking: data.isTracking ?? true,
        lastSync: data.lastSync,
        lastEvent: data.lastEvent,
        queuedEvents: (data.offlineQueue || []).length,
        currentTab: currentTab
      });
    });
    return true;
  }
  
  if (message.type === 'TOGGLE_TRACKING') {
    chrome.storage.local.get(['isTracking'], async (data) => {
      const newState = !data.isTracking;
      await chrome.storage.local.set({ isTracking: newState });
      
      if (!newState) {
        await saveCurrentTabData();
      }
      
      sendResponse({ isTracking: newState });
    });
    return true;
  }
  
  if (message.type === 'UPDATE_SETTINGS') {
    chrome.storage.local.set(message.settings, () => {
      sendResponse({ success: true });
    });
    return true;
  }
});

chrome.runtime.onSuspend.addListener(async () => {
  await saveCurrentTabData();
});
