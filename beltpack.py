"""
LanComm Pro Beltpack Firmware
Hardware-optimized intercom belt pack for SBCs with RGB LED buttons
"""

import sys
import asyncio
import pyaudio
import numpy as np
import json
import time
import queue
import logging
from collections import defaultdict
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QComboBox, QListWidget, QListWidgetItem, QProgressBar
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
import socket
import threading

# Hardware imports for SBC deployment
HARDWARE_AVAILABLE = False
try:
    import smbus2  # type: ignore
    import gpiod  # type: ignore
    from gpiod import LINE_REQ_DIR_IN, LINE_REQ_EV_RISING_EDGE, LINE_REQ_EV_FALLING_EDGE  # type: ignore
    HARDWARE_AVAILABLE = True
except ImportError:
    logging.warning("Hardware libraries not available - running in simulation mode")

# mDNS discovery
try:
    from zeroconf import ServiceBrowser, Zeroconf, ServiceListener
    MDNS_AVAILABLE = True
except ImportError:
    logging.warning("zeroconf not available - using hardcoded server IP")
    MDNS_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# ===== mDNS DISCOVERY =====

class ServerListener(ServiceListener):
    """mDNS service listener for server discovery"""
    def __init__(self):
        self.server_found = False
        self.server_ip = None
        self.server_port = None
    
    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            self.server_ip = socket.inet_ntoa(info.addresses[0])
            self.server_port = info.port
            self.server_found = True
            logging.info(f"🌐 Server discovered: {self.server_ip}:{self.server_port}")
    
    def remove_service(self, zc, type_, name):
        logging.warning(f"Server service removed: {name}")
    
    def update_service(self, zc, type_, name):
        pass


async def discover_server_async(timeout=10.0):
    """Discover server via mDNS with timeout"""
    if not MDNS_AVAILABLE:
        logging.info(f"mDNS not available, using hardcoded: {SERVER_HOST}:{TCP_PORT}")
        return SERVER_HOST, TCP_PORT
    
    try:
        zeroconf = Zeroconf()
        listener = ServerListener()
        browser = ServiceBrowser(zeroconf, "_lancomm._tcp.local.", listener)
        
        # Wait for discovery
        start_time = time.time()
        while time.time() - start_time < timeout:
            if listener.server_found:
                zeroconf.close()
                return listener.server_ip, listener.server_port
            await asyncio.sleep(0.1)
        
        # Timeout - use fallback
        zeroconf.close()
        logging.warning(f"mDNS discovery timeout, using fallback: {SERVER_HOST}:{TCP_PORT}")
        return SERVER_HOST, TCP_PORT
        
    except Exception as e:
        logging.error(f"mDNS discovery error: {e}, using fallback")
        return SERVER_HOST, TCP_PORT


# ===== CONFIGURATION =====
SERVER_HOST = '192.168.1.10'
TCP_PORT = 6001  # HelixNet standard port
UDP_PORT = 6001  # HelixNet standard port
RATE = 48000
CHUNK = 960
MAX_NODE_CHANNELS = 10  # Increased to support all 10 channels
JITTER_BUFFER_SIZE = 6  # Increased to 128ms for HelixNet parity
SIDETONE_LEVEL = 0.18  # Local sidetone gain (0.0-1.0)
AUTH_KEY = "lancomm-secure-2025"  # Must match server

# Headset Configuration
HEADSET_MODE = 'electret'  # 'electret' or 'dynamic' - set per deployment
MIC_BIAS_ENABLED = True  # Enable bias for electret mics (disable for dynamic Clear-Com)

# ===== ORANGE PI 5 PRO HARDWARE CONFIGURATION =====
# Platform: Orange Pi 5 Pro 16GB (RK3588S) + Waveshare PoE HAT
# Benefits: 8-core CPU (4xA76 + 4xA55), BUILT-IN Audio I/O (ES8388 codec), native 2.5G Ethernet
# Audio: Built-in ES8388 codec (no external HAT needed) - stereo I/O, 48kHz 16-bit
# I2C bus 3 (GPIO 2=SDA, 3=SCL) for RGB LED buttons - verify bus number with i2cdetect
# Note: GPIO chip may be 'gpiochip1' instead of 'gpiochip0' - adjust in code

# Hardware I2C Addresses (DFRobotics DFR0785 - Gravity I2C RGB LED Button Module)
# LED States: Yellow = Assigned channel (listening), Red = Active talk
RGB_BUTTON_ADDRESSES = [0x23, 0x24, 0x25, 0x26]  # 4 RGB LED buttons on I2C bus 3

# Rotary Encoder GPIO Pins (avoiding I2S: 18,19,20,21)
# Using EC11 rotary encoders with quadrature output
ROTARY_ENCODER_PINS = [
    (5, 6),      # Encoder 1: CLK=GPIO5, DT=GPIO6
    (13, 19),    # Encoder 2: CLK=GPIO13, DT=GPIO19 (Note: GPIO19 is I2S but safe for input reading)
    (26, 12),    # Encoder 3: CLK=GPIO26, DT=GPIO12
    (16, 7)      # Encoder 4: CLK=GPIO16, DT=GPIO7
]

# Menu Rotary Encoder (navigation and settings)
MENU_ENCODER_GPIO_CLK = 17  # Menu rotary encoder CLK pin
MENU_ENCODER_GPIO_DT = 27   # Menu rotary encoder DT pin
MENU_ENCODER_GPIO_SW = 22   # Menu rotary encoder button pin

# Microphone Bias Control (for 4-pin XLR headset compatibility)
MIC_BIAS_GPIO = 23  # GPIO to control bias power relay/switch
# Headset modes: 'electret' = bias ON (consumer headsets, some Clear-Com)
#                'dynamic' = bias OFF (Clear-Com CC-110/300, broadcast headsets)

# ===== HARDWARE ABSTRACTION LAYER =====

class RGBButton:
    """Gravity I2C RGB LED Button Module interface"""
    def __init__(self, i2c_bus, address):
        self.bus = i2c_bus
        self.addr = address
        self.pressed = False
        self.last_state = 0
        
    def set_color(self, r, g, b):
        """Set RGB LED color (0-255 each)"""
        try:
            self.bus.write_i2c_block_data(self.addr, 0x00, [r, g, b])
        except:
            pass
    
    def read_button(self):
        """Read button state (True if pressed)"""
        try:
            data = self.bus.read_byte_data(self.addr, 0x03)
            return data == 1
        except:
            return False
    
    def flash(self, duration=0.5):
        """Flash the button (white)"""
        self.set_color(255, 255, 255)
        time.sleep(duration)
        self.set_color(0, 0, 0)


