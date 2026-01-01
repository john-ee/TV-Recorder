#!/usr/bin/env python3
"""
TV Recorder Web Application
Simple architecture: Python manages everything, bash script just records
"""

from flask import Flask, render_template, jsonify, request
import xml.etree.ElementTree as ET
import requests
import subprocess
import os
import threading
import time
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Configuration
EPG_URL = "https://xmltvfr.fr/xmltv/xmltv_tnt.xml"
EPG_CACHE_FILE = "/tmp/epg_cache.xml"
EPG_CACHE_DURATION = 3600  # 1 hour
RECORD_SCRIPT = "/app/record.sh"
CHANNELS_CONFIG = "/app/channels.json"
SCHEDULES_FILE = "/tmp/schedules.json"

# Load channel configuration
channels = {}
settings = {}

def load_channels():
    """Load channel configuration from JSON"""
    global channels, settings
    try:
        with open(CHANNELS_CONFIG, 'r') as f:
            config = json.load(f)
            # Convert list to dict keyed by xmltv_id for easy lookup
            channels = {ch['xmltv_id']: ch for ch in config['channels'] if ch.get('enabled', True)}
            settings = config.get('settings', {})
            print(f"Loaded {len(channels)} channels")
    except Exception as e:
        print(f"Error loading channels config: {e}")
        channels = {}
        settings = {}

# In-memory schedules (persisted to file)
scheduled_recordings = []
active_recordings = {}

def load_schedules():
    """Load schedules from file"""
    global scheduled_recordings
    if os.path.exists(SCHEDULES_FILE):
        try:
            with open(SCHEDULES_FILE, 'r') as f:
                scheduled_recordings = json.load(f)
        except:
            scheduled_recordings = []
    else:
        scheduled_recordings = []

def save_schedules():
    """Save schedules to file"""
    with open(SCHEDULES_FILE, 'w') as f:
        json.dump(scheduled_recordings, f, indent=2)

def get_epg_data():
    """Fetch and cache EPG data"""
    # Check cache
    if os.path.exists(EPG_CACHE_FILE):
        cache_age = time.time() - os.path.getmtime(EPG_CACHE_FILE)
        if cache_age < EPG_CACHE_DURATION:
            with open(EPG_CACHE_FILE, 'r') as f:
                return f.read()
    
    # Fetch fresh data
    try:
        response = requests.get(EPG_URL, timeout=10)
        response.raise_for_status()
        
        # Cache it
        with open(EPG_CACHE_FILE, 'w') as f:
            f.write(response.text)
        
        return response.text
    except Exception as e:
        print(f"Error fetching EPG: {e}")
        # Try to use old cache
        if os.path.exists(EPG_CACHE_FILE):
            with open(EPG_CACHE_FILE, 'r') as f:
                return f.read()
        return None

def parse_epg(xml_data):
    """Parse XMLTV data and return programs"""
    if not xml_data:
        return []
    
    try:
        root = ET.fromstring(xml_data)
        programs = []
        
        for programme in root.findall('programme'):
            channel_id = programme.get('channel')
            
            # Only include channels we have configured
            if channel_id not in channels:
                continue
            
            channel = channels[channel_id]
            
            start = programme.get('start')
            stop = programme.get('stop')
            
            # Parse times
            start_dt = datetime.strptime(start[:14], '%Y%m%d%H%M%S')
            stop_dt = datetime.strptime(stop[:14], '%Y%m%d%H%M%S')
            
            title_elem = programme.find('title')
            title = title_elem.text if title_elem is not None else "Unknown"
            
            desc_elem = programme.find('desc')
            desc = desc_elem.text if desc_elem is not None else ""
            
            category_elem = programme.find('category')
            category = category_elem.text if category_elem is not None else ""
            
            programs.append({
                'channel_id': channel_id,
                'channel_name': channel['name'],
                'channel_key': channel['id'],
                'title': title,
                'description': desc,
                'category': category,
                'start': start_dt.isoformat(),
                'stop': stop_dt.isoformat(),
                'start_display': start_dt.strftime('%H:%M'),
                'stop_display': stop_dt.strftime('%H:%M'),
                'date_display': start_dt.strftime('%Y-%m-%d'),
                'duration': int((stop_dt - start_dt).total_seconds()),
                'stream_url': channel['stream_url']
            })
        
        return programs
    except Exception as e:
        print(f"Error parsing EPG: {e}")
        return []

def start_recording(schedule):
    """Execute a recording"""
    recording_id = schedule['id']
    channel_id = schedule['channel']
    title = schedule['title']
    duration = schedule['duration']
    stream_url = schedule['stream_url']
    
    # Find channel info
    channel_info = None
    for ch in channels.values():
        if ch['id'] == channel_id:
            channel_info = ch
            break
    
    if not channel_info:
        print(f"Error: Channel {channel_id} not found in config")
        return
    
    channel_name = channel_info['name']
    
    print(f"Starting recording: {title} on {channel_name}")
    
    try:
        # Build output filename
        output_dir = settings.get('output_dir', '/recordings')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Sanitize title for filename
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        safe_title = safe_title.replace(' ', '_')
        output_file = f"{output_dir}/{channel_id}-{safe_title}-{timestamp}.mkv"
        
        # Build command
        cmd = [
            RECORD_SCRIPT,
            '-u', stream_url,
            '-d', str(duration),
            '-o', output_file,
            '-a', settings.get('user_agent', 'Mozilla/5.0')
        ]
        
        # Start recording process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Track active recording
        active_recordings[recording_id] = {
            'pid': process.pid,
            'title': title,
            'channel': channel_name,
            'started': datetime.now().isoformat(),
            'output_file': output_file
        }
        
        print(f"Recording started with PID: {process.pid}")
        print(f"Output: {output_file}")
        
        # Wait for process to complete (in background)
        def wait_for_completion():
            stdout, _ = process.communicate()
            if stdout:
                print(f"Recording output: {stdout}")
            if recording_id in active_recordings:
                del active_recordings[recording_id]
            print(f"Recording completed: {title}")
        
        threading.Thread(target=wait_for_completion, daemon=True).start()
        
    except Exception as e:
        print(f"Error starting recording: {e}")
        import traceback
        traceback.print_exc()

