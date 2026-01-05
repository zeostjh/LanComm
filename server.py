import sys
import json
import asyncio
import numpy as np
import pyaudio
from collections import defaultdict, deque
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
    QFileDialog, QMessageBox, QComboBox, QScrollArea, QGroupBox, 
    QSlider, QFrame, QTabWidget, QSplitter, QGridLayout, QProgressBar, QDialog,
    QInputDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPalette, QColor, QFont
import logging
import socket
import threading
import time
from zeroconf import ServiceInfo, Zeroconf
import netifaces

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize PyAudio for device enumeration
try:
    p = pyaudio.PyAudio()
    logging.info(f"PyAudio initialized: {p.get_device_count()} audio devices found")
except Exception as e:
    logging.error(f"PyAudio initialization failed: {e}")
    p = None

# ===== CONFIGURATION =====
HOST = '0.0.0.0'
TCP_PORT = 6001  # HelixNet standard port for control and audio
UDP_PORT = 6001  # HelixNet uses same port 6001 for UDP audio
RATE = 48000
CHUNK = 960  # 20ms frames at 48kHz
JITTER_BUFFER_SIZE = 6  # Increased to 128ms (6 frames × 20ms) for HelixNet parity
MAX_CHANNELS = 10  # System-wide: maximum 10 channels available
MAX_USER_CHANNELS = 4  # Per beltpack: 4 physical buttons (can assign any 4 of the 10 channels)
MAX_USERS = 20  # User requirement: support 20 simultaneous users
AUTH_KEY = "lancomm-secure-2025"  # Authentication key (change in production!)
CONFIG_FILE = 'intercom_config.json'

# ===== GLOBAL STATE =====
users = {}  # {user_name: {'channels': set(), 'client_addr': None}}
channels = {}  # {ch_id: 'Channel Name'}
channel_volumes = {}  # {ch_id: 0.0-1.0}
channel_enabled = {}  # {ch_id: True/False} - admin can disable channels to save bandwidth
active_channel_count = 4  # Current active channels (min 1, max 10)
program_audio_device = None  # Selected audio input device for program audio
program_audio_channel = 0  # Selected channel from the device (0-based index)
device_names = {}  # {ip_addr: custom_name} - Admin-assigned device names

# 4-Wire interface configuration (supports 2 interfaces)
fourwire_enabled = [False, False]
fourwire_input_device = [None, None]
fourwire_output_device = [None, None]
fourwire_channel = [0, 1]  # Channels to bridge to
fourwire_input_gain = [0.8, 0.8]
fourwire_output_gain = [0.8, 0.8]
fourwire_stream_in: list = [None, None]
fourwire_stream_out: list = [None, None]
fourwire_thread: list = [None, None]
fourwire_running = [False, False]
client_data = {}
next_user_id = 0

# Audio buffers
# Structure: channel_buffers[ch_id][user_id] = deque([audio_chunk_1, audio_chunk_2, ...])
channel_buffers = defaultdict(lambda: defaultdict(lambda: deque(maxlen=10)))
channel_listeners = defaultdict(set)
channel_talkers = defaultdict(set)
channel_last_activity = defaultdict(float)
channel_seq_tracking = defaultdict(lambda: defaultdict(int))
channel_levels = defaultdict(float)  # Audio level for metering (0.0-1.0)
user_udp_addrs = {}  # {user_id: (ip, port)} for downlink audio

# Thread safety
config_lock = threading.RLock()
client_lock = threading.RLock()
audio_lock = threading.RLock()

# Node tracking (Rock Pi S belt packs)
active_nodes = {}  # {ip_addr: {'hostname': str, 'last_seen': float, 'user_name': str or None}}
node_lock = threading.RLock()
zeroconf_instance = None
zeroconf_service = None


# ===== CONFIGURATION MANAGEMENT =====

def load_config():
    """Load configuration from JSON file"""
    global users, channels, channel_volumes, program_audio_device, program_audio_channel, device_names, channel_enabled, active_channel_count
    with config_lock:
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                users = {k: {
                    'channels': list(v.get('channels', [])),
                    'button_modes': v.get('button_modes', {}),
                    'client_addr': None
                } for k, v in data.get('users', {}).items()}
                channels = {int(k): v for k, v in data.get('channels', {}).items()}
                channel_volumes = {int(k): float(v) for k, v in data.get('channel_volumes', {}).items()}
                channel_enabled = {int(k): bool(v) for k, v in data.get('channel_enabled', {}).items()}
                active_channel_count = int(data.get('active_channel_count', 6))
                program_audio_device = data.get('program_audio_device')
                program_audio_channel = int(data.get('program_audio_channel', 0))
                device_names = data.get('device_names', {})
                
                # Load 4-wire config (supports arrays for 2 interfaces)
                fw_enabled = data.get('fourwire_enabled', [False, False])
                fourwire_enabled = fw_enabled if isinstance(fw_enabled, list) else [fw_enabled, False]
                
                fw_input = data.get('fourwire_input_device', [None, None])
                fourwire_input_device = fw_input if isinstance(fw_input, list) else [fw_input, None]
                
                fw_output = data.get('fourwire_output_device', [None, None])
                fourwire_output_device = fw_output if isinstance(fw_output, list) else [fw_output, None]
                
                fw_ch = data.get('fourwire_channel', [0, 1])
                fourwire_channel = fw_ch if isinstance(fw_ch, list) else [fw_ch, 1]
                
                fw_in_gain = data.get('fourwire_input_gain', [0.8, 0.8])
                fourwire_input_gain = fw_in_gain if isinstance(fw_in_gain, list) else [fw_in_gain, 0.8]
                
                fw_out_gain = data.get('fourwire_output_gain', [0.8, 0.8])
                fourwire_output_gain = fw_out_gain if isinstance(fw_out_gain, list) else [fw_out_gain, 0.8]
                
                if not channels:
                    channels = {i: f'Channel {i+1}' for i in range(MAX_CHANNELS)}
                if not channel_volumes:
                    channel_volumes = {i: 0.8 for i in range(MAX_CHANNELS)}
                if not channel_enabled:
                    # Default: first 4 channels enabled
                    channel_enabled = {i: i < 4 for i in range(MAX_CHANNELS)}
                
                # VALIDATION: Enforce minimum 1 channel enabled
                active_count = sum(channel_enabled.values())
                if active_count < 1:
                    logging.warning(f"Config has {active_count} channels enabled, enforcing minimum of 1")
                    # Enable first channel if none are enabled
                    channel_enabled[0] = True
                    active_count = sum(channel_enabled.values())
                    
                logging.info(f"✓ Loaded: {len(users)} users, {active_count} of {len(channels)} channels active")
        except FileNotFoundError:
            logging.info("Creating default configuration...")
            channels = {i: f'Channel {i+1}' for i in range(MAX_CHANNELS)}
            channel_volumes = {i: 0.8 for i in range(MAX_CHANNELS)}
            channel_enabled = {i: i < 4 for i in range(MAX_CHANNELS)}  # Default: 4 channels enabled
            active_channel_count = 4
            save_config()
        except Exception as e:
            logging.error(f"Load error: {e}")
            channels = {i: f'Channel {i+1}' for i in range(MAX_CHANNELS)}
            channel_volumes = {i: 0.8 for i in range(MAX_CHANNELS)}
            channel_enabled = {i: i < 4 for i in range(MAX_CHANNELS)}
            active_channel_count = 4