class RotaryEncoder:
    """Rotary encoder for volume control (GPIO-based)
    
    Hardware: EC11 rotary encoder with quadrature output
    Wiring: CLK and DT pins to GPIO, common to GND
    Internal pull-ups enabled via gpiod
    """
    def __init__(self, clk_pin, dt_pin, min_val=0, max_val=100):
        self.clk_pin = clk_pin
        self.dt_pin = dt_pin
        self.value = 50  # Default mid-range
        self.min_val = min_val
        self.max_val = max_val
        self.last_clk = 1
        
        if HARDWARE_AVAILABLE:
            # Orange Pi 5 uses gpiochip1 for main GPIO (verify with: gpioinfo)
            self.chip = gpiod.Chip('gpiochip1')  # Orange Pi 5 GPIO chip
            self.clk_line = self.chip.get_line(clk_pin)
            self.dt_line = self.chip.get_line(dt_pin)
            self.clk_line.request(consumer='rotary', type=LINE_REQ_DIR_IN)
            self.dt_line.request(consumer='rotary', type=LINE_REQ_DIR_IN)
    
    def read(self):
        """Read current position"""
        if not HARDWARE_AVAILABLE:
            return self.value
        
        try:
            clk = self.clk_line.get_value()
            dt = self.dt_line.get_value()
            
            if clk != self.last_clk and clk == 0:
                if dt != clk:
                    self.value = min(self.max_val, self.value + 1)
                else:
                    self.value = max(self.min_val, self.value - 1)
            
            self.last_clk = clk
            return self.value
        except:
            return self.value


class MenuRotaryEncoder(RotaryEncoder):
    """Menu rotary encoder with push button"""
    def __init__(self, clk_pin, dt_pin, sw_pin):
        super().__init__(clk_pin, dt_pin, 0, 10)
        self.sw_pin = sw_pin
        self.button_pressed = False
        
        if HARDWARE_AVAILABLE:
            self.sw_line = self.chip.get_line(sw_pin)
            self.sw_line.request(consumer='menu_button', type=LINE_REQ_DIR_IN)
    
    def read_button(self):
        """Read button press"""
        if not HARDWARE_AVAILABLE:
            return False
        
        try:
            return self.sw_line.get_value() == 0  # Active low
        except:
            return False


# ===== HARDWARE MANAGER =====

class HardwareManager:
    """Manages all hardware interfaces"""
    def __init__(self):
        self.chip = None
        self.rgb_buttons = []
        self.volume_encoders = []
        self.menu_encoder = None
        self.flashing = False
        self.bias_line = None
        self.bias_enabled = MIC_BIAS_ENABLED
        
        if HARDWARE_AVAILABLE:
            try:
                # Orange Pi 5: I2C bus 3 is typically used for GPIO header
                # Verify with: i2cdetect -l (look for i2c-3 or i2c-1)
                self.i2c_bus = smbus2.SMBus(3)  # I2C bus 3 (Orange Pi 5)
                
                # Initialize RGB LED buttons
                for addr in RGB_BUTTON_ADDRESSES:
                    try:
                        btn = RGBButton(self.i2c_bus, addr)
                        btn.set_color(0, 0, 0)  # Off initially
                        self.rgb_buttons.append(btn)
                        logging.info(f"RGB Button initialized at 0x{addr:02X}")
                    except Exception as e:
                        logging.error(f"Failed to init RGB button at 0x{addr:02X}: {e}")
                        self.rgb_buttons.append(None)
                
                # Initialize volume rotary encoders using ROTARY_ENCODER_PINS
                for clk, dt in ROTARY_ENCODER_PINS:
                    try:
                        enc = RotaryEncoder(clk, dt)
                        self.volume_encoders.append(enc)
                        logging.info(f"Volume encoder initialized on GPIO {clk}/{dt}")
                    except Exception as e:
                        logging.error(f"Failed to init encoder: {e}")
                        self.volume_encoders.append(None)
                
                # Initialize menu rotary encoder
                self.menu_encoder = MenuRotaryEncoder(MENU_ENCODER_GPIO_CLK, MENU_ENCODER_GPIO_DT, MENU_ENCODER_GPIO_SW)
                logging.info("Menu encoder initialized")
                
                # Initialize microphone bias control
                try:
                    if self.chip:
                        self.bias_line = self.chip.get_line(MIC_BIAS_GPIO)
                        self.bias_line.request(consumer='mic_bias', type=gpiod.LINE_REQ_DIR_OUT, default_vals=[1 if MIC_BIAS_ENABLED else 0])
                        self.set_mic_bias(MIC_BIAS_ENABLED)
                        logging.info(f"Mic bias control initialized: {'ON' if MIC_BIAS_ENABLED else 'OFF'} ({HEADSET_MODE} mode)")
                except Exception as e:
                    logging.error(f"Failed to init mic bias control: {e}")
                
            except Exception as e:
                logging.error(f"Hardware initialization failed: {e}")
        else:
            # Mock hardware for testing
            for i in range(4):
                self.rgb_buttons.append(None)
                self.volume_encoders.append(RotaryEncoder(0, 0))
            self.menu_encoder = MenuRotaryEncoder(0, 0, 0)
    
    def set_button_color(self, button_id, r, g, b):
        """Set RGB button color"""
        if 0 <= button_id < len(self.rgb_buttons) and self.rgb_buttons[button_id]:
            self.rgb_buttons[button_id].set_color(r, g, b)
    
    def read_button(self, button_id):
        """Read button state"""
        if 0 <= button_id < len(self.rgb_buttons) and self.rgb_buttons[button_id]:
            return self.rgb_buttons[button_id].read_button()
        return False
    
    def read_volume(self, encoder_id):
        """Read volume encoder value"""
        if 0 <= encoder_id < len(self.volume_encoders) and self.volume_encoders[encoder_id]:
            return self.volume_encoders[encoder_id].read()
        return 50.0
    
    def flash_all_buttons(self):
        """Flash all RGB buttons for identification"""
        if self.flashing:
            return
        
        self.flashing = True
        threading.Thread(target=self._flash_sequence, daemon=True).start()
    
    def _flash_sequence(self):
        """Flash sequence for visual identification"""
        for _ in range(3):
            for btn in self.rgb_buttons:
                if btn:
                    btn.set_color(255, 255, 255)
            time.sleep(0.2)
            for btn in self.rgb_buttons:
                if btn:
                    btn.set_color(0, 0, 0)
            time.sleep(0.2)
        self.flashing = False
    
    def set_mic_bias(self, enable):
        """Enable or disable microphone bias power
        
        Args:
            enable: True = bias ON (for electret mics)
                    False = bias OFF (for dynamic mics like Clear-Com CC-110/300)
        """
        if self.bias_line and HARDWARE_AVAILABLE:
            try:
                self.bias_line.set_value(1 if enable else 0)
                self.bias_enabled = enable
                logging.info(f"Mic bias: {'ENABLED' if enable else 'DISABLED'}")
            except Exception as e:
                logging.error(f"Failed to set mic bias: {e}")
    
    def get_mic_bias_state(self):
        """Get current bias state"""
        return self.bias_enabled


