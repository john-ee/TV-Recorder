# 📺 TV Recorder

A web-based application for scheduling and recording TV programs from HLS streams using EPG (Electronic Program Guide) data.

## Features

- 📅 **EPG Integration** - Browse TV programs from XMLTV guide data
- 🎯 **Smart Scheduling** - Schedule recordings with automatic 10-minute buffer
- 📺 **Multi-view Interface** - Card and grid views for program browsing
- 🔔 **Discord Notifications** - Get notified when recordings start, complete, or fail
- ⏺️ **Live Monitoring** - Track active and scheduled recordings in real-time
- ✏️ **Flexible Management** - Rename or cancel scheduled recordings
- 🔍 **Search & Filter** - Find programs by channel, date, or keyword

## Prerequisites

- Docker
- Docker Compose

## Quick Start

### 1. Clone or Download

Download all the project files to a directory.

### 2. Create Configuration Files

**Create `channels.json`:**

```json
{
  "channels": [],
  "settings": {
    "output_dir": "/recordings",
    "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
  }
}
```

### 3. Set Environment Variables

Create a `.env` file (optional):

```bash
# Optional: Discord webhook for notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
EPG_URL=url
```

### 4. Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f
```

The application will be available at `http://localhost:5020`

## Configuration

### Channels Configuration

Edit `channels.json` to add your TV channels:

```json
{
  "channels": [
    {
      "id": "Channel 1",
      "name": "Channel 1",
      "xmltv_id": "channel1.com",
      "stream_url": "https://example.com/channel1.m3u8",
      "subtitle_url": null,
      "enabled": true
    }
  ],
  "settings": {
    "output_dir": "/recordings",
    "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
  }
}
```

**Channel Properties:**
- `id` - Unique channel identifier
- `name` - Display name
- `xmltv_id` - Channel ID from your EPG source
- `stream_url` - HLS stream URL (m3u8)
- `subtitle_url` - Optional subtitle stream
- `enabled` - Whether to show this channel (true/false)

### Environment Variables

Edit `docker-compose.yml` or `.env`:

- `EPG_URL` - XMLTV EPG data URL (necessary to schedule your recordings)
- `DISCORD_WEBHOOK_URL` - Discord webhook for notifications (optional)
- `TZ` - Timezone (default: Europe/Paris)

### Storage

Recordings are saved to `/dump/conversions/disks` by default. Change this in `docker-compose.yml`:

```yaml
volumes:
  - /your/recordings/path:/recordings
```

## Usage

### Browsing Programs

1. Navigate to the **Guide TV** tab
2. Use filters to find programs:
   - **Channel filter** - Show specific channels
   - **Date filter** - Today, tomorrow, or future days
   - **Search** - Search by title or description
3. Switch between **Cards** and **Grid** views

### Scheduling Recordings

1. Find a program in the guide
2. Click the **Enregistrer** button (or click a program in grid view)
3. Confirm the recording
4. A 10-minute buffer is automatically added before and after

### Managing Recordings

Navigate to the **Enregistrements** tab to:
- View **active recordings** currently in progress
- See **scheduled recordings** with start times
- **Rename** recordings using the ✏️ button
- **Cancel** recordings using the ✕ button

### Discord Notifications

If configured, you'll receive Discord notifications for:
- 🔴 **Recording Started** - When a recording begins
- ✅ **Recording Completed** - With file size and duration
- ❌ **Recording Failed** - With error details

## Docker Commands

```bash
# Start the service
docker-compose up -d

# Stop the service
docker-compose down

# View logs
docker-compose logs -f tv-recorder

# Restart the service
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build

# Check service status
docker-compose ps
```

## File Structure

```
.
├── app.py                  # Flask application
├── record.sh               # Recording script
├── channels.json           # Channel configuration
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose configuration
├── templates/
│   └── index.html         # Web interface
└── data/                  # Persistent data (created at runtime)
    ├── epg_cache.xml      # Cached EPG data
    └── schedules.json     # Scheduled recordings
```

## Troubleshooting

### Recordings Not Starting

- Check that the scheduled time hasn't passed
- Verify the stream URL is accessible
- Check logs: `docker-compose logs -f`

### EPG Not Loading

- Verify `EPG_URL` is accessible
- Check network connectivity from container
- EPG cache refreshes every hour

### Permission Issues

Ensure the recordings directory has proper permissions:

```bash
chmod 755 /dump/conversions/disks
```

## Technical Details

### Recording Process

1. Schedules are checked every 10 seconds
2. Recordings start within 30 seconds of scheduled time
3. FFmpeg captures the HLS stream with:
   - Automatic reconnection on errors
   - Video and audio copy (no re-encoding)
   - MKV container format

### Data Persistence

- EPG cache stored in `./data/epg_cache.xml`
- Schedules stored in `./data/schedules.json`
- Survives container restarts

## License

This project is provided as-is for personal use.

## Credits

- Built with Flask and FFmpeg
- Uses XMLTV for EPG data