def save_config():
    """Save configuration to JSON file"""
    with config_lock:
        data = {
            'users': {k: {
                'channels': list(v['channels']),
                'button_modes': v.get('button_modes', {})
            } for k, v in users.items()},
            'channels': {str(k): v for k, v in channels.items()},
            'channel_volumes': {str(k): v for k, v in channel_volumes.items()},
            'channel_enabled': {str(k): v for k, v in channel_enabled.items()},
            'active_channel_count': active_channel_count,
            'program_audio_device': program_audio_device,
            'program_audio_channel': program_audio_channel,
            'device_names': device_names,
            'fourwire_enabled': fourwire_enabled,
            'fourwire_input_device': fourwire_input_device,
            'fourwire_output_device': fourwire_output_device,
            'fourwire_channel': fourwire_channel,
            'fourwire_input_gain': fourwire_input_gain,
            'fourwire_output_gain': fourwire_output_gain
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logging.info("✓ Configuration saved")
        except Exception as e:
            logging.error(f"Save error: {e}")


# Initialize on startup
load_config()


# ===== NETWORK HANDLERS =====

async def handle_tcp(reader, writer):
    """Handle TCP control connections from clients"""
    addr = writer.get_extra_info('peername')
    user_id = None
    node_ip = addr[0]
    
    try:
        # Simple authentication handshake
        import hashlib
        challenge = str(time.time()).encode()
        writer.write(b"AUTH_CHALLENGE:" + challenge)
        await writer.drain()
        
        try:
            auth_response = await asyncio.wait_for(reader.read(1024), timeout=5.0)
            expected = hashlib.sha256(challenge + AUTH_KEY.encode()).hexdigest().encode()
            if auth_response != expected:
                logging.warning(f"Authentication failed from {addr}")
                writer.write(b"AUTH_FAIL")
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return
        except asyncio.TimeoutError:
            logging.warning(f"Authentication timeout from {addr}")
            writer.close()
            await writer.wait_closed()
            return
        
        global next_user_id
        with client_lock:
            user_id = next_user_id
            next_user_id += 1
            client_data[addr] = {
                'user_name': None, 
                'user_id': user_id, 
                'subscribed_channels': set(), 
                'sock': writer, 
                'last_seen': time.time(),
                'node_ip': node_ip
            }
        
        # Track this node
        with node_lock:
            if node_ip not in active_nodes:
                active_nodes[node_ip] = {
                    'hostname': f'node-{node_ip.split(".")[3]}',
                    'last_seen': time.time(),
                    'user_name': None
                }
        
        writer.write(f"USER_ID:{user_id}".encode())
        await writer.drain()
        logging.info(f"✓ Authenticated client {addr} as user_id {user_id}")
        
        while True:
            data = await reader.read(1024)
            if not data:
                break
                
            try:
                parts = data.decode().strip().split(':')
                cmd = parts[0]
                
                if cmd == 'GET_USERS':
                    with config_lock:
                        user_list = ','.join(users.keys())
                    writer.write(f"USERS:{user_list}".encode())
                    await writer.drain()
                
                elif cmd == 'SELECT_USER' and len(parts) >= 2:
                    user_name = parts[1]
                    with config_lock:
                        # Check user limit (HelixNet: 64-128, LanComm: 20)
                        active_user_count = sum(1 for c in client_data.values() if c.get('user_name'))
                        if active_user_count >= MAX_USERS and user_name not in [c.get('user_name') for c in client_data.values()]:
                            writer.write(b"ERROR:MAX_USERS_REACHED")
                            await writer.drain()
                            continue
                        
                        if user_name in users:
                            # Allow multiple belt packs to use same profile
                            with client_lock:
                                client_data[addr]['user_name'] = user_name
                                sub_channels = set([ch for ch in users[user_name]['channels'] if ch is not None])
                                client_data[addr]['subscribed_channels'] = sub_channels
                            # Refresh listener membership for this user_id
                            with audio_lock:
                                for ch_set in channel_listeners.values():
                                    ch_set.discard(user_id)
                                for ch in sub_channels:
                                    channel_listeners[ch].add(user_id)
                            
                            with node_lock:
                                if node_ip in active_nodes:
                                    active_nodes[node_ip]['user_name'] = user_name
                            
                            # Send channel names AND button modes - only for enabled channels
                            sub_channels_filtered = {ch for ch in sub_channels if channel_enabled.get(ch, False)}
                            ch_names = {str(ch): channels.get(ch, f'CH{ch}') for ch in sub_channels_filtered}
                            button_modes = users[user_name].get('button_modes', {})
                            config_data = {'channels': ch_names, 'button_modes': button_modes}
                            writer.write(f"CONFIG:{json.dumps(config_data)}".encode())
                        else:
                            writer.write(b"ERROR")
                    await writer.drain()
                
                elif cmd == 'TOGGLE_TALK' and len(parts) >= 3:
                    ch = int(parts[1])
                    enable = parts[2] == '1'
                    with client_lock:
                        subscribed = client_data.get(addr, {}).get('subscribed_channels', set())
                        if ch in subscribed:
                            with audio_lock:
                                if enable:
                                    channel_talkers[ch].add(user_id)
                                else:
                                    channel_talkers[ch].discard(user_id)
                
                elif cmd == 'ASSIGN_USER' and len(parts) >= 2:
                    # Server-initiated profile assignment
                    user_name = parts[1]
                    with config_lock:
                        if user_name in users:
                            users[user_name]['client_addr'] = addr
                            with client_lock:
                                client_data[addr]['user_name'] = user_name
                                sub_channels = set([ch for ch in users[user_name]['channels'] if ch is not None])
                                client_data[addr]['subscribed_channels'] = sub_channels
                            # Refresh listener membership for this user_id
                            with audio_lock:
                                for ch_set in channel_listeners.values():
                                    ch_set.discard(user_id)
                                for ch in sub_channels:
                                    channel_listeners[ch].add(user_id)
                            
                            with node_lock:
                                if node_ip in active_nodes:
                                    active_nodes[node_ip]['user_name'] = user_name
                            
                            # Send only enabled channels
                            sub_channels_filtered = {ch for ch in sub_channels if channel_enabled.get(ch, False)}
                            ch_names = {str(ch): channels.get(ch, f'CH{ch}') for ch in sub_channels_filtered}
                            writer.write(f"CONFIG:{json.dumps(ch_names)}".encode())
                        else:
                            writer.write(b"ERROR")
                    await writer.drain()
                
                elif cmd == 'PING':
                    with client_lock:
                        if addr in client_data:
                            client_data[addr]['last_seen'] = time.time()
                    with node_lock:
                        if node_ip in active_nodes:
                            active_nodes[node_ip]['last_seen'] = time.time()
                    writer.write(b"PONG")
                    await writer.drain()

                elif cmd == 'SET_UDP' and len(parts) >= 2:
                    # Client announces its UDP port for downstream audio
                    try:
                        udp_port = int(parts[1])
                        with client_lock:
                            client_data[addr]['udp_addr'] = (node_ip, udp_port)
                            user_udp_addrs[user_id] = (node_ip, udp_port)
                        writer.write(b"UDP_OK")
                    except Exception as e:
                        logging.error(f"SET_UDP parse error from {addr}: {e}")
                        writer.write(b"UDP_FAIL")
                    await writer.drain()
                    
            except Exception as e:
                logging.error(f"Command error: {e}")
    
    except Exception as e:
        logging.error(f"TCP error {addr}: {e}")
    
    finally:
        with client_lock:
            user_name = client_data.get(addr, {}).get('user_name')
            node_ip = client_data.get(addr, {}).get('node_ip')
        
        with audio_lock:
            for ch in list(channel_listeners.keys()):
                channel_listeners[ch].discard(user_id)
                if user_id is not None:
                    channel_talkers[ch].discard(user_id)

        # Remove cached UDP target
        with client_lock:
            if user_id is not None and user_id in user_udp_addrs:
                user_udp_addrs.pop(user_id, None)
        
        with node_lock:
            if node_ip and node_ip in active_nodes:
                active_nodes[node_ip]['user_name'] = None
                active_nodes[node_ip]['last_seen'] = time.time()
        
        with client_lock:
            if addr in client_data:
                del client_data[addr]
        
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass


async def tcp_server():
    """Start TCP server"""
    server = await asyncio.start_server(handle_tcp, HOST, TCP_PORT)
    async with server:
        await server.serve_forever()


async def receive_udp(udp_sock):
    """Receive and buffer audio packets"""
    loop = asyncio.get_running_loop()
    
    while True:
        try:
            data, addr = await loop.sock_recvfrom(udp_sock, 8192)
            if len(data) < 12:
                continue
            
            ch = int.from_bytes(data[0:4], 'big')
            user_id = int.from_bytes(data[4:8], 'big')
            seq = int.from_bytes(data[8:12], 'big')
            
            if ch < 0 or ch >= MAX_CHANNELS or user_id < 0 or user_id > 10000:
                continue

            # Drop audio for disabled channels
            with config_lock:
                if not channel_enabled.get(ch, False):
                    continue
            
            with audio_lock:
                if user_id not in channel_talkers.get(ch, set()):
                    continue
                
                last_seq = channel_seq_tracking[ch].get(user_id, -1)
                if last_seq >= 0 and seq != (last_seq + 1) % 65536:
                    # Simple loss detection
                    pass
                channel_seq_tracking[ch][user_id] = seq
            
            encoded = data[12:]
            if len(encoded) < 10:
                continue
            
            try:
                # Decode raw PCM (int16)
                audio_data = np.frombuffer(encoded, dtype=np.int16).astype(np.float32) / 32767.0
            except Exception as e:
                logging.error(f"PCM decode error: {e}")
                continue
            
            # Ensure correct chunk size
            if len(audio_data) < CHUNK:
                audio_data = np.pad(audio_data, (0, CHUNK - len(audio_data)))
            elif len(audio_data) > CHUNK:
                audio_data = audio_data[:CHUNK]
            
            with audio_lock:
                # Add to user's specific buffer queue
                channel_buffers[ch][user_id].append(audio_data)
                channel_last_activity[ch] = time.time()

            # Track the sender's UDP address for return audio
            with client_lock:
                user_udp_addrs[user_id] = addr
                for client in client_data.values():
                    if client.get('user_id') == user_id:
                        client['udp_addr'] = addr
                        break
        
        except Exception as e:
            logging.error(f"UDP RX: {e}")
            await asyncio.sleep(0.001)


async def mix_and_send(udp_sock):
    """Mix audio and send to listeners"""
    loop = asyncio.get_running_loop()
    last_cleanup = time.time()
    
    while True:
        try:
            current_time = time.time()
            
            if current_time - last_cleanup > 30:
                with audio_lock:
                    inactive = [ch for ch, t in channel_last_activity.items() 
                               if current_time - t > 60]
                    for ch in inactive:
                        channel_buffers.pop(ch, None)
                        channel_last_activity.pop(ch, None)
                        channel_seq_tracking.pop(ch, None)
                last_cleanup = current_time
            
            with audio_lock:
                channels_to_process = list(channel_buffers.keys())
            
            for ch in channels_to_process:
                # Skip disabled channels entirely
                with config_lock:
                    if not channel_enabled.get(ch, False):
                        continue
                with audio_lock:
                    if ch not in channel_buffers:
                        continue
                    
                    # Get active talkers and listeners
                    current_talkers = set(channel_talkers.get(ch, set()))
                    listeners = list(channel_listeners.get(ch, set()))
                    
                    if not listeners or not current_talkers:
                        # Drain buffers if no one is listening or talking
                        for uid in list(channel_buffers[ch].keys()):
                            if channel_buffers[ch][uid]:
                                channel_buffers[ch][uid].popleft()
                        continue

                    # Mix audio from all active talkers
                    mixed_audio = np.zeros(CHUNK, dtype=np.float32)
                    active_sources = 0
                    talker_audio_cache = {}  # Cache each talker's audio for null routing
                    
                    for uid in list(current_talkers):
                        user_queue = channel_buffers[ch][uid]
                        if user_queue:
                            # Get next chunk from this user
                            chunk = user_queue.popleft()
                            talker_audio_cache[uid] = chunk  # Cache for null routing
                            mixed_audio += chunk
                            active_sources += 1
                        else:
                            # User is talking but buffer empty (underrun)
                            pass
                
                if active_sources == 0:
                    continue
                
                # Normalize if multiple talkers to prevent clipping
                if active_sources > 1:
                    mixed_audio /= active_sources
                
                # Calculate audio level for metering (RMS)
                audio_level = np.sqrt(np.mean(mixed_audio ** 2))
                with audio_lock:
                    channel_levels[ch] = float(audio_level)
                
                with config_lock:
                    vol = channel_volumes.get(ch, 0.8)
                
                # Pre-compute all unique listener mixes (cache by excluded talker)
                listener_mix_cache = {}
                
                for uid in listeners:
                    # Create custom mix for this listener (exclude their own audio)
                    listener_mix = np.zeros(CHUNK, dtype=np.float32)
                    listener_sources = 0
                    
                    for talker_uid, talker_chunk in talker_audio_cache.items():
                        if talker_uid != uid:  # Null out this listener's own audio
                            listener_mix += talker_chunk
                            listener_sources += 1
                    
                    # Normalize if multiple sources (excluding the listener)
                    if listener_sources > 1:
                        listener_mix /= listener_sources
                    
                    # Apply channel volume and convert to raw PCM int16
                    listener_mix *= vol
                    listener_mix = np.clip(listener_mix, -1, 1)
                    pcm_data = (listener_mix * 32767).astype(np.int16)
                    
                    listener_mix_cache[uid] = pcm_data
                
                # Send raw PCM to each listener (no container overhead)
                for uid in listeners:
                    with client_lock:
                        udp_addr = user_udp_addrs.get(uid)
                    if not udp_addr:
                        continue
                    
                    pcm_data = listener_mix_cache[uid]
                    # Packet format: [channel:4][reserved:8][raw_pcm:1920]
                    packet = ch.to_bytes(4, 'big') + b'\x00'*8 + pcm_data.tobytes()
                    
                    try:
                        await loop.sock_sendto(udp_sock, packet, udp_addr)
                    except Exception as e:
                        pass
            
            # Run at ~50Hz (20ms) to match chunk size
            await asyncio.sleep(0.02)
        
        except Exception as e:
            logging.error(f"Mix error: {e}")
            await asyncio.sleep(0.01)


# ===== GUI STYLING =====

class BroadcastTheme:
    """Professional broadcast-grade dark theme"""
    
    @staticmethod
    def apply(app):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(18, 20, 24))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(232, 236, 242))
        palette.setColor(QPalette.ColorRole.Base, QColor(26, 28, 32))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 33, 38))
        palette.setColor(QPalette.ColorRole.Text, QColor(232, 236, 242))
        palette.setColor(QPalette.ColorRole.Button, QColor(32, 36, 42))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(232, 236, 242))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 168, 224))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 168, 224))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        app.setPalette(palette)

        app.setStyleSheet("""
            QMainWindow { background-color: #121418; }
            QWidget { background-color: #121418; color: #e8ecf2; font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif; font-size: 10pt; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1f8ac7, stop:1 #1377b1);
                border: 1px solid #0f6a9d; border-radius: 6px; padding: 8px 16px; color: #e8ecf2;
                min-height: 28px; font-weight: 600;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #26a0e0, stop:1 #1b88c5); border: 1px solid #1da4e6; }
            QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f5b8a, stop:1 #0d4d74); }
            QPushButton:checked { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f6a9d, stop:1 #0c5a84); border: 1px solid #1da4e6; }

            QLineEdit {
                background-color: #1b1e24; border: 1px solid #2f343d; border-radius: 6px;
                padding: 8px 12px; color: #e8ecf2; selection-background-color: #0f8ac7; font-size: 10pt;
            }
            QLineEdit:focus { border: 1px solid #0f8ac7; background-color: #1f2229; }

            QComboBox {
                background-color: #1b1e24; border: 1px solid #2f343d; border-radius: 6px;
                padding: 6px 10px; color: #e8ecf2; min-height: 26px; font-size: 10pt;
            }
            QComboBox:hover { border: 1px solid #0f8ac7; background-color: #1f2229; }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox::down-arrow { border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #7f8ba3; margin-right: 8px; }
            QComboBox QAbstractItemView { background-color: #1b1e24; border: 1px solid #0f8ac7; selection-background-color: #0f8ac7; color: #e8ecf2; padding: 4px; }

            QLabel { background-color: transparent; color: #e8ecf2; }

            QGroupBox {
                background-color: #161920; border: 1px solid #242933; border-radius: 8px;
                margin-top: 12px; padding-top: 18px; font-weight: 700; font-size: 11pt;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 6px 14px; color: #0f8ac7; font-size: 11pt; }

            QSlider::groove:vertical { background: #1a1d23; width: 10px; border-radius: 5px; border: 1px solid #2a303a; }
            QSlider::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #30b4ff, stop:1 #0f8ac7);
                height: 26px; margin: 0 -8px; border-radius: 13px; border: 1px solid #0d5c87;
            }
            QSlider::handle:vertical:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #52c4ff, stop:1 #20a2e0); }

            QTableWidget { background-color: #161920; border: 1px solid #222733; gridline-color: #222733; color: #e8ecf2; }
            QTableWidget::item { padding: 10px; }
            QTableWidget::item:selected { background-color: #0f8ac7; }
            QHeaderView::section { background-color: #1d2028; color: #9ca7bd; padding: 9px; border: none; font-weight: 700; border-bottom: 1px solid #222733; }

            QScrollBar:vertical { background: #121418; width: 12px; border-radius: 6px; }
            QScrollBar::handle:vertical { background: #2b313c; min-height: 32px; border-radius: 6px; }
            QScrollBar::handle:vertical:hover { background: #0f8ac7; }
            QScrollBar:horizontal { background: #121418; height: 12px; border-radius: 6px; }
            QScrollBar::handle:horizontal { background: #2b313c; min-width: 32px; border-radius: 6px; }
            QScrollBar::handle:horizontal:hover { background: #0f8ac7; }

            QTabWidget::pane { border: 1px solid #222733; border-radius: 8px; background-color: #121418; }
            QTabBar::tab {
                background: #161920;
                border: 1px solid #1f252f; border-bottom: none; border-top-left-radius: 7px;
                border-top-right-radius: 7px; padding: 9px 18px; margin-right: 2px;
                color: #9ca7bd; font-size: 10pt; font-weight: 600;
                min-width: 110px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1b8bcc, stop:1 #116eaa);
                color: #eaf2fb; border: 1px solid #1da4e6; border-bottom: none;
            }
            QTabBar::tab:hover:!selected { background: #1a1d23; color: #e8ecf2; }

            QFrame { border: none; }
        """)


# ===== ADD USER DIALOG =====