# ===== AUDIO MANAGER =====

class VOXGate:
    """Voice-Operated Transmit gate - HelixNet equivalent"""
    def __init__(self, threshold_db=-40, hold_time_ms=500):
        self.threshold = 10 ** (threshold_db / 20)  # Convert dB to linear
        self.hold_time = hold_time_ms / 1000.0
        self.gate_open = False
        self.last_open_time = 0
        self.enabled = False  # Toggle via config
    
    def process(self, audio_chunk, current_time):
        """Process audio through VOX gate"""
        if not self.enabled:
            return audio_chunk  # VOX disabled, pass through
        
        # Calculate RMS level
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        
        # Gate logic
        if rms > self.threshold:
            self.gate_open = True
            self.last_open_time = current_time
        elif current_time - self.last_open_time > self.hold_time:
            self.gate_open = False
        
        # Return audio if gate open, else silence
        return audio_chunk if self.gate_open else np.zeros_like(audio_chunk)


p = pyaudio.PyAudio()
class AudioManager:
    def __init__(self):
        self.input_buffer = queue.Queue(maxsize=10)
        self.output_buffer = queue.Queue(maxsize=10)
        self.stream = None
        try:
            self.stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, output=True, 
                                frames_per_buffer=CHUNK, stream_callback=self.callback)
            logging.info("Audio device initialized")
        except Exception as e:
            logging.error(f"Audio device error: {e}")
    
    def callback(self, in_data, frame_count, time_info, status):
        if status:
            logging.debug(f"Audio status: {status}")
        try:
            np_int16 = np.frombuffer(in_data, dtype=np.int16)
            self.input_buffer.put_nowait(np_int16.astype(np.float32) / 32767.0)
        except queue.Full:
            pass
        
        try:
            out_data = self.output_buffer.get_nowait()
        except queue.Empty:
            out_data = np.zeros(CHUNK, dtype=np.int16).tobytes()
        return (out_data, pyaudio.paContinue)
    
    def get_input(self):
        try:
            return self.input_buffer.get_nowait()
        except queue.Empty:
            return None
    
    def queue_output(self, data):
        np_int16 = (data * 32767).clip(-32768, 32767).astype(np.int16)
        try:
            self.output_buffer.put_nowait(np_int16.tobytes())
        except queue.Full:
            pass
    
    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()


# ===== MAIN APPLICATION =====

class BeltpackApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LanComm Pro Beltpack")
        self.setGeometry(0, 0, 480, 320)
        
        # GUI State Machine
        self.gui_state = 'boot'  # 'boot' -> 'user_select' -> 'main' -> 'settings'
        self.menu_index = 0
        self.settings_index = 0
        self.user_list = []
        self.user_list_widget = None
        self.screen_brightness = 100
        self.button_brightness = 100
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #19191c; color: #e6e6eb; }
            QLabel { color: #e6e6eb; font-size: 14pt; }
            QPushButton {
                background-color: #2d2d32; border: 1px solid #4a4a50; border-radius: 4px;
                padding: 12px; color: #e6e6eb; font-size: 12pt; font-weight: bold;
            }
            QPushButton:pressed { background-color: #5096ff; }
            QListWidget {
                background-color: #232326; border: 1px solid #3a3a3f; color: #e6e6eb;
                font-size: 14pt; padding: 8px;
            }
            QListWidget::item { padding: 12px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #5096ff; color: #ffffff; }
        """)
        
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.main_layout = QVBoxLayout()
        self.central.setLayout(self.main_layout)
        
        # Initialize hardware
        self.hardware = HardwareManager()
        self.audio = AudioManager()
        
        # Network state
        self.tcp_reader = None
        self.tcp_writer = None
        self.udp_sock = None
        self.user_id = None
        self.user_name = None
        self.channel_names = {}
        self.active_talk = set()
        self.button_modes = {}  # {slot: 'latch' or 'non-latch'}
        self.button_states = [False] * 10  # Track latch button states (increased to 10)
        self.volumes = [50.0] * MAX_NODE_CHANNELS
        self.channel_buffers = defaultdict(lambda: queue.Queue(maxsize=10))
        self.last_mic_chunk = np.zeros(CHUNK, dtype=np.float32)
        self.last_downlink_time = 0.0
        self.reconnecting = False
        self.loop = None
        self.command_queue = queue.Queue()
        self.last_heartbeat = time.time()
        self.tcp_rx_queue = None
        self.tcp_reader_task = None
        
        # VOX gates for each channel
        self.vox_gates = [VOXGate(threshold_db=-40, hold_time_ms=500) for _ in range(MAX_NODE_CHANNELS)]
        self.vox_enabled = False  # Master VOX enable/disable
        
        # Start async network thread
        self.async_thread = threading.Thread(target=self.run_async, daemon=True)
        self.async_thread.start()
        
        # Show boot screen first
        self.show_boot_screen()
        
        # Start hardware polling
        threading.Thread(target=self.hardware_poll, daemon=True).start()
        threading.Thread(target=self.menu_encoder_poll, daemon=True).start()
        
        # Initialize button LEDs
        self.update_button_leds()
        
        # Command processor timer
        self.cmd_timer = QTimer()
        self.cmd_timer.timeout.connect(self.process_commands)
        self.cmd_timer.start(100)
        
        # Audio mixer timer (runs in main thread or separate thread? Better separate)
        # Actually, let's run a mixer thread
        self.mixer_thread = threading.Thread(target=self.audio_mixer_loop, daemon=True)
        self.mixer_thread.start()
    
    def update_button_leds(self):
        """Update button LED colors based on channel assignments and talk state
        
        LED States (DFRobotics DFR0785):
        - Yellow (255, 255, 0): Channel assigned (listening)
        - Red (255, 0, 0): Active talk on this channel
        - Off (0, 0, 0): No channel assigned to this slot
        """
        try:
            # Get sorted channel list
            if not self.channel_names:
                # No profile loaded - turn all LEDs off
                for i in range(4):
                    self.hardware.set_button_color(i, 0, 0, 0)
                return
            
            sorted_channels = sorted(self.channel_names.keys())
            
            for i in range(4):
                if i < len(sorted_channels):
                    ch = sorted_channels[i]
                    if ch in self.active_talk:
                        # Red = actively talking on this channel
                        self.hardware.set_button_color(i, 255, 0, 0)
                    else:
                        # Yellow = channel assigned (listening)
                        self.hardware.set_button_color(i, 255, 255, 0)
                else:
                    # Off = no channel assigned to this slot
                    self.hardware.set_button_color(i, 0, 0, 0)
        except Exception as e:
            logging.debug(f"LED update error: {e}")

    def audio_mixer_loop(self):
        """Mix audio from all channels and push to output"""
        # Pre-allocate arrays for efficiency
        mixed_buffer = np.zeros(CHUNK, dtype=np.float32)
        
        while True:
            try:
                mixed_buffer.fill(0)  # Reset buffer (faster than creating new)
                active_sources = 0
                
                # Mix channels
                for ch, buf in list(self.channel_buffers.items()):
                    try:
                        chunk = buf.get_nowait()
                        # Find channel index for volume control
                        ch_idx = list(self.channel_names.keys()).index(ch) if ch in self.channel_names else -1
                        if ch_idx >= 0:
                            vol = self.volumes[ch_idx] / 100.0
                            mixed_buffer += chunk * vol
                            active_sources += 1
                    except (queue.Empty, ValueError):
                        pass
                
                # Add sidetone if talking
                if self.active_talk:
                    mixed_buffer += (self.last_mic_chunk * SIDETONE_LEVEL)
                    active_sources += 1
                
                if active_sources > 0:
                    np.clip(mixed_buffer, -1, 1, out=mixed_buffer)  # In-place clip
                    self.audio.queue_output(mixed_buffer)
                    self.last_downlink_time = time.time()
                
                time.sleep(0.02) # 20ms cycle
            except Exception as e:
                logging.error(f"Mixer error: {e}")
                time.sleep(0.02)

    def run_async(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.async_main())
        except Exception as e:
            logging.error(f"Async error: {e}")
        finally:
            self.loop.close()

    async def async_main(self):
        await self.connect_async()
        await asyncio.gather(
            self.receive_udp_async(), 
            self.record_send_async(),
            self.heartbeat_async(),
            return_exceptions=True
        )

    async def connect_async(self):
        while True:
            if self.reconnecting:
                await asyncio.sleep(1)
                continue
            
            try:
                # Discover server via mDNS
                discovered_host, discovered_port = await discover_server_async(timeout=10.0)
                server_host = discovered_host if discovered_host else SERVER_HOST
                server_port = discovered_port if discovered_port else TCP_PORT
                
                self.tcp_reader, self.tcp_writer = await asyncio.open_connection(server_host, server_port)
                
                # Handle authentication challenge
                import hashlib
                auth_data = await asyncio.wait_for(self.tcp_reader.read(1024), timeout=5.0)
                if auth_data.startswith(b"AUTH_CHALLENGE:"):
                    challenge = auth_data[15:]  # Remove "AUTH_CHALLENGE:" prefix
                    response = hashlib.sha256(challenge + AUTH_KEY.encode()).hexdigest().encode()
                    self.tcp_writer.write(response)
                    await self.tcp_writer.drain()
                else:
                    logging.error("No authentication challenge received")
                    await asyncio.sleep(5)
                    continue
                
                # Get user ID
                resp = await asyncio.wait_for(self.tcp_reader.read(1024), timeout=5.0)
                if resp.startswith(b"AUTH_FAIL"):
                    logging.error("Authentication failed - check AUTH_KEY")
                    await asyncio.sleep(10)
                    continue
                    
                self.user_id = int(resp.decode().split(':')[1])
                
                self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_sock.setblocking(False)
                try:
                    # Bind immediately so we advertise a real port to the server
                    self.udp_sock.bind(("0.0.0.0", 0))
                except Exception as e:
                    logging.error(f"UDP bind failed, downstream audio will break: {e}")
                
                # Add QoS for audio priority
                try:
                    self.udp_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0x88)
                    logging.info("✓ QoS enabled on beltpack")
                except Exception as e:
                    logging.debug(f"QoS setup: {e}")
                
                self.last_heartbeat = time.time()
                self.tcp_rx_queue = asyncio.Queue()
                self.tcp_reader_task = asyncio.create_task(self.tcp_reader_loop())
                # Advertise UDP port for downstream audio before first talk packet
                try:
                    udp_port = self.udp_sock.getsockname()[1]
                    self.tcp_writer.write(f"SET_UDP:{udp_port}".encode())
                    await self.tcp_writer.drain()
                except Exception as e:
                    logging.debug(f"SET_UDP failed: {e}")
                logging.info(f"Connected with user_id {self.user_id}")
                break
            except Exception as e:
                logging.error(f"Connect error: {e}")
                if self.tcp_writer:
                    try:
                        self.tcp_writer.close()
                        await self.tcp_writer.wait_closed()
                    except:
                        pass
                await asyncio.sleep(5)
    
    async def tcp_reader_loop(self):
        """Single consumer of TCP stream; dispatches flash and enqueues responses"""
        if not self.tcp_reader:
            return
        try:
            while True:
                data = await self.tcp_reader.read(1024)
                if not data:
                    raise ConnectionResetError("TCP stream closed")
                if data == b"FLASH_PACK":
                    logging.info("Received flash command from server")
                    self.hardware.flash_all_buttons()
                    continue
                if data == b"PONG":
                    self.last_heartbeat = time.time()
                    continue
                if data.startswith(b"UPDATE_CONFIG:"):
                    # Live config update from server
                    try:
                        config_str = data.decode().split(':', 1)[1]
                        config_data = json.loads(config_str)
                        
                        # Update local config
                        if isinstance(config_data, dict) and 'channels' in config_data:
                            raw_channels = config_data['channels']
                            self.button_modes = config_data.get('button_modes', {})
                        else:
                            raw_channels = config_data
                            self.button_modes = {}
                        
                        self.channel_names = {int(k): v for k, v in raw_channels.items()}
                        
                        logging.info(f"Config updated from server: {len(self.channel_names)} channels")
                        self.update_button_leds()  # Update LED colors for new config
                        self.command_queue.put(('show_main_gui', None))  # Refresh GUI
                    except Exception as e:
                        logging.error(f"Failed to parse UPDATE_CONFIG: {e}")
                    continue
                if self.tcp_rx_queue:
                    await self.tcp_rx_queue.put(data)
        except Exception as e:
            logging.debug(f"TCP reader loop ended: {e}")
            await self.reconnect_async()

    async def wait_for_prefix(self, prefix, timeout: float = 5.0):
        """Wait for next TCP message with any of the given prefix/prefixes"""
        prefixes = tuple(prefix) if isinstance(prefix, (list, tuple, set)) else (prefix,)
        if not self.tcp_rx_queue:
            raise ConnectionError("TCP queue not ready")
        try:
            while True:
                data = await asyncio.wait_for(self.tcp_rx_queue.get(), timeout=timeout)
                if any(data.startswith(p) for p in prefixes):
                    return data
                # Ignore unrelated messages (already handled flash/pong in reader)
        except Exception as e:
            raise e

    def show_boot_screen(self):
        """Show boot/startup screen"""
        self.gui_state = 'boot'
        self.clear_layout()
        
        boot_label = QLabel("Booting...")
        boot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        boot_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #5096ff;")
        self.main_layout.addWidget(boot_label)
        
        status_label = QLabel("Connecting to server...")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("font-size: 12pt; color: #a0a0a5;")
        self.main_layout.addWidget(status_label)
        
        # Wait for network connection, then show user select
        QTimer.singleShot(2000, self.show_user_select)
    
    def show_user_select(self):
        """Show user profile selection with rotary encoder navigation"""
        self.gui_state = 'user_select'
        self.menu_index = 0
        self.clear_layout()
        
        title = QLabel("Select User Profile")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #5096ff; padding: 10px;")
        self.main_layout.addWidget(title)
        
        # Queue command for async thread
        self.command_queue.put(('get_users', None))

    async def get_users_async(self):
        if not self.tcp_writer:
            await self.reconnect_async()
            return
        try:
            self.tcp_writer.write(b"GET_USERS")
            await self.tcp_writer.drain()
            resp = await self.wait_for_prefix(b"USERS:", timeout=5.0)
            if resp.decode().startswith("USERS:"):
                user_list = resp.decode().split(':')[1].split(',')
                # Update GUI from main thread
                self.command_queue.put(('update_user_list', user_list))
        except Exception as e:
            logging.error(f"Get users error: {e}")
            await self.reconnect_async()

    async def select_user_async(self):
        if not self.user_name or not self.tcp_writer:
            return
        try:
            self.tcp_writer.write(f"SELECT_USER:{self.user_name}".encode())
            await self.tcp_writer.drain()
            resp = await self.wait_for_prefix([b"CONFIG:", b"ERROR"], timeout=5.0)
            if resp.startswith(b"ERROR"):
                logging.error("User selection failed: ERROR")
                self.command_queue.put(('show_error', 'User unavailable'))
                return
            
            config_str = resp.decode().split(':', 1)[1]
            # Parse config - server sends {channels: {...}, button_modes: {...}}
            config_data = json.loads(config_str)
            
            # Handle both old format (just channels) and new format (with button_modes)
            if isinstance(config_data, dict) and 'channels' in config_data:
                raw_channels = config_data['channels']
                self.button_modes = config_data.get('button_modes', {})
            else:
                # Backwards compatibility: old server sends just channel dict
                raw_channels = config_data
                self.button_modes = {}
            
            self.channel_names = {int(k): v for k, v in raw_channels.items()}
            self.update_button_leds()
            self.command_queue.put(('show_main_gui', None))
        except Exception as e:
            logging.error(f"Select user error: {e}")
            await self.reconnect_async()
    
    def show_main_gui(self):
        """Show main GUI with channel status and settings gear"""
        self.gui_state = 'main'
        self.menu_index = 0
        self.clear_layout()
        
        # Header with user name and settings gear
        header_layout = QHBoxLayout()
        
        # User name label (selectable - returns to profile selection)
        self.user_name_label = QLabel(self.user_name)
        self.user_name_label.setStyleSheet("font-size: 10pt; color: #a0a0a5; padding: 5px; border-radius: 3px;")
        header_layout.addWidget(self.user_name_label)
        
        header_layout.addStretch()
        
        # Settings gear icon (selectable)
        self.settings_icon = QLabel("⚙")
        self.settings_icon.setStyleSheet("font-size: 18pt; color: #5096ff; padding: 5px; border-radius: 3px;")
        self.settings_icon.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(self.settings_icon)
        
        self.main_layout.addLayout(header_layout)
        
        # Channel status displays with volume indicators
        self.channel_widgets = []
        for i, (ch, name) in enumerate(sorted(self.channel_names.items())):
            ch_frame = QWidget()
            ch_frame.setStyleSheet("background-color: #232326; border-radius: 4px; padding: 8px; margin: 4px;")
            ch_layout = QHBoxLayout(ch_frame)
            ch_layout.setContentsMargins(8, 8, 8, 8)
            
            status_label = QLabel(f"CH{i+1}: {name}")
            status_label.setStyleSheet("font-size: 12pt; color: #e6e6eb;")
            ch_layout.addWidget(status_label)
            
            ch_layout.addStretch()
            
            # Volume meter
            vol_bar = QProgressBar()
            vol_bar.setOrientation(Qt.Orientation.Horizontal)
            vol_bar.setMinimum(0)
            vol_bar.setMaximum(100)
            vol_bar.setValue(int(self.volumes[i]))
            vol_bar.setMaximumWidth(120)
            vol_bar.setMaximumHeight(20)
            vol_bar.setTextVisible(True)
            vol_bar.setFormat("%v%")
            vol_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #1a1a1d; border: 1px solid #3d3d42; border-radius: 3px;
                    text-align: center; color: #5096ff; font-weight: bold;
                }
                QProgressBar::chunk { background-color: #5096ff; border-radius: 2px; }
            """)
            ch_layout.addWidget(vol_bar)
            
            self.channel_widgets.append((ch_frame, vol_bar))
            self.main_layout.addWidget(ch_frame)
        
        self.main_layout.addStretch()
        
        # Microphone level meter at bottom
        mic_label = QLabel("MIC LEVEL")
        mic_label.setStyleSheet("font-size: 9pt; color: #a0a0a5; padding: 2px;")
        mic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(mic_label)
        
        self.mic_meter = QProgressBar()
        self.mic_meter.setOrientation(Qt.Orientation.Horizontal)
        self.mic_meter.setMinimum(0)
        self.mic_meter.setMaximum(100)
        self.mic_meter.setValue(0)
        self.mic_meter.setMaximumHeight(15)
        self.mic_meter.setTextVisible(False)
        self.mic_meter.setStyleSheet("""
            QProgressBar {
                background-color: #1a1a1d; border: 1px solid #3d3d42; border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2a2, stop:0.7 #2a2, 
                    stop:0.7 #da2, stop:0.85 #da2,
                    stop:0.85 #d22, stop:1 #d22);
                border-radius: 2px;
            }
        """)
        self.main_layout.addWidget(self.mic_meter)
        
        # Hint text
        hint = QLabel("Rotate to navigate • Press User to change profile • Press ⚙ for settings")
        hint.setStyleSheet("color: #a0a0a5; font-size: 9pt; padding: 5px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(hint)
    
    def show_settings_menu(self):
        """Show settings menu with bias, brightness controls"""
        self.gui_state = 'settings'
        self.settings_index = 0
        self.clear_layout()
        
        # Header
        header = QLabel("⚙ Settings")
        header.setStyleSheet("font-size: 18pt; font-weight: bold; color: #5096ff; padding: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(header)
        
        # Settings options
        self.settings_widgets = []
        
        # 1. Mic Bias
        bias_frame = QWidget()
        bias_frame.setStyleSheet("background-color: #232326; border-radius: 4px; padding: 12px; margin: 4px;")
        bias_layout = QHBoxLayout(bias_frame)
        
        bias_label = QLabel("Mic Bias")
        bias_label.setStyleSheet("font-size: 12pt; color: #e6e6eb;")
        bias_layout.addWidget(bias_label)
        bias_layout.addStretch()
        
        self.bias_status_label = QLabel("ON" if self.hardware.get_mic_bias_state() else "OFF")
        self.bias_status_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #2a2;" if self.hardware.get_mic_bias_state() else "font-size: 12pt; font-weight: bold; color: #d22;")
        bias_layout.addWidget(self.bias_status_label)
        
        self.settings_widgets.append(('bias', bias_frame))
        self.main_layout.addWidget(bias_frame)
        
        # 2. Screen Brightness
        screen_frame = QWidget()
        screen_frame.setStyleSheet("background-color: #232326; border-radius: 4px; padding: 12px; margin: 4px;")
        screen_layout = QHBoxLayout(screen_frame)
        
        screen_label = QLabel("Screen Brightness")
        screen_label.setStyleSheet("font-size: 12pt; color: #e6e6eb;")
        screen_layout.addWidget(screen_label)
        screen_layout.addStretch()
        
        self.screen_brightness_label = QLabel(f"{self.screen_brightness}%")
        self.screen_brightness_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #5096ff;")
        screen_layout.addWidget(self.screen_brightness_label)
        
        self.settings_widgets.append(('screen_brightness', screen_frame))
        self.main_layout.addWidget(screen_frame)
        
        # 3. Button Brightness
        button_frame = QWidget()
        button_frame.setStyleSheet("background-color: #232326; border-radius: 4px; padding: 12px; margin: 4px;")
        button_layout = QHBoxLayout(button_frame)
        
        button_label = QLabel("Button Brightness")
        button_label.setStyleSheet("font-size: 12pt; color: #e6e6eb;")
        button_layout.addWidget(button_label)
        button_layout.addStretch()
        
        self.button_brightness_label = QLabel(f"{self.button_brightness}%")
        self.button_brightness_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #5096ff;")
        button_layout.addWidget(self.button_brightness_label)
        
        self.settings_widgets.append(('button_brightness', button_frame))
        self.main_layout.addWidget(button_frame)
        
        self.main_layout.addStretch()
        
        # Highlight first option
        self.update_settings_highlight()
        
        # Back hint
        hint = QLabel("Rotate to navigate • Press to select • Press ⚙ to exit")
        hint.setStyleSheet("color: #a0a0a5; font-size: 9pt; padding: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(hint)
    
    def toggle_talk(self, ch, enable):
        """Toggle talk state for channel"""
        if enable:
            self.active_talk.add(ch)
        else:
            self.active_talk.discard(ch)
        
        self.command_queue.put(('send_toggle', (ch, enable)))

    async def send_toggle(self, ch, checked):
        if not self.tcp_writer:
            await self.reconnect_async()
            return
        try:
            self.tcp_writer.write(f"TOGGLE_TALK:{ch}:{'1' if checked else '0'}".encode())
            await self.tcp_writer.drain()
        except Exception as e:
            logging.error(f"Send toggle error: {e}")
            await self.reconnect_async()

    async def reconnect_async(self):
        if self.reconnecting:
            return
        self.reconnecting = True
        logging.info("Reconnecting...")


        if self.tcp_writer:
            try:
                self.tcp_writer.close()
                await self.tcp_writer.wait_closed()
            except:
                pass
        
        self.tcp_reader = None
        self.tcp_writer = None
        await asyncio.sleep(2)
        self.reconnecting = False
        await self.connect_async()
    
    async def heartbeat_async(self):
        """Send periodic heartbeat to server"""
        while True:
            await asyncio.sleep(10)
            gap = time.time() - self.last_heartbeat
            if gap > 30:
                await self.reconnect_async()
                continue
            if self.tcp_writer and gap > 10:
                try:
                    self.tcp_writer.write(b"PING")
                    await self.tcp_writer.drain()
                    # last_heartbeat updated on PONG
                except:
                    await self.reconnect_async()
    
    # ===== HARDWARE POLLING =====
    
    def hardware_poll(self):
        """Poll hardware buttons and encoders"""
        last_button_states = [False] * 4
        
        while True:
            try:
                # Read RGB buttons
                for i in range(min(4, len(self.channel_names))):
                    button_pressed = self.hardware.read_button(i)
                    
                    # Detect button press (edge trigger)
                    if button_pressed and not last_button_states[i]:
                        ch = sorted(self.channel_names.keys())[i]
                        mode = self.button_modes.get(str(i), 'latch')
                        
                        if mode == 'latch':
                            # Toggle mode
                            self.button_states[i] = not self.button_states[i]
                            self.toggle_talk(ch, self.button_states[i])
                        else:
                            # Push-to-talk mode - enable on press
                            self.toggle_talk(ch, True)
                    
                    # Non-latch mode - disable on release
                    elif not button_pressed and last_button_states[i]:
                        ch = sorted(self.channel_names.keys())[i]
                        mode = self.button_modes.get(str(i), 'latch')
                        if mode == 'non-latch':
                            self.toggle_talk(ch, False)
                    
                    last_button_states[i] = button_pressed
                
                # Read volume encoders and update volumes
                for i in range(min(len(self.channel_names), len(self.hardware.volume_encoders))):
                    vol = self.hardware.read_volume(i)
                    if abs(vol - self.volumes[i]) > 1.0:  # Debounce small changes
                        self.volumes[i] = vol
                        # Update GUI volume bar if in main screen
                        if self.gui_state == 'main' and i < len(self.channel_widgets):
                            _, vol_bar = self.channel_widgets[i]
                            vol_bar.setValue(int(vol))
                
                time.sleep(0.05)  # 20Hz polling
            except Exception as e:
                logging.error(f"Hardware poll error: {e}")
                time.sleep(0.1)
    
    def menu_encoder_poll(self):
        """Poll menu rotary encoder for navigation"""
        last_button_state = False
        last_value = 0
        
        while True:
            try:
                if not self.hardware.menu_encoder:
                    time.sleep(0.1)
                    continue
                
                # Read rotation
                current_value = self.hardware.menu_encoder.read()
                if current_value != last_value:
                    delta = current_value - last_value
                    last_value = current_value
                    
                    if self.gui_state == 'user_select':
                        self.menu_index = (self.menu_index + (1 if delta > 0 else -1)) % max(1, len(self.user_list))
                        if self.user_list_widget:
                            self.user_list_widget.setCurrentRow(self.menu_index)
                    
                    elif self.gui_state == 'main':
                        # Rotate through: User name, Channels..., Settings gear
                        max_items = 1 + len(self.channel_names) + 1  # User name + channels + settings gear
                        self.menu_index = (self.menu_index + (1 if delta > 0 else -1)) % max_items
                        self.update_main_highlight()
                    
                    elif self.gui_state == 'settings':
                        self.settings_index = (self.settings_index + (1 if delta > 0 else -1)) % len(self.settings_widgets)
                        self.update_settings_highlight()
                
                # Read button press
                button_pressed = self.hardware.menu_encoder.read_button()
                if button_pressed and not last_button_state:
                    self.on_menu_button_press()
                
                last_button_state = button_pressed
                time.sleep(0.01)
            except Exception as e:
                logging.error(f"Menu encoder poll error: {e}")
                time.sleep(0.1)
    
    def on_menu_button_press(self):
        """Handle menu button press based on current state"""
        if self.gui_state == 'user_select':
            # Select user
            if len(self.user_list) > 0:
                self.user_name = self.user_list[self.menu_index]
                if self.loop:
                    asyncio.run_coroutine_threadsafe(self.select_user_async(), self.loop)
        
        elif self.gui_state == 'main':
            # Check what's selected: 0=user name, 1..N=channels, N+1=settings gear
            if self.menu_index == 0:
                # User name selected - return to profile selection
                self.command_queue.put(('show_user_select', None))
            elif self.menu_index == len(self.channel_names) + 1:
                # Settings gear selected
                self.command_queue.put(('show_settings', None))
        
        elif self.gui_state == 'settings':
            # Toggle/adjust selected setting
            setting_type, _ = self.settings_widgets[self.settings_index]
            
            if setting_type == 'bias':
                current_state = self.hardware.get_mic_bias_state()
                self.hardware.set_mic_bias(not current_state)
                self.bias_status_label.setText("ON" if not current_state else "OFF")
                self.bias_status_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #2a2;" if not current_state else "font-size: 12pt; font-weight: bold; color: #d22;")
                logging.info(f"Bias toggled: {'ON' if not current_state else 'OFF'}")
            
            elif setting_type == 'screen_brightness':
                # Cycle through brightness levels
                self.screen_brightness = (self.screen_brightness + 25) % 125
                if self.screen_brightness == 0:
                    self.screen_brightness = 25
                self.screen_brightness_label.setText(f"{self.screen_brightness}%")
                # TODO: Apply brightness to display
                logging.info(f"Screen brightness: {self.screen_brightness}%")
            
            elif setting_type == 'button_brightness':
                # Cycle through brightness levels
                self.button_brightness = (self.button_brightness + 25) % 125
                if self.button_brightness == 0:
                    self.button_brightness = 25
                self.button_brightness_label.setText(f"{self.button_brightness}%")
                self.apply_button_brightness()
                logging.info(f"Button brightness: {self.button_brightness}%")
    
    def update_main_highlight(self):
        """Update visual highlight on main screen"""
        if not hasattr(self, 'channel_widgets'):
            return
        
        # Remove all highlights
        if hasattr(self, 'user_name_label'):
            self.user_name_label.setStyleSheet("font-size: 10pt; color: #a0a0a5; padding: 5px; border-radius: 3px;")
        
        for i, (frame, _) in enumerate(self.channel_widgets):
            frame.setStyleSheet("background-color: #232326; border-radius: 4px; padding: 8px; margin: 4px;")
        
        if hasattr(self, 'settings_icon'):
            self.settings_icon.setStyleSheet("font-size: 18pt; color: #5096ff; padding: 5px; border-radius: 3px;")
        
        # Add highlight to selected item
        # Index 0 = user name, 1..N = channels, N+1 = settings gear
        if self.menu_index == 0:
            # User name selected
            if hasattr(self, 'user_name_label'):
                self.user_name_label.setStyleSheet("font-size: 10pt; color: #fff; background-color: #5096ff; padding: 5px; border-radius: 3px;")
        elif self.menu_index <= len(self.channel_widgets):
            # Channel selected (subtract 1 for user name offset)
            frame, _ = self.channel_widgets[self.menu_index - 1]
            frame.setStyleSheet("background-color: #2d2d32; border: 2px solid #5096ff; border-radius: 4px; padding: 8px; margin: 4px;")
        else:
            # Settings gear selected
            if hasattr(self, 'settings_icon'):
                self.settings_icon.setStyleSheet("font-size: 18pt; color: #fff; background-color: #5096ff; border-radius: 4px; padding: 5px;")
    
    def update_settings_highlight(self):
        """Update visual highlight in settings menu"""
        if not hasattr(self, 'settings_widgets'):
            return
        
        for i, (_, frame) in enumerate(self.settings_widgets):
            if i == self.settings_index:
                frame.setStyleSheet("background-color: #2d2d32; border: 2px solid #5096ff; border-radius: 4px; padding: 12px; margin: 4px;")
            else:
                frame.setStyleSheet("background-color: #232326; border-radius: 4px; padding: 12px; margin: 4px;")
    
    def apply_button_brightness(self):
        """Apply brightness to RGB LED buttons"""
        scale = self.button_brightness / 100.0
        for i in range(4):
            if i < len(sorted(self.channel_names.keys())):
                ch = sorted(self.channel_names.keys())[i]
                if ch in self.active_talk:
                    # Red scaled
                    self.hardware.set_button_color(i, int(255 * scale), 0, 0)
                else:
                    # Yellow scaled
                    self.hardware.set_button_color(i, int(255 * scale), int(255 * scale), 0)
                time.sleep(0.05)  # Brief recovery delay
    
    # ===== GUI FUNCTIONS =====
    
    def process_commands(self):
        """Process commands from async thread"""
        try:
            while True:
                cmd, data = self.command_queue.get_nowait()
                
                if cmd == 'get_users':
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(self.get_users_async(), self.loop)
                
                elif cmd == 'update_user_list':
                    # Persist list for rotary navigation and selection
                    self.user_list = data or []
                    self.user_list_widget = QListWidget()
                    self.user_list_widget.setStyleSheet("font-size: 16pt; padding: 8px;")
                    for user in self.user_list:
                        item = QListWidgetItem(user)
                        self.user_list_widget.addItem(item)
                    if self.user_list:
                        self.user_list_widget.setCurrentRow(self.menu_index % len(self.user_list))
                    self.user_list_widget.itemClicked.connect(self.on_user_selected)
                    self.main_layout.addWidget(self.user_list_widget)
                
                elif cmd == 'show_main_gui':
                    self.show_main_gui()
                
                elif cmd == 'show_settings':
                    self.show_settings_menu()
                
                elif cmd == 'show_user_select':
                    self.show_user_select()
                
                elif cmd == 'show_error':
                    error_label = QLabel(f"Error: {data}")
                    error_label.setStyleSheet("color: #ff5555; font-size: 12pt; padding: 10px;")
                    self.main_layout.addWidget(error_label)
                
                elif cmd == 'send_toggle':
                    ch, enable = data
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(self.send_toggle(ch, enable), self.loop)
        except queue.Empty:
            pass
    
    def on_user_selected(self, item):
        """Handle user selection from list"""
        self.user_name = item.text()
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.select_user_async(), self.loop)
    
    async def record_send_async(self):
        seq = 0
        while True:
            try:
                audio_np = self.audio.get_input()
                if audio_np is None:
                    await asyncio.sleep(0.001)
                    continue
                
                current_time = time.time()
                
                # Apply VOX gating if enabled
                if self.vox_enabled:
                    audio_np = self.vox_gates[0].process(audio_np, current_time)
                
                self.last_mic_chunk = audio_np
                
                if not self.active_talk:
                    await asyncio.sleep(0.001)
                    continue

                # Encode as raw PCM int16 (no container)
                pcm_data = (audio_np * 32767).clip(-32768, 32767).astype(np.int16).tobytes()
                
                if self.user_id is None or self.udp_sock is None:
                    await asyncio.sleep(0.001)
                    continue

                for ch in list(self.active_talk):
                    header = ch.to_bytes(4, 'big') + self.user_id.to_bytes(4, 'big') + seq.to_bytes(4, 'big')
                    try:
                        # Send to server (use cached address from connection)
                        server_addr = self.tcp_writer.get_extra_info('peername')[0] if self.tcp_writer else SERVER_HOST
                        await asyncio.get_running_loop().sock_sendto(self.udp_sock, header + pcm_data, (server_addr, UDP_PORT))
                    except Exception as e:
                        logging.debug(f"Send error ch{ch}: {e}")
                
                seq = (seq + 1) % 65536
            except Exception as e:
                logging.error(f"Record/send error: {e}")
                await asyncio.sleep(0.01)

    async def receive_udp_async(self):
        loop = asyncio.get_running_loop()
        if self.udp_sock is None:
            return
        while True:
            try:
                data, _ = await loop.sock_recvfrom(self.udp_sock, 8192)
                if len(data) < 12:
                    continue
                
                # Server sends: [ch:4][zeros:8][WAV_data]
                ch = int.from_bytes(data[0:4], 'big')
                if ch not in self.channel_names:
                    continue
                
                # Skip 8 zero bytes (user_id and seq placeholders from server)
                encoded = data[12:]
                if len(encoded) < 10:
                    continue
                
                try:
                    # Decode raw PCM int16 directly
                    audio_data = np.frombuffer(encoded, dtype=np.int16).astype(np.float32) / 32767.0
                except Exception as e:
                    logging.error(f"PCM decode error: {e}")
                    continue
                
                if len(audio_data) < CHUNK:
                    audio_data = np.pad(audio_data, (0, CHUNK - len(audio_data)))
                elif len(audio_data) > CHUNK:
                    audio_data = audio_data[:CHUNK]
                
                # Push to channel buffer for mixer thread
                try:
                    self.channel_buffers[ch].put_nowait(audio_data)
                except queue.Full:
                    pass # Drop packet if buffer full (jitter buffer overflow)
                
            except Exception as e:
                logging.error(f"UDP receive error: {e}")
                await asyncio.sleep(0.01)
    
    def clear_layout(self):
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            w = child.widget() if child else None
            if w:
                w.deleteLater()
    
    def closeEvent(self, event):
        """Clean shutdown"""
        logging.info("Shutting down beltpack...")
        self.audio.close()
        if self.tcp_writer:
            try:
                self.tcp_writer.close()
            except:
                pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BeltpackApp()
    window.showFullScreen()
    sys.exit(app.exec())