def scheduler_thread():
    """Background thread that checks for scheduled recordings"""
    print("Scheduler thread started")
    
    while True:
        try:
            now = datetime.now()
            
            # Check each scheduled recording
            for schedule in scheduled_recordings[:]:
                start_dt = datetime.fromisoformat(schedule['start'])
                
                # If it's time to start (within 30 seconds)
                time_diff = (start_dt - now).total_seconds()
                
                if -30 <= time_diff <= 30:
                    print(f"Time to record: {schedule['title']}")
                    start_recording(schedule)
                    scheduled_recordings.remove(schedule)
                    save_schedules()
                
                # Remove old schedules (more than 2 hours past)
                elif time_diff < -7200:
                    print(f"Removing old schedule: {schedule['title']}")
                    scheduled_recordings.remove(schedule)
                    save_schedules()
            
        except Exception as e:
            print(f"Scheduler error: {e}")
        
        # Check every 10 seconds
        time.sleep(10)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/channels')
def api_channels():
    """Get list of configured channels"""
    return jsonify([ch for ch in channels.values()])

@app.route('/api/epg')
def api_epg():
    """Get EPG data"""
    xml_data = get_epg_data()
    programs = parse_epg(xml_data)
    
    # Filter for today and next 7 days
    now = datetime.now()
    end = now + timedelta(days=7)
    
    filtered = [p for p in programs if now <= datetime.fromisoformat(p['start']) <= end]
    
    # Sort by start time
    filtered.sort(key=lambda x: x['start'])
    
    print(f"Returning {len(filtered)} programs")
    
    return jsonify(filtered)

@app.route('/api/recordings')
def api_recordings():
    """Get scheduled and active recordings"""
    return jsonify({
        'scheduled': scheduled_recordings,
        'active': list(active_recordings.values())
    })

@app.route('/api/schedule', methods=['POST'])
def api_schedule():
    """Schedule a new recording"""
    data = request.json
    
    channel_id = data.get('channel')
    title = data.get('title')
    start_time = data.get('start')
    duration = data.get('duration')
    stream_url = data.get('stream_url')
    
    if not all([channel_id, title, start_time, duration, stream_url]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Parse start time
    start_dt = datetime.fromisoformat(start_time)
    
    # Add 10 minutes buffer before and after
    buffer_minutes = 10
    adjusted_start = start_dt - timedelta(minutes=buffer_minutes)
    adjusted_duration = duration + (buffer_minutes * 2 * 60)  # Add 20 minutes total (10 before + 10 after)
    
    # Check if recording is in the past
    if adjusted_start < datetime.now() - timedelta(minutes=5):
        return jsonify({'error': 'Cannot schedule recordings in the past'}), 400
    
    # Create schedule
    recording_id = f"{channel_id}_{adjusted_start.strftime('%Y%m%d_%H%M%S')}"
    
    schedule = {
        'id': recording_id,
        'channel': channel_id,
        'title': title,
        'start': adjusted_start.isoformat(),
        'original_start': start_time,
        'duration': adjusted_duration,
        'original_duration': duration,
        'stream_url': stream_url,
        'created': datetime.now().isoformat(),
        'buffer_minutes': buffer_minutes
    }
    
    scheduled_recordings.append(schedule)
    save_schedules()
    
    print(f"Scheduled: {title} on {channel_id}")
    print(f"  Original: {start_dt.strftime('%Y-%m-%d %H:%M')} ({duration}s)")
    print(f"  Adjusted: {adjusted_start.strftime('%Y-%m-%d %H:%M')} ({adjusted_duration}s) [+{buffer_minutes}min buffer]")
    
    return jsonify({
        'success': True,
        'message': f'Recording scheduled for {adjusted_start.strftime("%Y-%m-%d %H:%M")} (+{buffer_minutes}min buffer)',
        'id': recording_id,
        'buffer_info': f'{buffer_minutes} minutes added before and after'
    })

@app.route('/api/schedule/<schedule_id>', methods=['DELETE'])
def api_delete_schedule(schedule_id):
    """Cancel a scheduled recording"""
    global scheduled_recordings
    scheduled_recordings = [s for s in scheduled_recordings if s['id'] != schedule_id]
    save_schedules()
    print(f"Cancelled schedule: {schedule_id}")
    return jsonify({'success': True})

# Initialize
load_channels()
load_schedules()

# Start scheduler thread
scheduler = threading.Thread(target=scheduler_thread, daemon=True)
scheduler.start()

if __name__ == '__main__':
    print("TV Recorder starting...")
    print(f"Loaded {len(channels)} channels")
    print(f"Loaded {len(scheduled_recordings)} scheduled recordings")
    app.run(host='0.0.0.0', port=5000, debug=False)