class ButtonModeDialog(QDialog):
    """Dialog for configuring button modes (latch/non-latch) per channel"""
    
    def __init__(self, user_name, parent=None):
        super().__init__(parent)
        self.user_name = user_name
        self.setWindowTitle(f"Button Modes - {user_name}")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        with config_lock:
            self.user_channels = users[user_name]['channels'].copy()
            self.button_modes = users[user_name].get('button_modes', {}).copy()
            self.available_channels = channels.copy()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel(f"Configure button behavior for {user_name}")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #5096ff;")
        layout.addWidget(title)
        
        desc = QLabel("Set whether each channel button latches (toggle on/off) or is non-latching (push-to-talk)")
        desc.setStyleSheet("color: #a0a0a5; font-size: 10pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Slots group
        slots_group = QGroupBox("Button Modes")
        slots_layout = QVBoxLayout()
        
        self.mode_buttons = []
        for slot in range(MAX_USER_CHANNELS):
            slot_layout = QHBoxLayout()
            
            slot_label = QLabel(f"Slot {slot+1}:")
            slot_label.setMinimumWidth(70)
            slot_label.setStyleSheet("font-size: 11pt; font-weight: bold;")
            slot_layout.addWidget(slot_label)
            
            # Show channel name
            ch_id = self.user_channels[slot] if slot < len(self.user_channels) else None
            ch_name = self.available_channels.get(ch_id, "None") if ch_id is not None else "None"
            ch_label = QLabel(ch_name)
            ch_label.setMinimumWidth(150)
            ch_label.setStyleSheet("font-size: 11pt; color: #e6e6eb;")
            slot_layout.addWidget(ch_label)
            
            slot_layout.addStretch()
            
            # Latch/Non-latch buttons
            latch_btn = QPushButton("Latch (Toggle)")
            latch_btn.setCheckable(True)
            latch_btn.setMinimumHeight(35)
            latch_btn.setMinimumWidth(140)
            
            nonlatch_btn = QPushButton("Non-Latch (PTT)")
            nonlatch_btn.setCheckable(True)
            nonlatch_btn.setMinimumHeight(35)
            nonlatch_btn.setMinimumWidth(140)
            
            # Get current mode (default to latch)
            current_mode = self.button_modes.get(str(slot), 'latch')
            if current_mode == 'latch':
                latch_btn.setChecked(True)
            else:
                nonlatch_btn.setChecked(True)
            
            # Make them mutually exclusive
            latch_btn.clicked.connect(lambda checked, s=slot, l=latch_btn, nl=nonlatch_btn: self.set_mode(s, 'latch', l, nl))
            nonlatch_btn.clicked.connect(lambda checked, s=slot, l=latch_btn, nl=nonlatch_btn: self.set_mode(s, 'non-latch', l, nl))
            
            slot_layout.addWidget(latch_btn)
            slot_layout.addWidget(nonlatch_btn)
            
            self.mode_buttons.append((slot, latch_btn, nonlatch_btn))
            slots_layout.addLayout(slot_layout)
        
        slots_group.setLayout(slots_layout)
        layout.addWidget(slots_group)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("✓ Save Settings")
        save_btn.setMinimumHeight(45)
        save_btn.setStyleSheet("font-size: 12pt; font-weight: bold;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.setMinimumHeight(45)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("""
            QDialog { background-color: #19191c; }
            QLabel { color: #e6e6eb; }
            QGroupBox { color: #5096ff; font-size: 13pt; font-weight: bold; }
        """)
    
    def set_mode(self, slot, mode, latch_btn, nonlatch_btn):
        """Set button mode and update button states"""
        self.button_modes[str(slot)] = mode
        if mode == 'latch':
            latch_btn.setChecked(True)
            nonlatch_btn.setChecked(False)
        else:
            latch_btn.setChecked(False)
            nonlatch_btn.setChecked(True)
    
    def get_button_modes(self):
        return self.button_modes


class AddUserDialog(QDialog):
    """Popup dialog for adding new users"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New User")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        with config_lock:
            # Only show enabled/active channels
            self.available_channels = {ch_id: name for ch_id, name in channels.items() 
                                      if channel_enabled.get(ch_id, False)}
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # User name input
        name_layout = QHBoxLayout()
        name_label = QLabel("User Name:")
        name_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        name_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter user name...")
        self.name_input.setMinimumHeight(40)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Channel assignments group
        channels_group = QGroupBox("Channel Assignments (Max 4)")
        channels_layout = QVBoxLayout()
        
        self.channel_combos = []
        for i in range(MAX_USER_CHANNELS):
            slot_layout = QHBoxLayout()
            
            slot_label = QLabel(f"Slot {i+1}:")
            slot_label.setMinimumWidth(70)
            slot_layout.addWidget(slot_label)
            
            combo = QComboBox()
            combo.setMinimumHeight(40)
            combo.addItem("-- None --", -1)
            
            for ch_id in sorted(self.available_channels.keys()):
                ch_name = self.available_channels[ch_id]
                combo.addItem(f"{ch_name} (CH{ch_id})", ch_id)
            
            slot_layout.addWidget(combo)
            self.channel_combos.append(combo)
            channels_layout.addLayout(slot_layout)
        
        channels_group.setLayout(channels_layout)
        layout.addWidget(channels_group)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("✓ Save New User")
        save_btn.setMinimumHeight(45)
        save_btn.setStyleSheet("font-size: 12pt; font-weight: bold;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.setMinimumHeight(45)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Apply theme
        self.setStyleSheet("""
            QDialog {
                background-color: #19191c;
            }
            QLabel {
                color: #e6e6eb;
            }
            QGroupBox {
                color: #5096ff;
                font-size: 13pt;
                font-weight: bold;
            }
        """)
    
    def get_user_name(self):
        return self.name_input.text().strip()
    
    def get_selected_channels(self):
        channels_list = []
        for combo in self.channel_combos:
            ch_id = combo.currentData()
            if ch_id != -1:
                channels_list.append(ch_id)
            else:
                channels_list.append(None)
        # Remove trailing None values
        while channels_list and channels_list[-1] is None:
            channels_list.pop()
        return channels_list


# ===== CHANNEL STRIP WIDGET =====

class ChannelStrip(QFrame):
    """Professional channel strip with fader and naming"""
    
    volume_changed = pyqtSignal(int, int)
    name_changed = pyqtSignal(int, str)
    enabled_changed = pyqtSignal(int, bool)
    
    def __init__(self, channel_id, channel_name, volume, is_program=False, enabled=True):
        super().__init__()
        self.channel_id = channel_id
        self.is_program = is_program
        
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Enable/Disable checkbox (only for regular channels, not program)
        if not is_program:
            self.enable_checkbox = QCheckBox("Active")
            self.enable_checkbox.setChecked(enabled)
            self.enable_checkbox.setStyleSheet("""
                QCheckBox { color: #5096ff; font-size: 9pt; font-weight: bold; }
                QCheckBox::indicator { width: 16px; height: 16px; }
                QCheckBox::indicator:checked { background-color: #0f8ac7; border: 1px solid #1da4e6; border-radius: 3px; }
                QCheckBox::indicator:unchecked { background-color: #2d2d32; border: 1px solid #4a4a50; border-radius: 3px; }
            """)
            self.enable_checkbox.stateChanged.connect(self.on_enabled_changed)
            layout.addWidget(self.enable_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Channel ID badge - only show for Program channel
        if is_program:
            id_label = QLabel("Program")
            id_label.setStyleSheet("""
                background-color: #3d3d42; color: #ff9650; border-radius: 3px;
                padding: 4px; font-size: 9pt; font-weight: bold;
            """)
            id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(id_label)
        
        # Channel name - editable for regular channels only (program has no name label)
        if not is_program:
            # Editable name for regular channels
            self.name_input = QLineEdit(channel_name)
            self.name_input.setMaxLength(12)
            self.name_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.name_input.setMinimumHeight(26)
            self.name_input.editingFinished.connect(self.on_name_changed)
            self.name_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: #232326; border: 1px solid #3d3d42; border-radius: 3px;
                    padding: 4px; color: #ffffff; font-size: 9pt; font-weight: 600;
                }}
                QLineEdit:focus {{ border: 1px solid #5096ff; background-color: #2a2a2d; }}
            """)
            layout.addWidget(self.name_input)
        
        # Volume fader
        self.volume_slider = QSlider(Qt.Orientation.Vertical)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(int(volume * 100))
        self.volume_slider.setMinimumHeight(250)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        layout.addWidget(self.volume_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Volume display
        self.volume_label = QLabel(f"{int(volume * 100)}%")
        self.volume_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_color = "#ff9650" if is_program else "#5096ff"
        self.volume_label.setStyleSheet(f"""
            background-color: #2d2d32; color: {label_color}; border-radius: 3px;
            padding: 4px; font-size: 11pt; font-weight: bold; min-width: 55px;
        """)
        layout.addWidget(self.volume_label)
        
        # Audio level meter
        meter_label = QLabel("LEVEL")
        meter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meter_label.setStyleSheet("font-size: 8pt; color: #a0a0a5; background: transparent;")
        layout.addWidget(meter_label)
        
        self.level_meter = QProgressBar()
        self.level_meter.setOrientation(Qt.Orientation.Vertical)
        self.level_meter.setMinimum(0)
        self.level_meter.setMaximum(100)
        self.level_meter.setValue(0)
        self.level_meter.setMinimumHeight(40)
        self.level_meter.setTextVisible(False)
        self.level_meter.setStyleSheet("""
            QProgressBar {
                background-color: #1a1a1d; border: 1px solid #3d3d42; border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:1, x2:0, y2:0,
                    stop:0 #2a2, stop:0.6 #2a2, 
                    stop:0.6 #da2, stop:0.8 #da2,
                    stop:0.8 #d22, stop:1 #d22);
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.level_meter, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        self.peak_hold = 0.0
        self.peak_decay = 0.0
        
        self.setLayout(layout)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        border_color = "#ff9650" if is_program else "#3d3d42"
        self.setStyleSheet(f"""
            ChannelStrip {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2d2d32, stop:1 #1e1e21);
                border: 1px solid {border_color}; border-radius: 4px;
            }}
        """)
        self.setMinimumWidth(90)
        self.setMaximumWidth(100)
    
    def on_volume_changed(self, value):
        self.volume_label.setText(f"{value}%")
        self.volume_changed.emit(self.channel_id, value)
    
    def on_name_changed(self):
        new_name = self.name_input.text().strip()
        if new_name:
            self.name_changed.emit(self.channel_id, new_name)
    
    def on_enabled_changed(self, state):
        """Handle enable/disable checkbox"""
        if not self.is_program:
            enabled = state == Qt.CheckState.Checked.value
            self.enabled_changed.emit(self.channel_id, enabled)
            # Gray out the strip when disabled
            self.setEnabled(True)  # Keep interactive
            opacity = "1.0" if enabled else "0.5"
            self.setStyleSheet(f"""
                ChannelStrip {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2d2d32, stop:1 #1e1e21);
                    border: 1px solid #3d3d42; border-radius: 4px;
                    opacity: {opacity};
                }}
            """)
    
    def update_level(self, level):
        """Update audio level meter with peak hold (0.0-1.0)"""
        level_percent = int(level * 100)
        
        # Peak hold with decay
        if level_percent > self.peak_hold:
            self.peak_hold = level_percent
            self.peak_decay = level_percent
        else:
            self.peak_decay *= 0.95  # Decay rate
            if self.peak_decay < level_percent:
                self.peak_decay = level_percent
        
        self.level_meter.setValue(int(self.peak_decay))
        
        # Color-code based on level
        if level_percent > 80:
            self.level_meter.setStyleSheet("""
                QProgressBar { background-color: #1a1a1d; border: 1px solid #d22; border-radius: 3px; }
                QProgressBar::chunk { background: #d22; border-radius: 2px; }
            """)
        elif level_percent > 60:
            self.level_meter.setStyleSheet("""
                QProgressBar { background-color: #1a1a1d; border: 1px solid #da2; border-radius: 3px; }
                QProgressBar::chunk { background: #da2; border-radius: 2px; }
            """)
        else:
            self.level_meter.setStyleSheet("""
                QProgressBar { background-color: #1a1a1d; border: 1px solid #3d3d42; border-radius: 3px; }
                QProgressBar::chunk {
                    background: qlineargradient(x1:0, y1:1, x2:0, y2:0,
                        stop:0 #2a2, stop:0.6 #2a2, 
                        stop:0.6 #da2, stop:0.8 #da2,
                        stop:0.8 #d22, stop:1 #d22);
                    border-radius: 2px;
                }
            """)


# ===== MAIN GUI =====

class ServerGUI(QMainWindow):
    """Commercial-grade intercom server GUI"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LanComm Server v1.0.0")
        self.setGeometry(100, 100, 1400, 860)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.create_matrix_tab(), "� User")
        self.tabs.addTab(self.create_fourwire_tab(), "🔌 4-Wire")
        self.tabs.addTab(self.create_mixer_tab(), "🎚️ Mixer")
        self.tabs.addTab(self.create_nodes_tab(), "📡 Beltpacks")
        main_layout.addWidget(self.tabs)
        
        # Status bar
        main_layout.addWidget(self.create_status_bar())
        
        # Update timer - faster for level meters
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(50)  # 20Hz for smooth meter response
        
        # Node refresh timer - slower for node list
        self.node_refresh_timer = QTimer()
        self.node_refresh_timer.timeout.connect(self.refresh_nodes_list)
        self.node_refresh_timer.start(2000)  # 2 seconds
    
    def create_fourwire_tab(self):
        """4-Wire interface configuration tab"""
        fourwire = QWidget()
        layout = QVBoxLayout(fourwire)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        title = QLabel("4-Wire Audio Interfaces")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #5096ff; padding: 4px;")
        layout.addWidget(title)
        
        desc = QLabel("Connect external systems (FreeSpeak II, Clear-Com, radio patches) via 4-wire audio interfaces")
        desc.setStyleSheet("color: #a0a0a5; font-size: 10pt; padding: 4px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Store references for later updates
        self.fourwire_enable_btn = []
        self.fourwire_channel_combo = []
        
        # 4-Wire Interface 1
        interface1_group = QGroupBox("4-Wire Interface 1")
        interface1_group.setStyleSheet("QGroupBox { color: #5096ff; }")
        interface1_layout = QVBoxLayout()
        interface1_layout.setSpacing(10)
        
        # Controls row 1
        controls1 = QHBoxLayout()
        controls1.setSpacing(8)
        
        enable_label1 = QLabel("Status:")
        enable_label1.setMinimumWidth(60)
        controls1.addWidget(enable_label1)
        
        fourwire_enable_btn_1 = QPushButton("OFF")
        self.fourwire_enable_btn.append(fourwire_enable_btn_1)
        fourwire_enable_btn_1.setCheckable(True)
        fourwire_enable_btn_1.setMinimumWidth(80)
        fourwire_enable_btn_1.setMinimumHeight(32)
        fourwire_enable_btn_1.setStyleSheet("""
            QPushButton {
                background-color: #666; color: #fff; border: 1px solid #888;
                border-radius: 4px; font-weight: bold; font-size: 10pt;
            }
            QPushButton:checked {
                background-color: #2a2; color: #fff; border: 1px solid #4d4;
            }
        """)
        fourwire_enable_btn_1.clicked.connect(lambda: self.on_fourwire_toggled(0))
        controls1.addWidget(fourwire_enable_btn_1)
        
        controls1.addSpacing(20)
        
        ch_label1 = QLabel("Channel:")
        ch_label1.setMinimumWidth(60)
        controls1.addWidget(ch_label1)
        
        fourwire_channel_combo_1 = QComboBox()
        self.fourwire_channel_combo.append(fourwire_channel_combo_1)
        fourwire_channel_combo_1.setMinimumWidth(120)
        fourwire_channel_combo_1.setMinimumHeight(32)
        with config_lock:
            for ch_id in range(MAX_CHANNELS):
                if channel_enabled.get(ch_id, False):
                    ch_name = channels.get(ch_id, f'CH{ch_id}')
                    fourwire_channel_combo_1.addItem(ch_name, ch_id)
        fourwire_channel_combo_1.currentIndexChanged.connect(lambda: self.on_fourwire_channel_changed(0))
        controls1.addWidget(fourwire_channel_combo_1)
        
        controls1.addStretch()
        interface1_layout.addLayout(controls1)
        
        # Input device row
        input_row1 = QHBoxLayout()
        input_row1.setSpacing(8)
        
        input_label1 = QLabel("Input Device:")
        input_label1.setMinimumWidth(100)
        input_row1.addWidget(input_label1)
        
        self.fourwire_input_combo_1 = QComboBox()
        self.fourwire_input_combo_1.setMinimumHeight(32)
        self.fourwire_input_combo_1.addItem("-- No Device --", None)
        try:
            if p is not None:
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    max_channels = info.get('maxInputChannels', 0)
                    if isinstance(max_channels, int) and max_channels > 0:
                        self.fourwire_input_combo_1.addItem(f"{info['name']} ({max_channels} ch)", i)
        except Exception as e:
            logging.error(f"Error enumerating input devices: {e}")
        
        with config_lock:
            if fourwire_input_device[0] is not None:
                for idx in range(self.fourwire_input_combo_1.count()):
                    if self.fourwire_input_combo_1.itemData(idx) == fourwire_input_device[0]:
                        self.fourwire_input_combo_1.setCurrentIndex(idx)
                        break
        
        self.fourwire_input_combo_1.currentIndexChanged.connect(lambda: self.on_fourwire_input_changed(0))
        input_row1.addWidget(self.fourwire_input_combo_1)
        
        input_gain_label1 = QLabel("Gain:")
        input_gain_label1.setMinimumWidth(40)
        input_row1.addWidget(input_gain_label1)
        
        self.fourwire_input_gain_slider_1 = QSlider(Qt.Orientation.Horizontal)
        self.fourwire_input_gain_slider_1.setMinimum(0)
        self.fourwire_input_gain_slider_1.setMaximum(100)
        self.fourwire_input_gain_slider_1.setValue(int(fourwire_input_gain[0] * 100))
        self.fourwire_input_gain_slider_1.setMaximumWidth(150)
        self.fourwire_input_gain_slider_1.valueChanged.connect(lambda v: self.on_fourwire_gain_changed(0, 'input', v))
        input_row1.addWidget(self.fourwire_input_gain_slider_1)
        
        self.fourwire_input_gain_label_1 = QLabel(f"{int(fourwire_input_gain[0] * 100)}%")
        self.fourwire_input_gain_label_1.setMinimumWidth(40)
        self.fourwire_input_gain_slider_1.valueChanged.connect(lambda v: self.fourwire_input_gain_label_1.setText(f"{v}%"))
        input_row1.addWidget(self.fourwire_input_gain_label_1)
        
        input_row1.addStretch()
        interface1_layout.addLayout(input_row1)
        
        # Output device row
        output_row1 = QHBoxLayout()
        output_row1.setSpacing(8)
        
        output_label1 = QLabel("Output Device:")
        output_label1.setMinimumWidth(100)
        output_row1.addWidget(output_label1)
        
        self.fourwire_output_combo_1 = QComboBox()
        self.fourwire_output_combo_1.setMinimumHeight(32)
        self.fourwire_output_combo_1.addItem("-- No Device --", None)
        try:
            if p is not None:
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    max_channels = info.get('maxOutputChannels', 0)
                    if isinstance(max_channels, int) and max_channels > 0:
                        self.fourwire_output_combo_1.addItem(f"{info['name']} ({max_channels} ch)", i)
        except Exception as e:
            logging.error(f"Error enumerating output devices: {e}")
        
        with config_lock:
            if fourwire_output_device[0] is not None:
                for idx in range(self.fourwire_output_combo_1.count()):
                    if self.fourwire_output_combo_1.itemData(idx) == fourwire_output_device[0]:
                        self.fourwire_output_combo_1.setCurrentIndex(idx)
                        break
        
        self.fourwire_output_combo_1.currentIndexChanged.connect(lambda: self.on_fourwire_output_changed(0))
        output_row1.addWidget(self.fourwire_output_combo_1)
        
        output_gain_label1 = QLabel("Gain:")
        output_gain_label1.setMinimumWidth(40)
        output_row1.addWidget(output_gain_label1)
        
        self.fourwire_output_gain_slider_1 = QSlider(Qt.Orientation.Horizontal)
        self.fourwire_output_gain_slider_1.setMinimum(0)
        self.fourwire_output_gain_slider_1.setMaximum(100)
        self.fourwire_output_gain_slider_1.setValue(int(fourwire_output_gain[0] * 100))
        self.fourwire_output_gain_slider_1.setMaximumWidth(150)
        self.fourwire_output_gain_slider_1.valueChanged.connect(lambda v: self.on_fourwire_gain_changed(0, 'output', v))
        output_row1.addWidget(self.fourwire_output_gain_slider_1)
        
        self.fourwire_output_gain_label_1 = QLabel(f"{int(fourwire_output_gain[0] * 100)}%")
        self.fourwire_output_gain_label_1.setMinimumWidth(40)
        self.fourwire_output_gain_slider_1.valueChanged.connect(lambda v: self.fourwire_output_gain_label_1.setText(f"{v}%"))
        output_row1.addWidget(self.fourwire_output_gain_label_1)
        
        output_row1.addStretch()
        interface1_layout.addLayout(output_row1)
        
        interface1_group.setLayout(interface1_layout)
        layout.addWidget(interface1_group)
        
        # 4-Wire Interface 2
        interface2_group = QGroupBox("4-Wire Interface 2")
        interface2_group.setStyleSheet("QGroupBox { color: #ff9650; }")
        interface2_layout = QVBoxLayout()
        interface2_layout.setSpacing(10)
        
        # Controls row 2
        controls2 = QHBoxLayout()
        controls2.setSpacing(8)
        
        enable_label2 = QLabel("Status:")
        enable_label2.setMinimumWidth(60)
        controls2.addWidget(enable_label2)
        
        fourwire_enable_btn_2 = QPushButton("OFF")
        self.fourwire_enable_btn.append(fourwire_enable_btn_2)
        fourwire_enable_btn_2.setCheckable(True)
        fourwire_enable_btn_2.setMinimumWidth(80)
        fourwire_enable_btn_2.setMinimumHeight(32)
        fourwire_enable_btn_2.setStyleSheet("""
            QPushButton {
                background-color: #666; color: #fff; border: 1px solid #888;
                border-radius: 4px; font-weight: bold; font-size: 10pt;
            }
            QPushButton:checked {
                background-color: #2a2; color: #fff; border: 1px solid #4d4;
            }
        """)
        fourwire_enable_btn_2.clicked.connect(lambda: self.on_fourwire_toggled(1))
        controls2.addWidget(fourwire_enable_btn_2)
        
        controls2.addSpacing(20)
        
        ch_label2 = QLabel("Channel:")
        ch_label2.setMinimumWidth(60)
        controls2.addWidget(ch_label2)
        
        fourwire_channel_combo_2 = QComboBox()
        self.fourwire_channel_combo.append(fourwire_channel_combo_2)
        fourwire_channel_combo_2.setMinimumWidth(120)
        fourwire_channel_combo_2.setMinimumHeight(32)
        with config_lock:
            for ch_id in range(MAX_CHANNELS):
                if channel_enabled.get(ch_id, False):
                    ch_name = channels.get(ch_id, f'CH{ch_id}')
                    fourwire_channel_combo_2.addItem(ch_name, ch_id)
        fourwire_channel_combo_2.currentIndexChanged.connect(lambda: self.on_fourwire_channel_changed(1))
        controls2.addWidget(fourwire_channel_combo_2)
        
        controls2.addStretch()
        interface2_layout.addLayout(controls2)
        
        # Input device row
        input_row2 = QHBoxLayout()
        input_row2.setSpacing(8)
        
        input_label2 = QLabel("Input Device:")
        input_label2.setMinimumWidth(100)
        input_row2.addWidget(input_label2)
        
        self.fourwire_input_combo_2 = QComboBox()
        self.fourwire_input_combo_2.setMinimumHeight(32)
        self.fourwire_input_combo_2.addItem("-- No Device --", None)
        try:
            if p is not None:
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    max_channels = info.get('maxInputChannels', 0)
                    if isinstance(max_channels, int) and max_channels > 0:
                        self.fourwire_input_combo_2.addItem(f"{info['name']} ({max_channels} ch)", i)
        except Exception as e:
            logging.error(f"Error enumerating input devices: {e}")
        
        with config_lock:
            if fourwire_input_device[1] is not None:
                for idx in range(self.fourwire_input_combo_2.count()):
                    if self.fourwire_input_combo_2.itemData(idx) == fourwire_input_device[1]:
                        self.fourwire_input_combo_2.setCurrentIndex(idx)
                        break
        
        self.fourwire_input_combo_2.currentIndexChanged.connect(lambda: self.on_fourwire_input_changed(1))
        input_row2.addWidget(self.fourwire_input_combo_2)
        
        input_gain_label2 = QLabel("Gain:")
        input_gain_label2.setMinimumWidth(40)
        input_row2.addWidget(input_gain_label2)
        
        self.fourwire_input_gain_slider_2 = QSlider(Qt.Orientation.Horizontal)
        self.fourwire_input_gain_slider_2.setMinimum(0)
        self.fourwire_input_gain_slider_2.setMaximum(100)
        self.fourwire_input_gain_slider_2.setValue(int(fourwire_input_gain[1] * 100))
        self.fourwire_input_gain_slider_2.setMaximumWidth(150)
        self.fourwire_input_gain_slider_2.valueChanged.connect(lambda v: self.on_fourwire_gain_changed(1, 'input', v))
        input_row2.addWidget(self.fourwire_input_gain_slider_2)
        
        self.fourwire_input_gain_label_2 = QLabel(f"{int(fourwire_input_gain[1] * 100)}%")
        self.fourwire_input_gain_label_2.setMinimumWidth(40)
        self.fourwire_input_gain_slider_2.valueChanged.connect(lambda v: self.fourwire_input_gain_label_2.setText(f"{v}%"))
        input_row2.addWidget(self.fourwire_input_gain_label_2)
        
        input_row2.addStretch()
        interface2_layout.addLayout(input_row2)
        
        # Output device row
        output_row2 = QHBoxLayout()
        output_row2.setSpacing(8)
        
        output_label2 = QLabel("Output Device:")
        output_label2.setMinimumWidth(100)
        output_row2.addWidget(output_label2)
        
        self.fourwire_output_combo_2 = QComboBox()
        self.fourwire_output_combo_2.setMinimumHeight(32)
        self.fourwire_output_combo_2.addItem("-- No Device --", None)
        try:
            if p is not None:
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    max_channels = info.get('maxOutputChannels', 0)
                    if isinstance(max_channels, int) and max_channels > 0:
                        self.fourwire_output_combo_2.addItem(f"{info['name']} ({max_channels} ch)", i)
        except Exception as e:
            logging.error(f"Error enumerating output devices: {e}")
        
        with config_lock:
            if fourwire_output_device[1] is not None:
                for idx in range(self.fourwire_output_combo_2.count()):
                    if self.fourwire_output_combo_2.itemData(idx) == fourwire_output_device[1]:
                        self.fourwire_output_combo_2.setCurrentIndex(idx)
                        break
        
        self.fourwire_output_combo_2.currentIndexChanged.connect(lambda: self.on_fourwire_output_changed(1))
        output_row2.addWidget(self.fourwire_output_combo_2)
        
        output_gain_label2 = QLabel("Gain:")
        output_gain_label2.setMinimumWidth(40)
        output_row2.addWidget(output_gain_label2)
        
        self.fourwire_output_gain_slider_2 = QSlider(Qt.Orientation.Horizontal)
        self.fourwire_output_gain_slider_2.setMinimum(0)
        self.fourwire_output_gain_slider_2.setMaximum(100)
        self.fourwire_output_gain_slider_2.setValue(int(fourwire_output_gain[1] * 100))
        self.fourwire_output_gain_slider_2.setMaximumWidth(150)
        self.fourwire_output_gain_slider_2.valueChanged.connect(lambda v: self.on_fourwire_gain_changed(1, 'output', v))
        output_row2.addWidget(self.fourwire_output_gain_slider_2)
        
        self.fourwire_output_gain_label_2 = QLabel(f"{int(fourwire_output_gain[1] * 100)}%")
        self.fourwire_output_gain_label_2.setMinimumWidth(40)
        self.fourwire_output_gain_slider_2.valueChanged.connect(lambda v: self.fourwire_output_gain_label_2.setText(f"{v}%"))
        output_row2.addWidget(self.fourwire_output_gain_label_2)
        
        output_row2.addStretch()
        interface2_layout.addLayout(output_row2)
        
        interface2_group.setLayout(interface2_layout)
        layout.addWidget(interface2_group)
        
        layout.addStretch()
        
        return fourwire
    
    def create_mixer_tab(self):
        """Mixer view with channel strips"""
        mixer = QWidget()
        layout = QVBoxLayout(mixer)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header with title and program audio selector
        header_layout = QHBoxLayout()
        
        title = QLabel("Mixer")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #5096ff; padding: 2px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Program audio device selector
        prog_label = QLabel("Program Audio:")
        prog_label.setStyleSheet("color: #5096ff; font-weight: bold; background: transparent; font-size: 9pt;")
        header_layout.addWidget(prog_label)
        
        self.program_device_combo = QComboBox()
        self.program_device_combo.setMinimumWidth(200)
        self.program_device_combo.setMinimumHeight(32)
        self.program_device_combo.addItem("-- No Device --", None)
        
        # Get available audio input devices
        try:
            if p is not None:
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    max_channels = info.get('maxInputChannels', 0)  # type: ignore
                    if isinstance(max_channels, int) and max_channels > 0:
                        self.program_device_combo.addItem(f"{info['name']}", (i, max_channels))
                        logging.debug(f"Found input device: {info['name']} ({info['maxInputChannels']} channels)")
            else:
                logging.warning("PyAudio not initialized - no audio devices available")
        except Exception as e:
            logging.error(f"Error enumerating audio devices: {e}")
        
        # Set current device
        with config_lock:
            if program_audio_device is not None:
                for idx in range(self.program_device_combo.count()):
                    data = self.program_device_combo.itemData(idx)
                    if data is not None and data[0] == program_audio_device:
                        self.program_device_combo.setCurrentIndex(idx)
                        break
        
        self.program_device_combo.currentIndexChanged.connect(self.on_program_device_changed)
        header_layout.addWidget(self.program_device_combo)
        
        # Program audio channel selector
        ch_label = QLabel("Ch:")
        ch_label.setStyleSheet("color: #5096ff; font-weight: bold; background: transparent; font-size: 9pt;")
        header_layout.addWidget(ch_label)
        
        self.program_channel_combo = QComboBox()
        self.program_channel_combo.setMinimumWidth(80)
        self.program_channel_combo.setMinimumHeight(32)
        self.program_channel_combo.addItem("Ch 1", 0)
        
        # Update channel list based on device
        device_data = self.program_device_combo.currentData()
        if device_data is not None:
            max_channels = device_data[1]
            self.program_channel_combo.clear()
            for i in range(max_channels):
                self.program_channel_combo.addItem(f"Ch {i+1}", i)
        
        with config_lock:
            idx = self.program_channel_combo.findData(program_audio_channel)
            if idx >= 0:
                self.program_channel_combo.setCurrentIndex(idx)
        
        self.program_channel_combo.currentIndexChanged.connect(self.on_program_channel_changed)
        header_layout.addWidget(self.program_channel_combo)
        
        layout.addLayout(header_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        strips_container = QWidget()
        strips_layout = QHBoxLayout(strips_container)
        strips_layout.setSpacing(10)
        strips_layout.setContentsMargins(8, 8, 8, 8)
        
        self.channel_strips = {}
        
        # Add Program fader first (special channel -1)
        with config_lock:
            prog_volume = channel_volumes.get(-1, 0.8)
        prog_strip = ChannelStrip(-1, "Program", prog_volume, is_program=True)
        prog_strip.volume_changed.connect(self.on_volume_changed)
        prog_strip.name_changed.connect(self.on_name_changed)
        self.channel_strips[-1] = prog_strip
        strips_layout.addWidget(prog_strip)
        
        # Add regular channel faders
        with config_lock:
            for ch_id in range(MAX_CHANNELS):
                ch_name = channels.get(ch_id, f'Channel {ch_id+1}')
                volume = channel_volumes.get(ch_id, 0.8)
                enabled = channel_enabled.get(ch_id, True)
                
                strip = ChannelStrip(ch_id, ch_name, volume, is_program=False, enabled=enabled)
                strip.volume_changed.connect(self.on_volume_changed)
                strip.name_changed.connect(self.on_name_changed)
                strip.enabled_changed.connect(self.on_channel_enabled_changed)
                
                self.channel_strips[ch_id] = strip
                strips_layout.addWidget(strip)
        
        strips_layout.addStretch()
        scroll.setWidget(strips_container)
        layout.addWidget(scroll)
        
        return mixer
    
    def create_nodes_tab(self):
        """Beltpacks view showing all connected belt packs"""
        nodes = QWidget()
        layout = QVBoxLayout(nodes)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        title = QLabel("Connected Beltpacks")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #5096ff; padding: 4px;")
        layout.addWidget(title)
        
        # Nodes table
        self.nodes_table = QTableWidget()
        self.nodes_table.setColumnCount(4)
        self.nodes_table.setHorizontalHeaderLabels(["IP Address", "Hostname", "Assigned User", "Actions"])
        self.nodes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.nodes_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        header = self.nodes_table.horizontalHeader()
        if header:
            header.setStretchLastSection(False)
        self.nodes_table.setColumnWidth(0, 150)
        self.nodes_table.setColumnWidth(1, 150)
        self.nodes_table.setColumnWidth(2, 200)
        self.nodes_table.setColumnWidth(3, 200)
        layout.addWidget(self.nodes_table)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh Node List")
        refresh_btn.setMinimumHeight(35)
        refresh_btn.clicked.connect(self.refresh_nodes_list)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        return nodes
    
    def refresh_nodes_list(self):
        """Update nodes table with current active nodes"""
        with node_lock:
            nodes_list = list(active_nodes.items())
        
        self.nodes_table.setRowCount(len(nodes_list))
        
        for row, (ip, node_data) in enumerate(nodes_list):
            # IP Address
            ip_item = QTableWidgetItem(ip)
            ip_item.setFlags(ip_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.nodes_table.setItem(row, 0, ip_item)
            
            # Hostname - show custom name if available
            with config_lock:
                display_name = device_names.get(ip, node_data.get('hostname', 'Unknown'))
            hostname_item = QTableWidgetItem(display_name)
            hostname_item.setFlags(hostname_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.nodes_table.setItem(row, 1, hostname_item)
            
            # Assigned User
            user_name = node_data.get('user_name')
            user_item = QTableWidgetItem(user_name if user_name else 'Unassigned')
            user_item.setFlags(user_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.nodes_table.setItem(row, 2, user_item)
            
            # Actions - Assign Profile, Rename, Flash buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 4, 4, 4)
            
            assign_btn = QPushButton("Assign Profile")
            assign_btn.setMinimumHeight(28)
            assign_btn.setProperty('node_ip', ip)
            assign_btn.clicked.connect(lambda checked, n=ip: self.assign_profile_to_node(n))
            action_layout.addWidget(assign_btn)
            
            rename_btn = QPushButton("Rename")
            rename_btn.setMinimumHeight(28)
            rename_btn.setProperty('node_ip', ip)
            rename_btn.clicked.connect(lambda checked, n=ip: self.rename_device(n))
            action_layout.addWidget(rename_btn)
            
            flash_btn = QPushButton("Flash")
            flash_btn.setMinimumHeight(28)
            flash_btn.setProperty('node_ip', ip)
            flash_btn.clicked.connect(lambda checked, n=ip: self.flash_node(n))
            action_layout.addWidget(flash_btn)
            
            action_layout.addStretch()
            self.nodes_table.setCellWidget(row, 3, action_widget)
    
    def assign_profile_to_node(self, node_ip):
        """Show dialog to assign user profile to a node"""
        with config_lock:
            user_list = list(users.keys())
        
        if not user_list:
            QMessageBox.warning(self, "No Users", "No user profiles available")
            return
        
        user_name, ok = QInputDialog.getItem(self, "Assign Profile", 
                                              f"Select user profile for node {node_ip}:",
                                              user_list, 0, False)
        
        if ok and user_name:
            # Find the node's client socket and send ASSIGN_USER command
            with client_lock:
                for addr, client in client_data.items():
                    if client.get('node_ip') == node_ip:
                        try:
                            sock = client.get('sock')
                            if sock:
                                sock.write(f"ASSIGN_USER:{user_name}".encode())
                                asyncio.create_task(sock.drain())
                                self.status_label.setText(f"● Assigned {user_name} to {node_ip}")
                                logging.info(f"Assigned profile {user_name} to node {node_ip}")
                                QMessageBox.information(self, "Success", 
                                                       f"Profile '{user_name}' assigned to node {node_ip}")
                                self.refresh_nodes_list()
                                return
                        except Exception as e:
                            logging.error(f"Failed to assign profile: {e}")
            
            QMessageBox.warning(self, "Error", f"Node {node_ip} not connected")
    
    def rename_device(self, node_ip):
        """Show dialog to rename a device"""
        with config_lock:
            current_name = device_names.get(node_ip, '')
        
        with node_lock:
            if node_ip not in active_nodes:
                QMessageBox.warning(self, "Error", f"Node {node_ip} not found")
                return
            default_hostname = active_nodes[node_ip].get('hostname', 'Unknown')
        
        new_name, ok = QInputDialog.getText(self, "Rename Device", 
                                             f"Enter custom name for device {node_ip}:\n(Leave empty to use default: {default_hostname})",
                                             QLineEdit.EchoMode.Normal, current_name)
        
        if ok:
            with config_lock:
                if new_name.strip():
                    device_names[node_ip] = new_name.strip()
                    self.status_label.setText(f"● Renamed: {node_ip} → {new_name.strip()}")
                    logging.info(f"Device {node_ip} renamed to: {new_name.strip()}")
                else:
                    # Remove custom name to revert to default
                    if node_ip in device_names:
                        del device_names[node_ip]
                    self.status_label.setText(f"● Reset name for {node_ip}")
                    logging.info(f"Device {node_ip} name reset to default")
            
            self.refresh_nodes_list()
            save_config()
    
    def flash_node(self, node_ip):
        """Send flash command to node to identify it"""
        with client_lock:
            for addr, client in client_data.items():
                if client.get('node_ip') == node_ip:
                    try:
                        sock = client.get('sock')
                        if sock:
                            sock.write(b"FLASH_PACK")
                            asyncio.create_task(sock.drain())
                            self.status_label.setText(f"● Flashing node {node_ip}")
                            logging.info(f"Flash command sent to {node_ip}")
                            QMessageBox.information(self, "Flash Sent", 
                                                   f"Flash command sent to node {node_ip}")
                            return
                    except Exception as e:
                        logging.error(f"Failed to flash node: {e}")
        
        QMessageBox.warning(self, "Error", f"Node {node_ip} not connected")
    
    def show_add_user_dialog(self):
        """Show add user popup dialog"""
        dialog = AddUserDialog(self)
        if dialog.exec() == 1:  # Accepted
            user_name = dialog.get_user_name()
            selected_channels = dialog.get_selected_channels()
            
            if not user_name:
                QMessageBox.warning(self, "Error", "User name cannot be empty")
                return
            
            with config_lock:
                if user_name in users:
                    QMessageBox.warning(self, "Error", f"User '{user_name}' already exists")
                    return
                
                # Filter out None values for validation
                valid_channels = [ch for ch in selected_channels if ch is not None]
                if len(valid_channels) == 0:
                    QMessageBox.warning(self, "Error", "Please select at least one channel")
                    return
                
                users[user_name] = {
                    'channels': selected_channels,
                    'button_modes': {},  # Default empty, all channels default to latch
                    'client_addr': None
                }
            
            self.refresh_matrix()
            self.status_label.setText(f"● Added: {user_name}")
            logging.info(f"Added user: {user_name}")
    
    def on_mode_changed(self, mode_combo):
        """Handle button mode dropdown selection"""
        user_name = mode_combo.property('user_name')
        slot = mode_combo.property('slot')
        mode = mode_combo.currentData()  # 'latch' or 'non-latch'
        
        with config_lock:
            if user_name in users:
                if 'button_modes' not in users[user_name]:
                    users[user_name]['button_modes'] = {}
                users[user_name]['button_modes'][str(slot)] = mode
                
                mode_name = "Latch" if mode == 'latch' else "Non-Latch (Push-to-Talk)"
                logging.info(f"User {user_name}: Slot {slot+1} set to {mode_name}")
        
        # Push config to connected clients
        self.push_config_update(user_name)
    
    def on_program_device_changed(self, index):
        """Handle program audio device selection"""
        global program_audio_device, program_audio_channel
        device_data = self.program_device_combo.currentData()
        
        with config_lock:
            if device_data is not None:
                program_audio_device = device_data[0]  # Device index
                max_channels = device_data[1]
                
                # Update channel dropdown
                self.program_channel_combo.clear()
                for i in range(max_channels):
                    self.program_channel_combo.addItem(f"Ch {i+1}", i)
                
                # Reset to channel 0
                program_audio_channel = 0
                self.program_channel_combo.setCurrentIndex(0)
                
                device_name = self.program_device_combo.currentText()
                self.status_label.setText(f"● Program: {device_name} Ch {program_audio_channel+1}")
                logging.info(f"Program audio device: {device_name}")
            else:
                program_audio_device = None
                program_audio_channel = 0
                self.program_channel_combo.clear()
                self.program_channel_combo.addItem("Ch 1", 0)
                self.status_label.setText("● Program: Disabled")
                logging.info("Program audio disabled")
    
    def on_program_channel_changed(self, index):
        """Handle program audio channel selection"""
        global program_audio_channel
        channel_idx = self.program_channel_combo.currentData()
        
        if channel_idx is not None:
            with config_lock:
                program_audio_channel = channel_idx
            
            device_name = self.program_device_combo.currentText()
            self.status_label.setText(f"● Program: {device_name} Ch {program_audio_channel+1}")
            logging.info(f"Program audio channel set to: Ch {program_audio_channel+1}")
    
    def configure_button_modes(self, user_name):
        """Open button mode configuration dialog"""
        dialog = ButtonModeDialog(user_name, self)
        if dialog.exec() == 1:  # Accepted
            button_modes = dialog.get_button_modes()
            with config_lock:
                if user_name in users:
                    users[user_name]['button_modes'] = button_modes
            
            self.status_label.setText(f"● Updated modes: {user_name}")
            logging.info(f"Updated button modes for {user_name}: {button_modes}")
    
    def create_matrix_tab(self):
        """Matrix overview with user list and settings panel"""
        matrix = QWidget()
        main_layout = QVBoxLayout(matrix)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Top toolbar - Always visible buttons
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        save_preset_btn = QPushButton("💾 Save Preset")
        save_preset_btn.setMinimumWidth(120)
        save_preset_btn.setMinimumHeight(32)
        save_preset_btn.clicked.connect(self.save_preset)
        toolbar.addWidget(save_preset_btn)
        
        load_preset_btn = QPushButton("📁 Load Preset")
        load_preset_btn.setMinimumWidth(120)
        load_preset_btn.setMinimumHeight(32)
        load_preset_btn.clicked.connect(self.load_preset)
        toolbar.addWidget(load_preset_btn)
        
        new_config_btn = QPushButton("🆕 New Config")
        new_config_btn.setMinimumWidth(120)
        new_config_btn.setMinimumHeight(32)
        new_config_btn.clicked.connect(self.new_config)
        toolbar.addWidget(new_config_btn)
        
        export_btn = QPushButton("📤 Export")
        export_btn.setMinimumWidth(100)
        export_btn.setMinimumHeight(32)
        export_btn.clicked.connect(self.export_config)
        toolbar.addWidget(export_btn)
        
        add_user_btn = QPushButton("➕ Add User")
        add_user_btn.setMinimumWidth(100)
        add_user_btn.setMinimumHeight(32)
        add_user_btn.clicked.connect(self.show_add_user_dialog)
        toolbar.addWidget(add_user_btn)
        
        toolbar.addStretch()
        main_layout.addLayout(toolbar)
        
        # Split layout: User list on left, Settings panel on right
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - User list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        user_list_label = QLabel("User Profiles:")
        user_list_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #5096ff; padding: 4px;")
        left_layout.addWidget(user_list_label)
        
        from PyQt6.QtWidgets import QListWidget
        self.user_list_widget = QListWidget()
        self.user_list_widget.setMinimumWidth(200)
        self.user_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #232326; border: 1px solid #3a3a3f; border-radius: 4px;
                padding: 4px; color: #e6e6eb; font-size: 11pt;
            }
            QListWidget::item {
                padding: 10px; border-radius: 3px; margin: 2px;
            }
            QListWidget::item:hover {
                background-color: #2d2d32;
            }
            QListWidget::item:selected {
                background-color: #5096ff; color: #ffffff;
            }
        """)
        self.user_list_widget.currentItemChanged.connect(self.on_user_selected)
        left_layout.addWidget(self.user_list_widget)
        
        content_splitter.addWidget(left_panel)
        
        # Right side - Settings panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # Settings panel header
        settings_header = QLabel("User Settings")
        settings_header.setStyleSheet("font-size: 12pt; font-weight: bold; color: #5096ff; padding: 4px;")
        right_layout.addWidget(settings_header)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_layout.setSpacing(15)
        
        # Placeholder message when no user selected
        self.no_selection_label = QLabel("← Select a user profile to edit settings")
        self.no_selection_label.setStyleSheet("""
            color: #a0a0a5; font-size: 12pt; font-style: italic;
            padding: 40px; background-color: transparent;
        """)
        self.no_selection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.settings_layout.addWidget(self.no_selection_label)
        self.settings_layout.addStretch()
        
        scroll.setWidget(self.settings_container)
        right_layout.addWidget(scroll)
        
        content_splitter.addWidget(right_panel)
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(content_splitter)
        
        self.refresh_user_list()
        
        return matrix
    
    def push_config_update(self, user_name):
        """Push updated config to all connected clients using this user profile"""
        with config_lock:
            if user_name not in users:
                return
            
            sub_channels = set([ch for ch in users[user_name]['channels'] if ch is not None])
            # Filter to only enabled channels
            sub_channels_filtered = {ch for ch in sub_channels if channel_enabled.get(ch, False)}
            ch_names = {str(ch): channels.get(ch, f'CH{ch}') for ch in sub_channels_filtered}
            button_modes = users[user_name].get('button_modes', {})
            config_data = {'channels': ch_names, 'button_modes': button_modes}
            config_msg = f"UPDATE_CONFIG:{json.dumps(config_data)}".encode()
        
        # Send to all connected clients using this profile
        push_count = 0
        with client_lock:
            for addr, client in list(client_data.items()):
                if client.get('user_name') == user_name:
                    try:
                        sock = client.get('sock')
                        if sock:
                            sock.write(config_msg)
                            asyncio.create_task(sock.drain())
                            push_count += 1
                    except Exception as e:
                        logging.error(f"Failed to push config to {addr}: {e}")
        
        if push_count > 0:
            logging.info(f"Pushed config update to {push_count} client(s) for user '{user_name}'")
            self.status_label.setText(f"● Config pushed to {push_count} device(s)")
    
    def create_status_bar(self):
        """Status bar with live info"""
        status = QFrame()
        status.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2a2d, stop:1 #232326);
                border: 1px solid #3a3a3f; border-radius: 6px; padding: 6px;
            }
        """)
        layout = QHBoxLayout(status)
        layout.setSpacing(12)
        
        self.status_label = QLabel("● Ready")
        self.status_label.setStyleSheet("color: #4a4; font-weight: bold; font-size: 10pt;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.clients_label = QLabel("Clients: 0")
        self.clients_label.setStyleSheet("color: #5096ff; font-weight: bold; font-size: 10pt;")
        layout.addWidget(self.clients_label)
        
        self.talkers_label = QLabel("Talkers: 0")
        self.talkers_label.setStyleSheet("color: #ff9650; font-weight: bold; font-size: 10pt;")
        layout.addWidget(self.talkers_label)
        
        self.network_label = QLabel(f"TCP:{TCP_PORT} | UDP:{UDP_PORT}")
        self.network_label.setStyleSheet("color: #a0a0a5; font-size: 9pt;")
        layout.addWidget(self.network_label)
        
        return status
    
    def on_slot_changed(self, combo):
        """Handle channel selection changes in slot dropdowns"""
        user_name = combo.property('user_name')
        slot = combo.property('slot')
        new_ch_id = combo.currentData()  # None or channel ID
        
        with config_lock:
            if user_name not in users:
                return
            
            current_channels = users[user_name]['channels']
            
            # Ensure list has enough slots
            while len(current_channels) <= slot:
                current_channels.append(None)
            
            # Check if this channel is already assigned to another slot
            if new_ch_id is not None and new_ch_id in current_channels:
                other_slot = current_channels.index(new_ch_id)
                if other_slot != slot:
                    reply = QMessageBox.question(self, "Channel Already Assigned",
                                               f"This channel is already assigned to Button {other_slot+1}.\n"
                                               f"Move it to Button {slot+1}?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.No:
                        # Revert to previous value
                        old_ch = current_channels[slot]
                        if old_ch is not None:
                            idx = combo.findData(old_ch)
                            combo.setCurrentIndex(idx if idx >= 0 else 0)
                        else:
                            combo.setCurrentIndex(0)
                        return
                    else:
                        # Move channel: clear old slot and set new slot
                        current_channels[other_slot] = None
                        current_channels[slot] = new_ch_id
                        
                        # Clean up trailing None values
                        while current_channels and current_channels[-1] is None:
                            current_channels.pop()
                        
                        users[user_name]['channels'] = current_channels
                        
                        ch_name = channels.get(new_ch_id, f"CH{new_ch_id}") if new_ch_id is not None else "None"
                        logging.info(f"User {user_name}: Moved {ch_name} from Button {other_slot+1} to Button {slot+1}")
                        
                        # Refresh the GUI to update both dropdowns
                        self.populate_settings_panel(user_name)
                        
                        # Push config to connected clients
                        self.push_config_update(user_name)
                        return
            
            # Set the new channel for this slot (normal assignment, no conflict)
            current_channels[slot] = new_ch_id
            
            # Clean up trailing None values
            while current_channels and current_channels[-1] is None:
                current_channels.pop()
            
            users[user_name]['channels'] = current_channels
            
            ch_name = channels.get(new_ch_id, f"CH{new_ch_id}") if new_ch_id is not None else "None"
            logging.info(f"User {user_name}: Button {slot+1} set to {ch_name}")
        
        # Push config to connected clients
        self.push_config_update(user_name)
    
    def get_device_count(self, user_name):
        """Get count of devices using this user profile"""
        with node_lock:
            count = sum(1 for node_data in active_nodes.values() 
                       if node_data.get('user_name') == user_name)
        return count
    
    def show_device_list(self, user_name):
        """Show popup with list of devices using this profile"""
        with node_lock:
            device_ips = [ip for ip, node_data in active_nodes.items() 
                         if node_data.get('user_name') == user_name]
        
        if device_ips:
            ip_list = '\n'.join(device_ips)
            QMessageBox.information(self, f"Devices using '{user_name}'", 
                                   f"IP Addresses:\n\n{ip_list}")
        else:
            QMessageBox.information(self, f"Devices using '{user_name}'", 
                                   "No devices are currently using this profile.")
    
    def refresh_user_list(self):
        """Update the user list widget"""
        self.user_list_widget.clear()
        with config_lock:
            for user_name in sorted(users.keys()):
                device_count = self.get_device_count(user_name)
                display_text = f"{user_name}"
                if device_count > 0:
                    display_text += f"  (📱 {device_count})"
                
                from PyQt6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, user_name)
                self.user_list_widget.addItem(item)
    
    def on_user_selected(self, current, previous):
        """Handle user selection in the list"""
        if not current:
            self.clear_settings_panel()
            return
        
        user_name = current.data(Qt.ItemDataRole.UserRole)
        self.populate_settings_panel(user_name)
    
    def clear_settings_panel(self):
        """Clear all widgets from settings panel"""
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        # Show placeholder
        self.no_selection_label = QLabel("← Select a user profile to edit settings")
        self.no_selection_label.setStyleSheet("""
            color: #a0a0a5; font-size: 12pt; font-style: italic;
            padding: 40px; background-color: transparent;
        """)
        self.no_selection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.settings_layout.addWidget(self.no_selection_label)
        self.settings_layout.addStretch()
    
    def populate_settings_panel(self, user_name):
        """Populate the settings panel with user configuration options"""
        # Clear existing widgets
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        with config_lock:
            if user_name not in users:
                return
            user_channels = users[user_name]['channels'].copy()
            button_modes = users[user_name].get('button_modes', {}).copy()
            # Only show enabled/active channels
            available_channels = {ch_id: name for ch_id, name in channels.items() 
                                 if channel_enabled.get(ch_id, False)}
            available_channels[-1] = 'Program'
        
        # Action buttons
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        rename_btn = QPushButton("✏️ Rename User")
        rename_btn.setMinimumHeight(35)
        rename_btn.clicked.connect(lambda: self.rename_user_inline(user_name))
        actions_layout.addWidget(rename_btn)
        
        duplicate_btn = QPushButton("📋 Duplicate User")
        duplicate_btn.setMinimumHeight(35)
        duplicate_btn.clicked.connect(lambda: self.duplicate_user_inline(user_name))
        actions_layout.addWidget(duplicate_btn)
        
        delete_btn = QPushButton("🗑 Delete User")
        delete_btn.setMinimumHeight(35)
        delete_btn.clicked.connect(lambda: self.delete_user_inline(user_name))
        actions_layout.addWidget(delete_btn)
        
        flash_btn = QPushButton("💡 Flash User")
        flash_btn.setMinimumHeight(35)
        flash_btn.clicked.connect(lambda: self.flash_user_packs(user_name))
        actions_layout.addWidget(flash_btn)
        
        actions_group.setLayout(actions_layout)
        self.settings_layout.addWidget(actions_group)
        
        # Device info
        device_count = self.get_device_count(user_name)
        device_info_label = QLabel(f"📱 {device_count} device(s) using this profile")
        device_info_label.setStyleSheet("color: #5096ff; font-size: 10pt; padding: 5px;")
        device_info_label.setCursor(Qt.CursorShape.PointingHandCursor)
        device_info_label.mousePressEvent = lambda ev: self.show_device_list(user_name)
        self.settings_layout.addWidget(device_info_label)
        
        # Channel assignments - compact 2x2 grid
        channels_group = QGroupBox("Channel Assignments")
        channels_grid = QGridLayout()
        channels_grid.setSpacing(6)
        channels_grid.setContentsMargins(8, 8, 8, 8)
        
        for slot in range(MAX_USER_CHANNELS):
            row = slot // 2
            col = slot % 2
            
            slot_container = QFrame()
            slot_container.setStyleSheet("""
                QFrame {
                    background-color: #2d2d32; border: 1px solid #3a3a3f; border-radius: 3px;
                    padding: 6px;
                }
            """)
            slot_layout = QVBoxLayout(slot_container)
            slot_layout.setSpacing(4)
            slot_layout.setContentsMargins(4, 4, 4, 4)
            
            slot_header = QLabel(f"Button {slot+1}")
            slot_header.setStyleSheet("font-size: 9pt; font-weight: bold; color: #5096ff;")
            slot_layout.addWidget(slot_header)
            
            # Channel selection
            ch_layout = QHBoxLayout()
            ch_label = QLabel("Ch:")
            ch_label.setMinimumWidth(35)
            ch_label.setStyleSheet("color: #e6e6eb; font-size: 9pt;")
            ch_layout.addWidget(ch_label)
            
            ch_combo = QComboBox()
            ch_combo.setMinimumHeight(26)
            ch_combo.addItem("-- None --", None)
            for ch_id in sorted(available_channels.keys()):
                ch_name = available_channels[ch_id]
                ch_combo.addItem(ch_name, ch_id)
            
            current_ch = None
            if slot < len(user_channels):
                current_ch = user_channels[slot]
            
            if current_ch is not None:
                idx_ch = ch_combo.findData(current_ch)
                if idx_ch >= 0:
                    ch_combo.setCurrentIndex(idx_ch)
            
            ch_combo.setProperty('user_name', user_name)
            ch_combo.setProperty('slot', slot)
            ch_combo.currentIndexChanged.connect(lambda idx, c=ch_combo: self.on_slot_changed(c))
            ch_layout.addWidget(ch_combo)
            slot_layout.addLayout(ch_layout)
            
            # Latching mode
            mode_layout = QHBoxLayout()
            mode_label = QLabel("Latch:")
            mode_label.setMinimumWidth(35)
            mode_label.setStyleSheet("color: #e6e6eb; font-size: 9pt;")
            mode_layout.addWidget(mode_label)
            
            current_mode = button_modes.get(str(slot), 'latch')
            mode_combo = QComboBox()
            mode_combo.setMinimumHeight(26)
            mode_combo.addItem("Off", "non-latch")
            mode_combo.addItem("On", "latch")
            mode_combo.setCurrentIndex(1 if current_mode == 'latch' else 0)
            mode_combo.setProperty('user_name', user_name)
            mode_combo.setProperty('slot', slot)
            mode_combo.currentIndexChanged.connect(lambda idx, c=mode_combo: self.on_mode_changed(c))
            mode_layout.addWidget(mode_combo)
            slot_layout.addLayout(mode_layout)
            
            channels_grid.addWidget(slot_container, row, col)
        
        channels_group.setLayout(channels_grid)
        self.settings_layout.addWidget(channels_group)
        
        self.settings_layout.addStretch()
    
    def rename_user_inline(self, user_name):
        """Rename user and refresh both list and panel"""
        new_name, ok = QInputDialog.getText(self, "Rename User", 
                                             f"Enter new name for '{user_name}':",
                                             QLineEdit.EchoMode.Normal, user_name)
        
        if ok and new_name and new_name != user_name:
            new_name = new_name.strip()
            
            with config_lock:
                if new_name in users:
                    QMessageBox.warning(self, "Error", f"User '{new_name}' already exists")
                    return
                
                if user_name in users:
                    users[new_name] = users[user_name].copy()
                    del users[user_name]
            
            self.refresh_user_list()
            # Select the renamed user
            for i in range(self.user_list_widget.count()):
                item = self.user_list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == new_name:
                    self.user_list_widget.setCurrentItem(item)
                    break
            
            self.status_label.setText(f"● Renamed: {user_name} → {new_name}")
            logging.info(f"Renamed user: {user_name} → {new_name}")
    
    def duplicate_user_inline(self, user_name):
        """Duplicate user and refresh both list and panel"""
        new_name, ok = QInputDialog.getText(self, "Duplicate User", 
                                             f"Enter name for duplicate of '{user_name}':",
                                             QLineEdit.EchoMode.Normal, f"{user_name} Copy")
        
        if ok and new_name:
            new_name = new_name.strip()
            
            with config_lock:
                if new_name in users:
                    QMessageBox.warning(self, "Error", f"User '{new_name}' already exists")
                    return
                
                if user_name in users:
                    import copy
                    users[new_name] = {
                        'channels': users[user_name]['channels'].copy(),
                        'button_modes': users[user_name].get('button_modes', {}).copy(),
                        'client_addr': None
                    }
            
            self.refresh_user_list()
            # Select the new user
            for i in range(self.user_list_widget.count()):
                item = self.user_list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == new_name:
                    self.user_list_widget.setCurrentItem(item)
                    break
            
            self.status_label.setText(f"● Duplicated: {user_name} → {new_name}")
            logging.info(f"Duplicated user: {user_name} → {new_name}")
    
    def delete_user_inline(self, user_name):
        """Delete user and refresh list"""
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Delete user '{user_name}'?\n\nThis will disconnect them if online.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            with config_lock:
                if user_name in users:
                    del users[user_name]
            
            self.refresh_user_list()
            self.clear_settings_panel()
            self.status_label.setText(f"● Deleted: {user_name}")
            logging.info(f"Deleted user: {user_name}")
    
    def flash_user_packs(self, user_name):
        """Flash all belt packs that have this user profile loaded"""
        with client_lock:
            flash_count = 0
            for addr, client in client_data.items():
                if client.get('user_name') == user_name:
                    try:
                        sock = client.get('sock')
                        if sock:
                            sock.write(b"FLASH_PACK")
                            asyncio.create_task(sock.drain())
                            flash_count += 1
                    except Exception as e:
                        logging.error(f"Failed to flash pack at {addr}: {e}")
        
        if flash_count > 0:
            self.status_label.setText(f"● Flashing {flash_count} pack(s) for user '{user_name}'")
            logging.info(f"Flashed {flash_count} pack(s) for user '{user_name}'")
        else:
            self.status_label.setText(f"● No packs online for user '{user_name}'")
            QMessageBox.information(self, "No Devices", 
                                   f"No belt packs are currently connected with user profile '{user_name}'")
        
        # Refresh the GUI to show current profile state
        self.populate_settings_panel(user_name)
    
    def refresh_matrix(self):
        """Update user list (compatibility method)"""
        self.refresh_user_list()
    
    def on_volume_changed(self, channel_id, volume):
        """Handle volume change"""
        with config_lock:
            channel_volumes[channel_id] = volume / 100.0
        logging.debug(f"CH{channel_id} volume: {volume}%")
    
    def on_name_changed(self, channel_id, new_name):
        """Handle channel rename"""
        with config_lock:
            channels[channel_id] = new_name
        
        self.refresh_matrix()
        self.status_label.setText(f"● Renamed CH{channel_id}: {new_name}")
        logging.info(f"Channel {channel_id} renamed to: {new_name}")
    
    def on_channel_enabled_changed(self, channel_id, enabled):
        """Handle channel enable/disable"""
        with config_lock:
            # Calculate what the count WOULD BE after this change
            current_count = sum(channel_enabled.values())
            # If disabling and this would put us below 1, prevent it
            if not enabled:
                new_count = current_count - (1 if channel_enabled.get(channel_id, False) else 0)
                if new_count < 1:
                    # Prevent disabling - would go below minimum
                    QMessageBox.warning(self, "Minimum Channels", 
                                       "Cannot disable channel.\n\nMinimum of 1 channel must remain active.")
                    # Block signals to prevent recursion, then re-check the checkbox
                    if channel_id in self.channel_strips:
                        self.channel_strips[channel_id].enable_checkbox.blockSignals(True)
                        self.channel_strips[channel_id].enable_checkbox.setChecked(True)
                        self.channel_strips[channel_id].enable_checkbox.blockSignals(False)
                    return
            
            channel_enabled[channel_id] = enabled
            active_count = sum(channel_enabled.values())
        
        status = "enabled" if enabled else "disabled"
        self.status_label.setText(f"● CH{channel_id} {status} ({active_count} active)")
        logging.info(f"Channel {channel_id} {status} - {active_count} channels active")

        # If disabling, immediately drop talkers/listeners and buffers so audio stops
        if not enabled:
            with audio_lock:
                channel_listeners.pop(channel_id, None)
                channel_talkers.pop(channel_id, None)
                channel_buffers.pop(channel_id, None)
                channel_last_activity.pop(channel_id, None)
                channel_seq_tracking.pop(channel_id, None)
                channel_levels.pop(channel_id, None)
        
        # Refresh the settings panel if a user is currently selected
        current_item = self.user_list_widget.currentItem()
        if current_item:
            user_name = current_item.data(Qt.ItemDataRole.UserRole)
            self.populate_settings_panel(user_name)
    
    def save_preset(self):
        """Save configuration preset to file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Preset", "", "JSON Files (*.json)")
        if filename:
            global CONFIG_FILE
            old_file = CONFIG_FILE
            CONFIG_FILE = filename
            save_config()
            CONFIG_FILE = old_file
            QMessageBox.information(self, "Success", f"Preset saved to {filename}")
            self.status_label.setText(f"● Preset saved")
    
    def load_preset(self):
        """Load configuration preset from file"""
        filename, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "JSON Files (*.json)")
        if filename:
            global CONFIG_FILE
            old_file = CONFIG_FILE
            CONFIG_FILE = filename
            load_config()
            CONFIG_FILE = old_file
            
            # Update mixer channel strips
            with config_lock:
                for ch_id, strip in self.channel_strips.items():
                    strip.name_input.setText(channels.get(ch_id, f'Channel {ch_id+1}'))
                    strip.volume_slider.setValue(int(channel_volumes.get(ch_id, 0.8) * 100))
            
            self.refresh_user_list()
            QMessageBox.information(self, "Success", f"Preset loaded from {filename}")
            self.status_label.setText("● Preset loaded")
    
    def new_config(self):
        """Create new clean configuration with no users"""
        reply = QMessageBox.question(self, "New Configuration",
                                     "Create new configuration?\n\nThis will:\n1. Save current config\n2. Create fresh config with no users\n3. Keep default 4 channels active",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Save current config first
            save_config()
            
            # Create fresh config
            global users, channels, channel_volumes, channel_enabled, active_channel_count
            with config_lock:
                users = {}  # Empty users dict
                channels = {i: f'Channel {i+1}' for i in range(MAX_CHANNELS)}
                channel_volumes = {i: 0.8 for i in range(MAX_CHANNELS)}
                channel_enabled = {i: i < 4 for i in range(MAX_CHANNELS)}  # 4 channels enabled
                active_channel_count = 4
            
            # Save new config
            save_config()
            
            # Update mixer channel strips
            for ch_id, strip in self.channel_strips.items():
                if ch_id >= 0:  # Skip program channel
                    strip.name_input.setText(channels.get(ch_id, f'Channel {ch_id+1}'))
                    strip.volume_slider.setValue(int(channel_volumes.get(ch_id, 0.8) * 100))
                    strip.enable_checkbox.setChecked(channel_enabled.get(ch_id, False))
            
            # Clear user list
            self.refresh_user_list()
            self.clear_settings_panel()
            
            QMessageBox.information(self, "Success", "New configuration created with 4 active channels")
            self.status_label.setText("● New config created")
            logging.info("Created new clean configuration")
    
    def on_channel_name_changed(self, name_input):
        """Handle channel name change from matrix tab"""
        ch_id = name_input.property('channel_id')
        new_name = name_input.text().strip()
        if new_name:
            with config_lock:
                channels[ch_id] = new_name
            
            # Update mixer strip name
            if ch_id in self.channel_strips:
                self.channel_strips[ch_id].name_input.setText(new_name)
            
            # Refresh user profile settings panel if a user is selected
            current_item = self.user_list_widget.currentItem()
            if current_item:
                user_name = current_item.data(Qt.ItemDataRole.UserRole)
                self.populate_settings_panel(user_name)
            
            self.refresh_user_list()
            self.status_label.setText(f"● Renamed CH{ch_id}: {new_name}")
            logging.info(f"Channel {ch_id} renamed to: {new_name}")
    
    def save_config(self):
        """Save configuration"""
        save_config()
        QMessageBox.information(self, "Success", f"Configuration saved to {CONFIG_FILE}")
        self.status_label.setText("● Configuration saved")
    
    def load_config(self):
        """Load configuration"""
        load_config()
        
        with config_lock:
            for ch_id, strip in self.channel_strips.items():
                strip.name_input.setText(channels.get(ch_id, f'Channel {ch_id+1}'))
                strip.volume_slider.setValue(int(channel_volumes.get(ch_id, 0.8) * 100))
        
        self.refresh_user_list()
        
        QMessageBox.information(self, "Success", f"Configuration loaded from {CONFIG_FILE}")
        self.status_label.setText("● Configuration loaded")
    
    def export_config(self):
        """Export to file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Export Configuration", "", "JSON Files (*.json)")
        
        if filename:
            global CONFIG_FILE
            old_file = CONFIG_FILE
            CONFIG_FILE = filename
            save_config()
            CONFIG_FILE = old_file
            
            QMessageBox.information(self, "Success", f"Exported to {filename}")
            self.status_label.setText(f"● Exported to {filename}")
    
    def update_status(self):
        """Update status indicators and level meters"""
        with client_lock:
            active_clients = len([c for c in client_data.values() if c.get('user_name')])
        
        with audio_lock:
            active_talkers = sum(len(v) for v in channel_talkers.values())
            levels_copy = dict(channel_levels)  # Copy for thread safety
        
        # Update level meters for all channel strips
        for ch_id, strip in self.channel_strips.items():
            level = levels_copy.get(ch_id, 0.0)
            strip.update_level(level)
        
        self.clients_label.setText(f"Clients: {active_clients}")
        self.talkers_label.setText(f"Talkers: {active_talkers}")
        
        if active_clients > 0:
            self.status_label.setText("● Online")
            self.status_label.setStyleSheet("color: #4a4; font-weight: bold; font-size: 10pt;")
        else:
            self.status_label.setText("● Standby")
            self.status_label.setStyleSheet("color: #ff9650; font-weight: bold; font-size: 10pt;")
    
    def on_fourwire_toggled(self, interface_idx):
        """Toggle 4-wire interface on/off"""
        checked = self.fourwire_enable_btn[interface_idx].isChecked()
        fourwire_enabled[interface_idx] = checked
        
        if checked:
            self.fourwire_enable_btn[interface_idx].setText("ON")
            # Start 4-wire interface if configured
            if fourwire_input_device[interface_idx] is not None and fourwire_output_device[interface_idx] is not None:
                self.start_fourwire_interface(interface_idx)
                self.status_label.setText(f"● 4-Wire {interface_idx + 1}: Enabled")
            else:
                self.fourwire_enable_btn[interface_idx].setChecked(False)
                fourwire_enabled[interface_idx] = False
                QMessageBox.warning(self, "4-Wire Not Configured",
                                   f"Please configure 4-Wire {interface_idx + 1} audio devices first.\nClick the ⚙ button.")
        else:
            self.fourwire_enable_btn[interface_idx].setText("OFF")
            self.stop_fourwire_interface(interface_idx)
            self.status_label.setText(f"● 4-Wire {interface_idx + 1}: Disabled")
    
    def on_fourwire_channel_changed(self, interface_idx):
        """Handle 4-wire channel assignment change"""
        fourwire_channel[interface_idx] = self.fourwire_channel_combo[interface_idx].currentData()
        if fourwire_channel[interface_idx] is not None:
            logging.info(f"4-Wire {interface_idx + 1} assigned to channel {fourwire_channel[interface_idx]}")
            self.status_label.setText(f"● 4-Wire {interface_idx + 1} → CH{fourwire_channel[interface_idx]}")
    
    def on_fourwire_input_changed(self, interface_idx):
        """Handle 4-wire input device change"""
        if interface_idx == 0:
            fourwire_input_device[interface_idx] = self.fourwire_input_combo_1.currentData()
        else:
            fourwire_input_device[interface_idx] = self.fourwire_input_combo_2.currentData()
        save_config()
        self.status_label.setText(f"● 4-Wire {interface_idx + 1} input device updated")
        
        # If 4-wire is currently enabled, restart with new config
        if fourwire_enabled[interface_idx]:
            self.stop_fourwire_interface(interface_idx)
            # Wait for thread to terminate (max 1 second)
            if fourwire_thread[interface_idx] is not None:
                fourwire_thread[interface_idx].join(timeout=1.0)
            if fourwire_input_device[interface_idx] is not None and fourwire_output_device[interface_idx] is not None:
                self.start_fourwire_interface(interface_idx)
    
    def on_fourwire_output_changed(self, interface_idx):
        """Handle 4-wire output device change"""
        if interface_idx == 0:
            fourwire_output_device[interface_idx] = self.fourwire_output_combo_1.currentData()
        else:
            fourwire_output_device[interface_idx] = self.fourwire_output_combo_2.currentData()
        save_config()
        self.status_label.setText(f"● 4-Wire {interface_idx + 1} output device updated")
        
        # If 4-wire is currently enabled, restart with new config
        if fourwire_enabled[interface_idx]:
            self.stop_fourwire_interface(interface_idx)
            # Wait for thread to terminate (max 1 second)
            if fourwire_thread[interface_idx] is not None:
                fourwire_thread[interface_idx].join(timeout=1.0)
            if fourwire_input_device[interface_idx] is not None and fourwire_output_device[interface_idx] is not None:
                self.start_fourwire_interface(interface_idx)
    
    def on_fourwire_gain_changed(self, interface_idx, direction, value):
        """Handle 4-wire gain slider change"""
        gain = value / 100.0
        if direction == 'input':
            fourwire_input_gain[interface_idx] = gain
        else:
            fourwire_output_gain[interface_idx] = gain
        save_config()
    
    def start_fourwire_interface(self, interface_idx):
        """Start 4-wire audio interface"""
        if fourwire_input_device[interface_idx] is None or fourwire_output_device[interface_idx] is None:
            logging.warning(f"4-Wire {interface_idx + 1} devices not configured")
            return
        
        if p is None:
            logging.error(f"4-Wire {interface_idx + 1}: PyAudio not initialized")
            return
        
        try:
            # Start input stream
            fourwire_stream_in[interface_idx] = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                input_device_index=fourwire_input_device[interface_idx],
                frames_per_buffer=CHUNK
            )
            
            # Start output stream
            fourwire_stream_out[interface_idx] = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                output=True,
                output_device_index=fourwire_output_device[interface_idx],
                frames_per_buffer=CHUNK
            )
            
            fourwire_running[interface_idx] = True
            fourwire_thread[interface_idx] = threading.Thread(target=lambda: self.fourwire_audio_loop(interface_idx), daemon=True)
            fourwire_thread[interface_idx].start()
            
            logging.info(f"✓ 4-Wire {interface_idx + 1} interface started")
        except Exception as e:
            logging.error(f"4-Wire {interface_idx + 1} start error: {e}")
            self.stop_fourwire_interface(interface_idx)
    
    def stop_fourwire_interface(self, interface_idx):
        """Stop 4-wire audio interface"""
        fourwire_running[interface_idx] = False
        
        if fourwire_stream_in[interface_idx]:
            try:
                fourwire_stream_in[interface_idx].stop_stream()
                fourwire_stream_in[interface_idx].close()
            except:
                pass
            fourwire_stream_in[interface_idx] = None
        
        if fourwire_stream_out[interface_idx]:
            try:
                fourwire_stream_out[interface_idx].stop_stream()
                fourwire_stream_out[interface_idx].close()
            except:
                pass
            fourwire_stream_out[interface_idx] = None
        
        logging.info(f"✓ 4-Wire {interface_idx + 1} interface stopped")
    
    def fourwire_audio_loop(self, interface_idx):
        """4-Wire audio processing thread - acts as virtual beltpack"""
        FOURWIRE_USER_ID = -2 - interface_idx  # Unique user ID per interface (-2, -3)
        
        while fourwire_running[interface_idx]:
            try:
                # INPUT: Read from external system, inject into channel
                if fourwire_stream_in[interface_idx]:
                    try:
                        audio_bytes = fourwire_stream_in[interface_idx].read(CHUNK, exception_on_overflow=False)
                        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                        
                        # Apply input gain
                        audio_np *= fourwire_input_gain[interface_idx]
                        
                        # Inject into channel buffer as if from a beltpack
                        with audio_lock:
                            channel_buffers[fourwire_channel[interface_idx]][FOURWIRE_USER_ID].append(audio_np)
                            channel_talkers[fourwire_channel[interface_idx]].add(FOURWIRE_USER_ID)
                    except Exception as e:
                        logging.debug(f"4-Wire {interface_idx + 1} input error: {e}")
                
                # OUTPUT: Tap channel mix, send to external system
                if fourwire_stream_out[interface_idx]:
                    try:
                        # Get mixed audio from this channel (for all talkers EXCEPT the 4-wire itself)
                        mixed_audio = np.zeros(CHUNK, dtype=np.float32)
                        active_sources = 0
                        
                        with audio_lock:
                            if fourwire_channel[interface_idx] in channel_buffers:
                                for uid, queue in channel_buffers[fourwire_channel[interface_idx]].items():
                                    if uid != FOURWIRE_USER_ID and queue:  # Exclude 4-wire's own audio
                                        try:
                                            chunk = queue.popleft()
                                            mixed_audio += chunk
                                            active_sources += 1
                                        except:
                                            pass
                        
                        # Normalize if multiple sources
                        if active_sources > 1:
                            mixed_audio /= active_sources
                        
                        # Apply output gain and channel volume
                        with config_lock:
                            vol = channel_volumes.get(fourwire_channel[interface_idx], 0.8)
                        
                        mixed_audio *= (fourwire_output_gain[interface_idx] * vol)
                        mixed_audio = np.clip(mixed_audio, -1, 1)
                        
                        # Convert to int16 and send
                        pcm_data = (mixed_audio * 32767).astype(np.int16)
                        fourwire_stream_out[interface_idx].write(pcm_data.tobytes())
                    except Exception as e:
                        logging.debug(f"4-Wire {interface_idx + 1} output error: {e}")
                
                # No sleep needed - PyAudio read() blocks for CHUNK duration
            except Exception as e:
                logging.error(f"4-Wire {interface_idx + 1} loop error: {e}")
                time.sleep(0.02)  # Brief sleep on error
    
    def closeEvent(self, event):
        """Handle window close"""
        reply = QMessageBox.question(self, "Confirm Exit",
                                     "Save configuration before exiting?",
                                     QMessageBox.StandardButton.Yes | 
                                     QMessageBox.StandardButton.No | 
                                     QMessageBox.StandardButton.Cancel)
        
        if reply == QMessageBox.StandardButton.Yes:
            save_config()
            # Stop 4-wire interfaces
            for i in range(2):
                if fourwire_enabled[i]:
                    self.stop_fourwire_interface(i)
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            # Stop 4-wire interfaces
            for i in range(2):
                if fourwire_enabled[i]:
                    self.stop_fourwire_interface(i)
            event.accept()
        else:
            event.ignore()


# ===== ASYNC SERVER RUNNER =====

def run_async():
    """Run async server in background"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logging.info("Server stopped")
    except Exception as e:
        logging.error(f"Server error: {e}", exc_info=True)


async def node_cleanup_task():
    """Periodically clean up stale node entries"""
    while True:
        await asyncio.sleep(30)  # Check every 30 seconds
        current_time = time.time()
        with node_lock:
            stale_nodes = [ip for ip, data in active_nodes.items() 
                          if current_time - data['last_seen'] > 60]  # 60 second timeout
            for ip in stale_nodes:
                logging.info(f"Node timeout: {ip}")
                del active_nodes[ip]


async def async_main():
    """Main async entry point"""
    global zeroconf_instance, zeroconf_service
    udp_sock = None
    try:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # HelixNet QoS: DSCP AF41 (0x88 = 34 << 2) for audio priority
        try:
            udp_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0x88)
            logging.info("✓ QoS enabled: DSCP AF41 (priority audio)")
        except Exception as e:
            logging.warning(f"QoS setup failed (requires admin): {e}")
        
        udp_sock.bind((HOST, UDP_PORT))
        udp_sock.setblocking(False)
        
        # Start mDNS service broadcasting
        try:
            zeroconf_instance = Zeroconf()
            # Get local IP address
            local_ip = socket.gethostbyname(socket.gethostname())
            
            service_info = ServiceInfo(
                "_lancomm._tcp.local.",
                "LanCommServer._lancomm._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=TCP_PORT,
                properties={'version': '1.0', 'type': 'server'},
            )
            zeroconf_instance.register_service(service_info)
            zeroconf_service = service_info
            logging.info(f"🌐 mDNS service registered: {local_ip}:{TCP_PORT}")
        except Exception as e:
            logging.warning(f"mDNS registration failed: {e}")
        
        logging.info(f"🚀 Server starting on TCP:{TCP_PORT}, UDP:{UDP_PORT}")
        
        tasks = [
            asyncio.create_task(receive_udp(udp_sock)),
            asyncio.create_task(mix_and_send(udp_sock)),
            asyncio.create_task(tcp_server()),
            asyncio.create_task(node_cleanup_task())
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logging.error(f"Async error: {e}", exc_info=True)
    finally:
        # Cleanup UDP socket
        if udp_sock:
            try:
                udp_sock.close()
            except:
                pass
        
        # Cleanup mDNS
        if zeroconf_instance and zeroconf_service:
            try:
                zeroconf_instance.unregister_service(zeroconf_service)
                zeroconf_instance.close()
            except:
                pass


# ===== MAIN ENTRY POINT =====

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        
        # Apply professional theme
        BroadcastTheme.apply(app)
        
        # Create and show GUI
        window = ServerGUI()
        window.show()
        
        # Start async server
        threading.Thread(target=run_async, daemon=True).start()
        
        # Run Qt event loop
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Application error: {e}", exc_info=True)
        raise
