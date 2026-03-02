# FocusVault Chrome Extension

A Chrome extension that tracks your browsing activity and identifies learning patterns.

## Features

- ✅ **Automatic Tracking**: Monitors active tabs and time spent
- ✅ **Smart Detection**: Only tracks meaningful page visits (5+ seconds)
- ✅ **Offline Support**: Queues events when backend is unavailable
- ✅ **Privacy First**: Skip chrome:// and extension pages
- ✅ **Real-time Sync**: Sends data to backend every 30 seconds
- ✅ **Beautiful UI**: Modern popup with stats and controls

## Installation

### 1. Load Extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `extension` folder from this project
5. The FocusVault icon should appear in your toolbar

### 2. Configure Settings

1. Click the FocusVault icon in toolbar
2. Click "Settings"
3. Set your API URL (default: `http://localhost:8000/api`)
4. Set your User ID (default: `1`)
5. Click "Save"

## How It Works

### Tracking Logic

```
1. User switches to a new tab
2. Extension records: URL, title, domain, start time
3. When user leaves tab (or after 30s), calculate duration
4. If duration >= 5 seconds, send event to backend
5. Backend runs ML classification
6. Event stored in database
```

### Data Collected

```javascript
{
  url: "https://example.com/article",
  title: "How to Learn DSA",
  domain: "example.com",
  duration_seconds: 180,
  hour_of_day: 14
}
```

### Offline Mode

- Events are queued locally if backend is unavailable
- Automatic retry every 30 seconds
- Max 100 events in queue (FIFO)

## Files Structure

```
extension/
├── manifest.json       # Extension configuration
├── background.js       # Service worker (tracking logic)
├── content.js         # Page content extraction
├── popup.html         # Extension popup UI
├── popup.css          # Popup styling
├── popup.js           # Popup functionality
└── icons/            # Extension icons (16, 48, 128)
```

## Usage

### Start Tracking
- Extension tracks automatically once installed
- Green dot = Active tracking
- Red dot = Paused

### Pause/Resume
- Click extension icon
- Click "Pause Tracking" / "Resume Tracking"

### View Stats
- Click extension icon to see:
  - Current page being tracked
  - Pages tracked today
  - Learning time today
  - Sync status
  - Queued events

### Access Dashboard
- Click "Dashboard" button in popup
- Opens web dashboard at `http://localhost:3000`

## Development

### Testing

1. Make changes to extension files
2. Go to `chrome://extensions/`
3. Click refresh icon on FocusVault card
4. Test changes

### Debugging

- **Background Script**: `chrome://extensions/` → FocusVault → "service worker"
- **Popup**: Right-click popup → "Inspect"
- **Content Script**: Open DevTools on any page → Console

### Common Issues

**Extension not tracking:**
- Check if tracking is enabled (green dot)
- Verify API URL in settings
- Check background script console for errors

**Events not reaching backend:**
- Ensure backend is running on `http://localhost:8000`
- Check network tab in background script console
- Look for queued events in popup

**Popup not loading:**
- Check popup.js console for errors
- Verify all files are in extension folder

## API Integration

### Endpoint Used

```
POST /api/events/{user_id}

Body:
{
  "url": "string",
  "title": "string",
  "domain": "string",
  "duration_seconds": number,
  "hour_of_day": number
}

Response:
{
  "id": number,
  "activity_label": "learning" | "work" | "entertainment",
  "activity_probs": {...},
  "topic_id": number,
  "topic_name": "string"
}
```

## Privacy & Permissions

### Required Permissions

- `tabs`: Access tab information (URL, title)
- `storage`: Store settings and offline queue
- `alarms`: Periodic sync
- `activeTab`: Track active tab
- `<all_urls>`: Monitor all websites

### Data Privacy

- All data stored locally and on your backend
- No third-party services
- No cloud storage
- You control what domains to track

## Future Enhancements

- [ ] Domain whitelist/blacklist
- [ ] Manual "Save to Knowledge Base" button
- [ ] Page content extraction for RAG
- [ ] Activity breakdown charts in popup
- [ ] Export tracked data
- [ ] Multi-user support with login

## License

Part of FocusVault B.Tech Final Year Project
