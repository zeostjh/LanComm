<div align="center">

# 🎙️ LanComm

### Professional IP-Based Intercom System

*Commercial-grade communication at 1/10th the cost*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/zeostjh/LanComm)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

[Features](#-key-features) • [Quick Start](#-quick-start) • [Hardware](#-hardware-bill-of-materials) • [Documentation](#-documentation) • [Contributing](CONTRIBUTING.md)

---

### Broadcast-quality intercom for live events, studios, and industrial environments

Built for professionals who need reliable communication without the commercial price tag. Inspired by Clear-Com HelixNet and RTS ADAM systems.

</div>

## ✨ Why LanComm?

<table>
<tr>
<td width="50%">

### 💰 Cost Effective
**$210/beltpack** vs $1,000+ commercial  
75-80% cost savings  
Perfect for budget-conscious productions

### ⚡ Low Latency
**<50ms end-to-end**  
Broadcast-grade performance  
Raw PCM audio (48kHz/16-bit)

### 🎯 Professional Grade
Authentication & encryption  
QoS network priority  
mDNS auto-discovery

</td>
<td width="50%">

### 🔧 Open Source
Fully customizable  
MIT License  
Extend and modify freely

### 🌐 Scalable
20 simultaneous users  
10 independent channels  
PoE-powered deployment

### 🎨 Modern Interface
PyQt6 GUI with real-time meters  
4-wire external system bridges  
RGB LED visual feedback

</td>
</tr>
</table>

---

## 🎯 Key Features

### Audio Performance
```
🎵 48kHz 16-bit PCM          Professional uncompressed audio
⚡ <50ms latency              Faster than most commercial systems  
🔊 Full-duplex               Talk and listen simultaneously
🎚️ Null routing              Never hear your own voice delayed
📊 Jitter buffer (128ms)     Network resilience
🎤 VOX gating                 Optional voice-activation
```

### System Capacity
```
👥 20 users                   Simultaneous connections
📻 10 channels                Independent communication paths  
🎛️ 4 buttons per beltpack    Hardware controls
🌐 QoS-aware                  DSCP AF41 traffic priority
```

### Hardware Features
```
⚡ PoE powered                Single cable deployment
🎵 ES8388 codec               Built-in professional audio
💡 RGB LED buttons            Yellow=listen, Red=talk
🎚️ Rotary encoders           Per-channel volume control
📱 3.4" OLED touchscreen     800×800 square display
🎧 4-pin XLR compatible       Broadcast headsets
```

### Professional Tools
```
🖥️ PyQt6 GUI                  Channel mixer with live meters
🔌 4-wire interfaces (2x)     Connect external systems
👤 User profiles              Save channel assignments
🔐 SHA-256 authentication     Secure access control
🔍 mDNS discovery             Zero-config networking
💡 Flash identification       Find specific beltpacks
```

---

## 🎬 Perfect For

| Industry | Use Cases |
|----------|----------|
| **🎭 Live Events** | Concerts, theater, conferences, festivals |
| **📺 Broadcasting** | TV studios, radio production, streaming |
| **🏭 Industrial** | Construction sites, manufacturing floors |
| **🎓 Education** | School theaters, auditoriums, A/V teams |
| **⛪ Houses of Worship** | Churches, synagogues, mosques |
| **🏟️ Sports** | Stadium operations, broadcast coordination |

---

## 🏗️ System Architecture

### Overview

```
                    ┌─────────────────────────────┐
                    │      SERVER PC/Mac/Linux     │
                    │   ┌─────────────────────┐   │
                    │   │  PyQt6 GUI          │   │
                    │   │  • Channel Mixer    │   │
                    │   │  • User Management  │   │
                    │   │  • 4-Wire Bridges   │   │
                    │   └─────────────────────┘   │
                    │                              │
                    │   ┌──────────┬──────────┐   │
                    │   │ TCP:6001 │ UDP:6001 │   │
                    │   │ Control  │  Audio   │   │
                    │   └──────────┴──────────┘   │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │  Gigabit PoE+ Switch        │
                    │  (QoS/DSCP Priority)        │
                    └──┬───────┬───────┬──────────┘
                       │       │       │
           ┌───────────┴─┐  ┌──┴────────┐  ┌────────────┐
           │ Beltpack 1  │  │Beltpack 2 │  │ Beltpack N │
           │┌───────────┐│  │┌─────────┐│  │┌──────────┐│
           ││Orange Pi  ││  ││Orange Pi││  ││Orange Pi ││
           ││5 Pro 16GB ││  ││5 Pro 16G││  ││5 Pro 16GB││
           ││┌─────────┐││  ││┌───────┐││  ││┌────────┐││
           │││ES8388   │││  │││ES8388 │││  │││ES8388  │││
           │││Audio    │││  │││Audio  │││  │││Audio   │││
           ││└─────────┘││  ││└───────┘││  ││└────────┘││
           ││           ││  ││         ││  ││          ││
           ││ [🔴][🔴]  ││  ││ [🟢][🟢]││  ││ [🟡][🟡] ││
           ││ [🔴][🔴]  ││  ││ [🟢][🟢]││  ││ [🟡][🟡] ││
           ││           ││  ││         ││  ││          ││
           ││ 🎚️ 🎚️ 🎚️ ││  ││ 🎚️ 🎚️ 🎚️││  ││ 🎚️ 🎚️ 🎚️ ││
           │└───────────┘│  │└─────────┘│  │└──────────┘│
           └─────────────┘  └───────────┘  └────────────┘
              PoE Power        PoE Power      PoE Power
```

### Audio Flow Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         BELTPACK                                │
│  ┌──────┐  ┌────────┐  ┌─────────┐  ┌────────┐               │
│  │ Mic  ├─►│ ES8388 ├─►│ PyAudio ├─►│ Encode ├─┐             │
│  └──────┘  └────────┘  └─────────┘  └────────┘ │             │
│                                                  │             │
│                                                  ▼             │
│                                           ┌──────────┐         │
│                                           │   UDP    │         │
│                                           │ Uplink   │         │
│                                           └────┬─────┘         │
└────────────────────────────────────────────────┼───────────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                          SERVER                                 │
│  ┌──────────┐  ┌─────────┐  ┌────────────┐  ┌──────────────┐  │
│  │  Jitter  ├─►│  Mixer  ├─►│ Null Route ├─►│ Custom Mixes │  │
│  │  Buffer  │  │(Sum all)│  │(Exclude own│  │(Per listener)│  │
│  │ (128ms)  │  │         │  │   audio)   │  │              │  │
│  └──────────┘  └─────────┘  └────────────┘  └──────┬───────┘  │
│                                                     │          │
│                                                     ▼          │
│                                               ┌──────────┐     │
│                                               │   UDP    │     │
│                                               │Downlinks │     │
│                                               └────┬─────┘     │
└────────────────────────────────────────────────────┼───────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BELTPACK                                │
│  ┌────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐  ┌───────┐ │
│  │  UDP   ├─►│ Decode  ├─►│  Apply  ├─►│  Mix   ├─►│ES8388 │ │
│  │ Receive│  │         │  │ Volume  │  │Channels│  │Output │ │
│  └────────┘  └─────────┘  └─────────┘  └───┬────┘  └───────┘ │
│                                             │                  │
│  ┌────────┐                                 │                  │
│  │Sidetone│─────────────────────────────────┘                  │
│  │  (18%) │  (Direct mic monitoring)                           │
│  └────────┘                                                    │
└─────────────────────────────────────────────────────────────────┘

Key Innovation: Null Routing
────────────────────────────
You never hear your own voice with network delay - only local sidetone!
```

### Network Protocol

#### 🔐 Authentication (TCP Port 6001)

```
     Beltpack                        Server
        │                               │
        ├──── CONNECT ─────────────────►│
        │◄─── AUTH_CHALLENGE ───────────┤  (random nonce)
        ├──── SHA256(nonce+key) ───────►│  
        │◄─── USER_ID:123 ──────────────┤  ✓ Authenticated
        │──── SET_UDP:50123 ────────────►│
        │◄─── UDP_OK ────────────────────┤
        │                               │
```

#### 📡 Commands (TCP)

| Command | Description | Response |
|---------|-------------|----------|
| `GET_USERS` | Request user list | `USERS:Bob,Alice,Charlie` |
| `SELECT_USER:` | Select profile | `CONFIG:{channels, modes}` |
| `TOGGLE_TALK:2:1` | Enable talk on CH2 | (none) |
| `SET_UDP:50123` | Advertise UDP port | `UDP_OK` |
| `PING` | Heartbeat (every 10s) | `PONG` |
| `FLASH_PACK` | Flash LEDs | (none) |

#### 🎵 Audio Packets (UDP Port 6001)

**Uplink Format** (Beltpack → Server):
```
┌─────────┬─────────┬──────────┬────────────────────┐
│Channel  │User ID  │Sequence  │PCM Audio Data      │
│(4 bytes)│(4 bytes)│(4 bytes) │(1920 bytes)        │
│         │         │          │960 samples @ 16-bit│
└─────────┴─────────┴──────────┴────────────────────┘
         12-byte header        20ms audio frame
```

**Downlink Format** (Server → Beltpack):
```
┌─────────┬──────────────────┬──────────────────────┐
│Channel  │Reserved (zeros)  │Mixed PCM Audio       │
│(4 bytes)│(8 bytes)         │(1920 bytes)          │
│         │                  │Null-routed for talker│
└─────────┴──────────────────┴──────────────────────┘
```

**Quality of Service**:  
🚀 DSCP AF41 (0x88) marking for traffic prioritization on managed switches

---

## 📦 Hardware Parts List

### Server Components (PC/Mac/Linux)

**Minimum Requirements**:
- CPU: Dual-core 2GHz+ (quad-core recommended for 10+ nodes)
- RAM: 4GB (8GB recommended)
- Network: Gigabit Ethernet (10Gb recommended for large deployments)
- OS: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)

**Software Dependencies**:
- Python 3.8+ (3.13+ recommended for best performance)
- PyQt6, numpy, pyaudio
- zeroconf, netifaces (for mDNS server discovery)
- smbus2 (for I2C RGB buttons)
- gpiod (for GPIO encoders, Linux only)

### Beltpack Components (per unit)

**Platform**: Orange Pi 5 Pro (16GB) + Waveshare PoE HAT + **Built-in ES8388 Audio**

#### Core Components
| Qty | Part | Description | Est. Cost | Source |
|-----|------|-------------|-----------|--------|
| 1 | SBC | Orange Pi 5 Pro (16GB) w/ built-in ES8388 audio | $110 | Orange Pi, AliExpress |
| 1 | PoE HAT | Waveshare PoE HAT (802.3af/at, 25.5W) | $22 | Waveshare, Amazon |
| 4 | RGB Button | Gravity I2C RGB LED Button (DFRobot SEN0302) | $8 ea | DFRobot |
| 4 | Rotary Encoder | EC11 Rotary Encoder (20 detents, 6mm shaft) | $2 ea | Amazon |
| 1 | Menu Encoder | EC11 with Push Button | $3 | Amazon |
| 5 | Knob | Aluminum knob 6mm shaft | $1 ea | Amazon |
| 1 | Enclosure | ABS/Aluminum case (~150x100x50mm) | $15 | Amazon |
| 1 | MicroSD Card | 32GB Class 10 (for OS) | $10 | Amazon |
| 1 | Display (opt.) | 3.4" MIPI DSI OLED (800×800 square, capacitive touch) | $35 | Waveshare |
| | **Total per Beltpack** | | **~$210** (add $35 for display) | |

*Why Orange Pi 5 Pro? 8-core CPU (4×A76 + 4×A55) @ 2.4GHz, 16GB RAM, 2.5Gb Ethernet, **built-in professional audio codec (no HAT needed!)**, PCIe expansion. See [docs/HARDWARE_RECOMMENDATIONS.md](docs/HARDWARE_RECOMMENDATIONS.md) for detailed comparison.

#### Optional Components
| Qty | Part | Description | Est. Cost |
|-----|------|-------------|-----------|
| 1 | Screen | 3.4" Waveshare MIPI DSI OLED (800×800, see recommendations below) | $35 |
| 1 | Belt Clip | Heavy duty spring clip | $5 |
| 1 | XLR Jack | 4-pin XLR for headset | $8 |
| 4 | Pull-up Resistor | 4.7kΩ 1/4W (if needed for I2C) | $0.10 |

#### Display Recommendations (MIPI DSI for Orange Pi 5 Pro)

**Why MIPI DSI?** Orange Pi 5 Pro has native DSI support, providing better performance, lower latency, and easier integration than HDMI for small displays.

| Display | Resolution | Size | Type | Touch | Cost | Best For |
|---------|------------|------|------|-------|------|----------|
| **Waveshare 3.4" Round OLED** ⭐ | 800×800 | 3.4" | AMOLED | Yes | $35 | Professional builds - vibrant OLED, perfect square |
| Waveshare 3.4" Square LCD | 720×720 | 3.4" | IPS LCD | Yes | $25 | Budget builds - good quality IPS |
| Generic 3.0" MIPI OLED | 480×640 | 3.0" | OLED | Optional | $20 | Basic builds - 4:3 ratio |
| Waveshare 4.0" DSI LCD | 720×720 | 4.0" | IPS | Yes | $30 | Larger display option |

**Recommended**: **Waveshare 3.4" 800×800 Round OLED Display**
- Part Number: 3.4inch DSI OLED (C)
- Interface: MIPI DSI 4-lane
- Perfect square viewable area (circular display)
- Capacitive touch with gesture support
- Direct connection to Orange Pi 5 Pro DSI connector
- No drivers needed on Armbian/Ubuntu
- Professional appearance for belt pack

**Where to Buy**:
- Waveshare Official: [waveshare.com](https://www.waveshare.com/3.4inch-dsi-oled.htm)
- Amazon: Search "Waveshare 3.4 DSI OLED"
- AliExpress: ~$30-35 with shipping

#### Cables & Connectors
| Qty | Part | Description | Est. Cost |
|-----|------|-------------|-----------|
| 1 | Dupont Cables | Female-to-female 20cm (40-pack) | $6 |
| 1 | Heat Shrink | 2:1 ratio assortment | $8 |
| 1 | Cable Strain Relief | Rubber grommet | $2 |

### Network Infrastructure (Shared)

| Qty | Component | Specification | Est. Cost |
|-----|-----------|---------------|-----------|
| 1 | Ethernet Switch | Gigabit PoE+ switch (8-24 ports) | $100-500 |
| N | Cat6 Cables | Various lengths for installation | $2-10 ea |
| 1 | Router | Gigabit router (if not using existing) | $50-150 |

**Total System Cost** (Server + 4 Beltpacks + Network):
- **Budget**: ~$1,200 (vs. $4,000+ commercial)
- **Professional**: ~$1,500 (with displays, better enclosures)
- **Commercial Equivalent**: $5,000-10,000 (Clear-Com HelixNet, RTS ADAM)

**Savings**: **75-80% cost reduction** vs commercial systems

---

## 🔌 Wiring Schematic

### Beltpack Pin Assignments

**Note**: Orange Pi 5 Pro uses 40-pin GPIO header compatible with Raspberry Pi pinout. Verify I2C bus number with `i2cdetect -l` (typically bus 3 on Orange Pi 5 Pro).

#### I2C Bus (RGB LED Buttons)

```
SBC I2C Bus 3 (pins 3 & 5 on Orange Pi 5 Pro - compatible with RPi pinout)
│
├─ 0x23 ─ Gravity RGB LED Button Module #1 (Channel 1)
├─ 0x24 ─ Gravity RGB LED Button Module #2 (Channel 2)
├─ 0x25 ─ Gravity RGB LED Button Module #3 (Channel 3)
└─ 0x26 ─ Gravity RGB LED Button Module #4 (Channel 4)

Connections per module:
├─ VCC → 3.3V or 5V (check module spec)
├─ GND → Ground
├─ SDA → Pin 3 (GPIO 2, I2C1 Data)
└─ SCL → Pin 5 (GPIO 3, I2C1 Clock)

Notes:
- Pull-up resistors (4.7kΩ to 3.3V) on SDA/SCL
- Gravity modules have built-in pull-ups
```

#### GPIO (Volume Rotary Encoders)

**⚠️ I2S AUDIO**: GPIO 18, 19, 20, 21 are **RESERVED** for built-in ES8388 audio codec. Do not use for encoders!

```
Volume Encoder 1 (Channel 1):
├─ CLK → GPIO 5  (Pin 29)
├─ DT  → GPIO 6  (Pin 31)
└─ GND → Ground  (Pin 30)

Volume Encoder 2 (Channel 2):
├─ CLK → GPIO 13 (Pin 33)
├─ DT  → GPIO 19 (Pin 35) ⚠️ I2S LRCK but safe for INPUT
└─ GND → Ground  (Pin 34)

Volume Encoder 3 (Channel 3):
├─ CLK → GPIO 26 (Pin 37)
├─ DT  → GPIO 12 (Pin 32)
└─ GND → Ground  (Pin 39)

Volume Encoder 4 (Channel 4):
├─ CLK → GPIO 16 (Pin 36)
├─ DT  → GPIO 7  (Pin 26)
└─ GND → Ground  (Pin 25)

Notes:
- CLK: Clock output A
- DT: Data output B (direction detection)
- Common pin: Ground
- Internal pull-ups enabled in software (gpiod)
- See [docs/BELTPACK_WIRING.md](docs/BELTPACK_WIRING.md) for full pinout diagram
```

#### GPIO (Menu Rotary Encoder)

```
Menu Encoder with Push Button:
├─ CLK → GPIO 17 (Pin 11)
├─ DT  → GPIO 27 (Pin 13)
├─ SW  → GPIO 22 (Pin 15) [Push button, active low]
└─ GND → Ground  (Pin 14)

Notes:
- SW pin goes LOW when button pressed
- Internal pull-up configured in software
- Used for menu navigation
```

#### Complete Orange Pi 5 Pro GPIO Header Pinout

**Note**: Orange Pi 5 Pro uses 40-pin header compatible with Raspberry Pi pinout. GPIO chip is typically `gpiochip1` (verify with `gpioinfo`).

```
     3.3V  (1) (2)  5V      ← Power rails
I2C3 SDA  (3) (4)  5V      ← I2C bus 3 (Orange Pi 5 Pro)
I2C3 SCL  (5) (6)  GND     ← Ground
          (7) (8)
      GND  (9) (10)
Menu CLK (11) (12)         ← Menu encoder CLK
Menu DT  (13) (14) GND
Menu SW  (15) (16)         ← Menu button
     3.3V (17) (18)
         (19) (20) GND
         (21) (22)
         (23) (24)
      GND (25) (26)
         (27) (28)
 Vol1 CLK (29) (30) GND    ← Volume encoder 1
 Vol1 DT  (31) (32)
 Vol2 CLK (33) (34) GND    ← Volume encoder 2
 Vol2 DT  (35) (36) Vol4 DT ← Volume encoders 2 & 4
 Vol3 CLK (37) (38) Vol3 DT ← Volume encoder 3
      GND (39) (40) Vol4 CLK ← Volume encoder 4
```

#### Audio Interface

**Orange Pi 5 Pro Built-in Audio (ES8388 Codec)**:
```
Built-in ES8388 Stereo Codec:
├─ Microphone Input  → 3.5mm mic jack (mono, 48kHz, 16-bit)
├─ Line Input        → 3.5mm line in (stereo, use left channel)
├─ Headphone Output  → 3.5mm headphone jack (stereo, 48kHz, 16-bit)
└─ Line Output       → 3.5mm line out

Configuration:
- ALSA device: hw:0,0 (check with aplay -l)
- Sample rate: 48kHz native (no resampling)
- Bit depth: 16-bit (S16_LE)
- Latency: <5ms codec delay
- No external HAT required!
```

**Alternative for Raspberry Pi** (if not using Orange Pi 5 Pro):
```
I2S Audio HAT (HiFiBerry DAC+ Zero):
├─ DAC Output → 3.5mm stereo jack
├─ ADC Input  → Requires separate USB mic or I2S ADC
└─ I2S Pins   → GPIO 18, 19, 20, 21 (reserved)

OR

USB Audio Adapter:
├─ Microphone Input  → USB port (mono, 48kHz, 16-bit)
├─ Headphone Output  → USB port (mono, 48kHz, 16-bit)
└─ GND → Common ground

Recommended USB Audio Devices:
- Generic USB soundcard (CM108/CM119 chipset)
- Behringer UCA202 (stereo, use left channel only)
- Focusrite Scarlett Solo (high-quality option)
```

#### Network & Power

```
Ethernet (RJ45):
├─ 100Mbps or 1Gbps Ethernet
└─ PoE+ support (IEEE 802.3at) for single-cable deployment

Power Options:
Option 1: PoE+ (Recommended)
  ├─ PoE Splitter → 5V 2.4A
  └─ Single Cat6 cable (data + power)

Option 2: USB-C PD
  ├─ 5V 3A (15W minimum)
  └─ Separate Ethernet cable

Option 3: DC Barrel Jack
  ├─ 5V 3A regulated supply
  └─ 2.1mm x 5.5mm jack
```

### System Wiring Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                 SERVER (Windows/Mac/Linux PC)                 │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  server.py (PyQt6 GUI)                               │    │
│  │  - TCP Server (Port 6001) - Control commands         │    │
│  │  │  - UDP Server (Port 6001) - Audio streams            │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────┬───────────────────────────────────┘
                           │ 2.5 Gigabit Ethernet
                  ┌────────▼────────┐
                  │  PoE+ Switch    │ ← 802.3af/at, 8-24 ports
                  │ (2.5Gb/1Gb)     │
                  └─┬──────┬──────┬─┘
                    │      │      │
         ┌──────────▼──┐ ┌─▼──────────┐ ┌──▼──────────┐
         │  Beltpack 1 │ │ Beltpack 2 │ │ Beltpack N  │
         │Orange Pi 5  │ │Orange Pi 5  │ │Orange Pi 5  │
         │  Pro 16GB   │ │  Pro 16GB   │ │  Pro 16GB   │
         │ ES8388 ♪    │ │ ES8388 ♪    │ │ ES8388 ♪    │
         └─────────────┘ └────────────┘ └─────────────┘
         ┌─────────────┐ ┌────────────┐ ┌─────────────┐
         │ 4× RGB Btn  │ │ 4× RGB Btn │ │ 4× RGB Btn  │
         │ 4× Vol Knob │ │ 4× Vol Knob│ │ 4× Vol Knob │
         │ 1× Menu Knob│ │ 1× Menu Knob│ │ 1× Menu Knob│
         │ Built-in ♪  │ │ Built-in ♪ │ │ Built-in ♪  │
         └─────────────┘ └────────────┘ └─────────────┘
              ║               ║               ║
         [Headset + Mic] [Headset + Mic] [Headset + Mic]
         4-pin XLR       4-pin XLR       4-pin XLR
```

## ⚙️ Configuration

### Server Config (`intercom_config.json`)

```json
{
  "users": {
    "Bob": {
      "channels": [0, 1, 4, 5],
      "button_modes": {
        "0": "latch",
        "1": "non-latch",
        "2": "latch",
        "3": "latch"
      }
    }
  },
  "channels": {
    "0": "Stage Left",
    "1": "Stage Right",
    "2": "Front of House",
    "3": "Lighting",
    "4": "Monitor Mix",
    "5": "Backstage"
  },
  "channel_volumes": {
    "0": 0.8,
    "1": 0.8,
    "2": 0.9
  },
  "channel_enabled": {
    "0": true,
    "1": true,
    "2": false
  },
  "active_channel_count": 6,
  "fourwire_enabled": [false, false]
}
```

### Button Modes

- **Latch (Toggle)**: Press once = talk on, press again = talk off
- **Non-Latch (PTT)**: Hold to talk, release to stop

Configure per user in GUI: **User tab → Select user → Button Modes button**

### Network Settings

```python
# server.py
HOST = '0.0.0.0'          # Listen on all interfaces
TCP_PORT = 6001           # HelixNet standard
UDP_PORT = 6001
AUTH_KEY = "your-secret"  # Change in production!

# beltpack.py
SERVER_HOST = '192.168.1.10'  # Auto-discovered via mDNS
RATE = 48000
CHUNK = 960  # 20ms frames
JITTER_BUFFER_SIZE = 6  # 128ms
```

---

## 🐛 Troubleshooting

### Server Won't Start

**Error**: `Address already in use`
```powershell
# Windows - kill process on port 6001
netstat -ano | findstr :6001
taskkill /PID <pid> /F

# Linux
sudo lsof -ti:6001 | xargs sudo kill -9
```

**Error**: `PyQt6 not found`
```bash
pip install --upgrade PyQt6 numpy pyaudio
```

### Beltpack Can't Connect

**Symptom**: "Connecting to server..." loop

1. **Check firewall**:
   ```powershell
   # Windows
   Test-NetConnection -ComputerName 192.168.1.10 -Port 6001
   
   # Linux
   telnet 192.168.1.10 6001
   ```

2. **Verify mDNS**:
   ```bash
   # Beltpack
   avahi-browse -a
   # Should show: _lancomm._tcp
   ```

3. **Hardcode server IP** (fallback):
   ```python
   # beltpack.py line 19
   SERVER_HOST = '192.168.1.10'  # Your server IP
   ```

### No Audio

**Symptom**: Talk button lights up, but no sound

1. **Check UDP firewall**:
   ```powershell
   # Server must allow UDP 6001 inbound
   New-NetFirewallRule -DisplayName "LanComm UDP" -Direction Inbound -Protocol UDP -LocalPort 6001 -Action Allow
   ```

2. **Test audio devices**:
   ```bash
   # Orange Pi 5 Pro
   arecord -l  # List capture devices
   aplay -l    # List playback devices
   speaker-test -c 2 -t wav  # Test speakers
   arecord -d 5 test.wav && aplay test.wav  # Test mic
   ```

3. **Check channel assignment**:
   - Server GUI → User tab → Verify user has channels assigned
   - Beltpack → Press menu button → Check channel names show

### Choppy/Distorted Audio

**Symptom**: Audio cuts out or sounds robotic

1. **Check network latency**:
   ```bash
   ping -c 100 192.168.1.10
   # Should be <1ms, <0.5% loss
   ```

2. **Increase jitter buffer**:
   ```python
   # beltpack.py line 21
   JITTER_BUFFER_SIZE = 8  # Increase from 6 to 8 (160ms)
   ```

3. **Check CPU usage**:
   ```bash
   # Beltpack
   htop  # Should be <50% on Orange Pi 5 Pro
   ```

### RGB Buttons Not Working

**Symptom**: Buttons don't light up

1. **Check I2C bus**:
   ```bash
   i2cdetect -y 3
   # Should show: 23 24 25 26
   ```

2. **Enable I2C**:
   ```bash
   sudo armbian-config
   # System → Hardware → i2c3 [enable]
   sudo reboot
   ```

3. **Test button module**:
   ```python
   import smbus2
   bus = smbus2.SMBus(3)
   bus.write_i2c_block_data(0x23, 0x00, [255, 0, 0])  # Red
   ```

### "User Already Taken" Error

**Symptom**: Can't select user profile on beltpack

- **Solution**: Server only allows one client per user (by design)
- **Workaround**: Create duplicate profiles (e.g., "Bob", "Bob2")
- **Or**: Disconnect old beltpack first

---

#### Main Process
- **Event Loop**: Asyncio managing TCP/UDP servers concurrently
- **GUI Thread**: PyQt6 application running in main thread
- **Thread Safety**: RLocks protecting shared state (config, clients, audio)

#### Key Functions

| Function | Purpose |
|----------|---------|
| `load_config()` | Loads user/channel config from JSON (thread-safe) |
| `save_config()` | Persists config to disk with proper serialization |
| `handle_tcp()` | Manages client connections, user selection, talk toggles |
| `tcp_server()` | Accepts incoming TCP connections on port 5000 |
| `receive_udp()` | Receives OPUS audio packets, validates, decodes, buffers |
| `mix_and_send()` | Mixes jitter buffers, re-encodes, multicasts to listeners |
| `ServerGUI` | PyQt6 interface with Mixer/Users/Matrix tabs and professional broadcast theme |

#### Data Structures

```python
users = {
    "Bob": {
        "channels": {0, 1, 4, 5},  # Set of subscribed channel IDs
        "client_addr": ("192.168.1.100", 12345)  # TCP address or None
    }
}

client_data = {
    ("192.168.1.100", 12345): {
        "user_name": "Bob",
        "user_id": 0,  # Sequential ID assigned on connect
        "subscribed_channels": {0, 1, 4, 5},
        "sock": <StreamWriter>,
        "last_seen": 1702838400.0  # Unix timestamp
    }
}

channel_buffers = {
    0: [np.array([...]), np.array([...])],  # Jitter buffer (2 frames)
    1: [np.array([...]), np.array([...])]
}

channel_talkers = {
    0: {0, 3, 7},  # Set of user_ids currently talking on channel 0
}

channel_listeners = {
    0: {(0, ("192.168.1.100", 12345)), ...}  # (user_id, addr) tuples
}
```

### Node Components (`beltpack.py`)

#### Main Process
- **Asyncio Thread**: Handles all network I/O (TCP control, UDP audio)
- **Qt Main Thread**: GUI rendering and user interaction
- **Audio Thread**: PyAudio callback (system-managed)
- **GPIO Thread**: Hardware button polling (200Hz, Linux only)

#### Key Functions

| Function | Purpose |
|----------|---------|
| `AudioManager` | Thread-safe audio I/O with queue-based buffering |
| `ClientApp.__init__()` | Initializes GUI, spawns async/GPIO threads |
| `connect_async()` | Establishes TCP connection, receives user_id |
| `get_users_async()` | Requests available user list from server |
| `select_user_async()` | Selects user, receives channel assignments |
| `record_send_async()` | Captures mic, encodes OPUS once, sends to all active channels |
| `receive_udp_async()` | Receives mixed audio, decodes, applies volume, outputs |
| `gpio_poll()` | Polls talk buttons (5ms), toggles channels on press |
| `update_volumes()` | Reads ADC pots (50ms), updates GUI progress bars |
| `heartbeat_async()` | Sends TCP PING every 10s to maintain connection |
| `reconnect_async()` | Handles TCP/UDP reconnection with backoff |
| `process_commands()` | Bridges asyncio→Qt thread for GUI updates |

#### Hardware Integration (Linux SBC Only)

```python
# GPIO Talk Buttons (gpiochip0, pins 0-3)
- Pull-up resistors enabled
- Polled at 200Hz (5ms interval)
- Low state = button pressed → toggle talk

# SPI ADC (MCP3008 on bus 0)
- 4 potentiometers on channels 0-3
- 10-bit resolution (0-1023)
- Polled at 20Hz (50ms interval)
- Mapped to 0-100% volume

# Audio I/O
- PyAudio with ALSA backend
- 48kHz, 16-bit mono
- 960 sample frames (20ms @ 48kHz)
```

---

## 🔧 Installation

### Prerequisites

- **Server**: Python 3.8+, any OS (Windows/Mac/Linux)
- **Nodes**: Python 3.8+, Linux (Debian/Ubuntu on SBC)
- **Network**: Local LAN with 10Gb backbone recommended, 1Gb/100Mb acceptable

### Server Installation (Windows/Mac/Linux)

```bash
# Clone repository
git clone https://github.com/yourusername/LanComm.git
cd LanComm

# Install Python dependencies
pip install PyQt6 numpy pyaudio zeroconf netifaces

# Configure authentication key (IMPORTANT!)
# Edit server.py line 27: AUTH_KEY = "your-secure-passphrase-here"

# Run server
python server.py
```

**Important Notes**:
- **Authentication**: Change `AUTH_KEY` in both `server.py` and `beltpack.py` to a secure passphrase (default: "lancomm-secure-2025")
- **Firewall**: Allow TCP/UDP port 6001 (see [docs/PORT_MIGRATION_GUIDE.md](docs/PORT_MIGRATION_GUIDE.md))
- **PyAudio on Windows**: May require Microsoft C++ Build Tools or prebuilt wheels from [https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)

### Node Installation (Orange Pi 5 Pro)

#### 1. OS Setup
```bash
# Flash Armbian or Orange Pi OS to microSD card
# Download from: http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-Pi-5-Pro.html
# Boot SBC and connect via SSH
# Default: root/orangepi or orangepi/orangepi

sudo apt-get update
sudo apt-get upgrade -y
```

#### 2. System Dependencies
```bash
# Audio libraries
sudo apt-get install -y portaudio19-dev python3-pyaudio alsa-utils

# GPIO libraries
sudo apt-get install -y python3-gpiod libgpiod-dev

# Python development
sudo apt-get install -y python3-pip python3-dev
```

#### 3. Python Dependencies
```bash
pip3 install PyQt6 numpy pyaudio zeroconf netifaces smbus2 gpiod
```

**Note**: Removed `torchaudio` and `torch` (no longer using OPUS codec). Added `smbus2` for I2C RGB buttons, `zeroconf` for mDNS discovery.

#### 4. Hardware Configuration

**I2C RGB LED Buttons** (Raspberry Pi 4):
```
I2C Bus 1 (GPIO 2 = SDA, GPIO 3 = SCL)
├─ 0x23 → Button 1 (Channel 1)
├─ 0x24 → Button 2 (Channel 2)
├─ 0x25 → Button 3 (Channel 3)
└─ 0x26 → Button 4 (Channel 4)

Connection (per button):
├─ VCC → 5V (Pin 2 or 4)
├─ GND → Ground
├─ SDA → GPIO 2 (Pin 3)
└─ SCL → GPIO 3 (Pin 5)

Note: Gravity modules have built-in pull-ups
```

**Volume Encoders** (GPIO, avoiding I2S pins 18, 20, 21):
```
See BELTPACK_WIRING.md for full pinout
Encoder 1: GPIO 5/6
Encoder 2: GPIO 13/19
Encoder 3: GPIO 26/12
Encoder 4: GPIO 16/7
```

**Audio** (Orange Pi 5 Pro Built-in ES8388):
```bash
# ES8388 audio is built-in, no configuration needed!
# Verify it's detected:
aplay -l
arecord -l

# Should show:
# card 0: audiocodec [audiocodec], device 0: CDC PCM Codec-0 []
# OR
# card 0: ES8388 [ES8388], device 0: ES8388 HiFi []

# Test audio (adjust card number if needed)
arecord -D hw:0,0 -f S16_LE -r 48000 -c 1 -d 5 test.wav
aplay -D hw:0,0 test.wav

# Set volume levels
alsamixer
# Use arrow keys: F6 to select card, adjust mic/speaker levels
```

**For Raspberry Pi** (if using HiFiBerry instead):
```bash
# Configure I2S audio HAT
sudo nano /boot/config.txt
# Add: dtoverlay=hifiberry-dac

# Reboot to apply
sudo reboot

# List audio devices
arecord -l  # Shows I2S input
aplay -l    # Shows I2S output

# Test audio (device names may vary)
arecord -D plughw:CARD=sndrpihifiberry,DEV=0 -f S16_LE -r 48000 -c 1 test.wav
aplay -D plughw:CARD=sndrpihifiberry,DEV=0 test.wav
```

#### 5. Systemd Service (Auto-start on Boot)
```bash
sudo nano /etc/systemd/system/beltpack.service
```

```ini
[Unit]
Description=LanComm Intercom Beltpack
After=network.target sound.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/LanComm
Environment="DISPLAY=:0"
ExecStart=/usr/bin/python3 /root/LanComm/beltpack.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable beltpack.service
sudo systemctl start beltpack.service

# Check status
sudo systemctl status beltpack.service

# View live logs
journalctl -u beltpack.service -f
```

#### 6. Network Configuration
```bash
# Set static IP (edit /etc/network/interfaces or NetworkManager)
sudo nano /etc/network/interfaces

# Example:
auto eth0
iface eth0 inet static
    address 192.168.1.101
    netmask 255.255.255.0
    gateway 192.168.1.1
    dns-nameservers 8.8.8.8
```

**mDNS Auto-Discovery** (recommended):
- Server broadcasts on `_lancomm._tcp.local.`
- Beltpacks auto-discover server (no manual IP config)
- Fallback to hardcoded IP if mDNS unavailable

**Manual Configuration** (if mDNS fails):
Edit `beltpack.py` line 100 (top of file):
```python
SERVER_HOST = '192.168.1.10'  # Change to your server's IP
TCP_PORT = 6001  # HelixNet standard port
UDP_PORT = 6001  # Same port for audio
```

**Authentication** (CRITICAL):
Edit both files with matching keys:
- `server.py` line 32: `AUTH_KEY = "your-secure-passphrase"`
- `beltpack.py` line 105: `AUTH_KEY = "your-secure-passphrase"` (must match!)

---

## 📖 Usage

### Server Operation

#### 1. Launch Server
```bash
python server.py
```
The PyQt6 GUI will open with 3 professional tabs:

#### 2. Mixer Tab (🎚️)
Professional channel strip interface with:
- **Channel Names**: Large, editable text fields (14pt bold, 45px tall)
- **Volume Faders**: Vertical sliders (250px tall) with precise control
- **Volume Display**: Large numeric readout (18pt)
- **Width**: 150-180px per channel for maximum visibility
- Edit names directly in the strip, adjust volume with mouse or arrow keys
- Changes save automatically to configuration

#### 3. Users Tab (👥)
Dropdown-based user management:
- **Add User**: Enter name, select up to 4 channels from dropdowns (35px tall)
- **User Cards**: Each user shows name and assigned channels
- **Update/Delete**: Buttons on each card for modifications
- Max 4 channels per user enforced by interface

**Example Users**:
```
Bob      → Stage Left, FOH, Lighting, Director
Alice    → FOH, Camera 1, Audio Booth
Charlie  → Director, Green Room, Backstage, Tech
```

#### 4. Matrix Tab (📊)
Visual grid showing user-to-channel assignments:
- **Grid View**: Users (rows) × Channels (columns)
- **Indicators**: ✓ marks show channel assignments
- **Read-only**: Update assignments via Users tab
- Auto-updates when configuration changes

#### 5. Status Bar (Real-time)
Bottom of window displays:
- **Connected Clients**: Live count of active nodes
- **Active Talkers**: Per-channel talker counts
- **Network**: TCP/UDP port status
- Updates automatically every 500ms

#### 6. Menu Bar
- **File → Save Config**: Export to `intercom_config.json`
- **File → Load Config**: Import existing configuration
- **File → Exit**: Clean shutdown of server

**Config File Example**:
```json
{
  "users": {
    "Bob": {
      "channels": [0, 1, 4, 5]
    },
    "Alice": {
      "channels": [1, 2, 3]
    }
  },
  "channels": [
    "Stage Left",
    "FOH",
    "Camera",
    "Audio",
    "Lighting",
    "Director",
    "Green Room",
    "Backstage",
    "Tech",
    "CH9"
  ],
  "channel_volumes": {
    "0": 1.0,
    "1": 0.8,
    "2": 1.0,
    ...
  }
}
```

### Node Operation

#### 1. Power On
- Connect PoE ethernet cable or power supply
- SBC boots and auto-launches beltpack app (if systemd configured)
- Full-screen GUI displays on 3.4" MIPI DSI OLED (800×800)

#### 2. Select User
- GUI shows "Select User:" with dropdown
- Choose your assigned username (e.g., "Bob")
- Click **Select**

#### 3. Channel Display
- Main screen shows assigned channels:
```
User: Bob
Stage Left: Vol [████████████████    ] On
FOH: Vol        [████████████████    ] On
Lighting: Vol   [████████████████    ] On
Director: Vol   [████████████████    ] On
```

#### 4. Controls

**Talk Buttons** (Hardware GPIO):
- Press button to toggle talk for corresponding channel
- LED/button feedback (if wired)
- Latching: press once to enable, press again to disable

**Volume Knobs** (Hardware ADC):
- Turn knob to adjust per-channel receive volume
- Progress bar updates in real-time
- Range: 0-100%

**Software Buttons** (Touchscreen):
- Tap "On" button to toggle talk (changes to "Off")
- Alternative to hardware buttons

#### 5. Audio Operation
- **Listen**: Receive audio from all assigned channels simultaneously
- **Talk**: Transmit mic to all channels with "On" status
- **Mix**: Server mixes all talkers, node mixes all received channels locally

---

## 🛠️ Configuration

### Audio Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Sample Rate | 48000 Hz | Fixed, do not change |
| Bit Depth | 16-bit | PyAudio int16 I/O |
| Channels | 1 (Mono) | Stereo not supported |
| Frame Size | 960 samples | 20ms @ 48kHz |
| Codec | **Raw PCM** | No compression (lowest latency) |
| Bitrate | 768 kbps | Fixed (48000 × 16 / 1000) |
| Sidetone | 18% | Local mic monitoring |
| VOX Threshold | -40 dB | Optional voice activation |

### Network Parameters

| Parameter | Default | Configurable |
|-----------|---------|--------------|
| TCP Port | 5000 | Change in both files |
| UDP Port | 5001 | Change in both files |
| Server IP | `192.168.1.10` | Edit `beltpack.py` line 31 |
| Buffer Size | 8192 bytes | UDP recv buffer |
| Jitter Buffer | 2 frames (40ms) | Adjust `JITTER_BUFFER_SIZE` |

### System Limits

| Limit | Value | Hard Limit |
|-------|-------|------------|
| Max Channels | **10** | Change `MAX_CHANNELS` |
| Max Channels/User | **10** (all channels) | Change `MAX_USER_CHANNELS` |
| Max Users | **20** simultaneous | Change `MAX_USERS` (line 28) |
| Max Packet Size | 8192 bytes | UDP buffer size |
| Jitter Buffer | 128ms (6 frames) | `JITTER_BUFFER_SIZE = 6` |

---

## 🔍 Troubleshooting

### Server Issues

**"Address already in use"**
```bash
# Find process using port
netstat -ano | findstr :5000  # Windows
lsof -i :5000                 # Linux/Mac

# Kill process or change port in code
```

**No audio mixing**
```bash
# Check for errors in terminal
# Verify UDP port 5001 is open in firewall
sudo ufw allow 5001/udp  # Linux
```

**Config won't load**
- Verify JSON syntax with online validator
- Check file permissions
- Look for special characters in user/channel names

### Node Issues

**Cannot connect to server**
```bash
# Ping server
ping 192.168.1.10

# Check firewall on server
# Verify SERVER_HOST in beltpack.py matches server IP

# Check logs
journalctl -u beltpack.service -f
```

**No audio input/output**
```bash
# List devices
arecord -l
aplay -l

# Test directly
arecord -D hw:0,0 -f S16_LE -r 48000 -c 1 test.wav
aplay test.wav

# Check ALSA config
alsamixer
```

**GPIO buttons not working**
```bash
# Check GPIO chip (Orange Pi uses gpiochip1)
gpioinfo

# Verify correct chip in beltpack.py (line ~130)
# self.chip = gpiod.Chip('gpiochip1')  # Orange Pi 5 Pro

# Check GPIO permissions
sudo usermod -a -G gpio $USER
sudo chmod 666 /dev/gpiochip*

# Test manually (Orange Pi)
gpioget gpiochip1 5  # Read GPIO 5 (encoder CLK)

# Reboot may be required for group changes
sudo reboot
```

**SPI ADC not working**
```bash
# Enable SPI
sudo raspi-config  # Raspberry Pi
# Or edit /boot/armbianEnv.txt for Radxa

# Verify SPI device
ls /dev/spidev*

# Test with Python
python3 -c "import spidev; s=spidev.SpiDev(); s.open(0,0); print(s.xfer2([1,128,0]))"
```

**Choppy/distorted audio**
- Increase jitter buffer: `JITTER_BUFFER_SIZE = 3` or `4`
- Check network bandwidth (run `iperf3` between nodes)
- Verify switch supports jumbo frames or isn't dropping packets
- Reduce number of active talkers per channel

**"Hardware libraries not available"**
- Expected on Windows (simulation mode)
- On Linux, install: `pip3 install spidev gpiod`

### Network Issues

**High latency (>100ms)**
- Check for WiFi (use wired only)
- Verify QoS settings on switch
- Disable power saving on NICs
- Use 1Gb+ switches, avoid 100Mb

**Packet loss**
- Check switch buffer sizes
- Use dedicated VLAN for intercom traffic
- Enable IGMP snooping for multicast efficiency
- Upgrade to 10Gb backbone

---

## 📊 Performance Metrics

### Latency Breakdown (Typical)
```
Audio Capture:         0-3 ms   (PyAudio callback, 20ms chunks)
PCM Buffering:         0-1 ms   (No encoding needed)
Network (LAN):         1-3 ms   (1Gb/2.5Gb ethernet)
Server Processing:     3-8 ms   (PCM mix, no decode/encode)
Network (LAN):         1-3 ms   (return trip)
PCM Buffering:         0-1 ms   (No decoding needed)
Audio Output:          0-3 ms   (PyAudio callback)
Jitter Buffer:         128 ms   (6 frames @ 20ms - adaptive)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:                 133-150 ms (with conservative buffer)
Optimal (2-frame buf): 8-25 ms   (competitive with HelixNet)
```

**Note**: Jitter buffer is the main latency factor. Reduce to 2-3 frames (40-60ms) for lower latency on stable networks.

### Bandwidth Usage
```
Per talker uplink:    ~768 kbps (raw PCM, 48kHz 16-bit mono)
Per listener downlink:~768 kbps (mixed PCM from server)
Per node (4 channels):~3.07 Mbps uplink + 3.07 Mbps downlink
Per node (talking all):~7.68 Mbps uplink (10 channels)
20 nodes typical:     ~30-60 Mbps (30-50% talk time)
20 nodes peak:        ~150 Mbps (all talking, all channels)

Network Requirements:
- 100Mbps: Marginal for 10 nodes (not recommended)
- 1Gbps: Comfortable for 20-30 nodes
- 2.5Gbps: Recommended (Orange Pi 5 Pro native)
- 10Gbps: Future-proof for 100+ nodes
```

**Raw PCM vs OPUS**: Raw PCM trades bandwidth for minimal latency (no codec delay). OPUS compression would reduce bandwidth by 5-10x but adds 10-15ms encoding/decoding delay per hop.

### System Requirements

**Server:**
- CPU: 2+ cores, 2.0 GHz (Intel i5/Ryzen 5 or better)
- RAM: 4 GB minimum, 8 GB recommended
- Network: 1Gb NIC (2.5Gb/10Gb for large deployments)
- OS: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)

**Beltpack (Orange Pi 5 Pro - Recommended Platform):**
- **SBC**: Orange Pi 5 Pro 16GB - $110
- **CPU**: RK3588S Octa-core (4×A76 @ 2.4GHz + 4×A55 @ 1.8GHz)
- **RAM**: 16GB LPDDR4X
- **Audio**: Built-in ES8388 codec (no HAT needed!)
- **Network**: 2.5 Gigabit Ethernet
- **PoE HAT**: Waveshare PoE HAT - $22 (802.3af/at)
- **I2C Buttons**: 4× Gravity RGB LED - $32 ($8 ea)
- **Encoders**: 5× EC11 Rotary - $13
- **Enclosure**: ABS/Aluminum case - $15
- **MicroSD**: 32GB Class 10 - $10
- **Display** (optional): 3.4" MIPI DSI OLED 800×800 - $35
- **Total: ~$210-245/node** (vs $500-1000 commercial)

**Alternative: Raspberry Pi 4 (Budget Option)**
- Pi 4 Model B 2GB: $35
- Official PoE HAT: $20
- HiFiBerry DAC+ Zero: $20
- Same buttons/encoders/case: $60
- **Total: ~$135-160/node** (requires audio HAT)

---

## 🧪 Testing Without Hardware

### Windows/Mac Testing

Run both server and node on the same machine:

```bash
# Terminal 1: Start server
python server.py

# Terminal 2: Edit beltpack.py (line 31)
# Change: SERVER_HOST = '127.0.0.1'

# Run node
python beltpack.py
```

**Virtual Audio Cables** (for testing with multiple instances):
- Windows: VB-Cable (https://vb-audio.com/Cable/)
- macOS: BlackHole (https://github.com/ExistentialAudio/BlackHole)
- Linux: PulseAudio loopback (`pactl load-module module-loopback`)

### Simulated GPIO/SPI

Hardware imports fail gracefully on Windows:
```python
# Automatically mocked:
HARDWARE_AVAILABLE = False
read_pot(ch) → returns 50.0 (mid-range)
talk_lines[i] → returns None (no GPIO)
```

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` folder:

### Getting Started
- **[QUICK_START.md](docs/QUICK_START.md)** - 3-step guide to get running in 5 minutes
- **[PORT_MIGRATION_GUIDE.md](docs/PORT_MIGRATION_GUIDE.md)** - Firewall configuration for port 6001

### Hardware Setup
- **[HARDWARE_RECOMMENDATIONS.md](docs/HARDWARE_RECOMMENDATIONS.md)** - Complete SBC comparison (Pi 4 vs Rock Pi vs Orange Pi)
- **[BELTPACK_HARDWARE.md](docs/BELTPACK_HARDWARE.md)** - Pi 4 platform specification with I2S pin warnings
- **[BELTPACK_WIRING.md](docs/BELTPACK_WIRING.md)** - GPIO pinout diagrams and wiring schematics

### Configuration & Deployment
- **[NETWORK_SETUP.md](docs/NETWORK_SETUP.md)** - Network architecture, QoS, VLAN, PoE requirements
- **[CHANGES_IMPLEMENTED.md](docs/CHANGES_IMPLEMENTED.md)** - Complete changelog of HelixNet parity features
- **[COMPATIBILITY_FIXES.md](docs/COMPATIBILITY_FIXES.md)** - Cross-platform compatibility notes

### Technical Analysis
- **[HELIXNET_COMPARISON_ANALYSIS.md](docs/HELIXNET_COMPARISON_ANALYSIS.md)** - 68-page technical comparison with ClearCom HelixNet
- **[BELTPACK_VERIFICATION.md](docs/BELTPACK_VERIFICATION.md)** - Code verification report confirming all features

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Web-based configuration interface
- [ ] VAD (voice activity detection) for auto-mute
- [ ] Tally light integration (GPIO outputs)
- [ ] Dante/AES67 audio I/O
- [ ] AES encryption (was removed for simplicity)
- [ ] Recording/playback functionality
- [ ] Mobile app clients (iOS/Android)
- [ ] Zeroconf/mDNS auto-discovery

### Development Setup

```bash
git clone https://github.com/yourusername/LanComm.git
cd LanComm

# Install dev dependencies
pip install black pylint pytest

# Format code
black *.py

# Lint
pylint server.py beltpack.py

# Run tests (if implemented)
pytest tests/
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Inspired by:
- **Clear-Com HelixNet**: Professional wired partyline intercom
- **Unity Intercom**: Software-based flexible intercom solution
- **RTS Intercom Systems**: Broadcast industry standard

Built with:
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - Professional GUI framework
- [PyAudio](http://people.csail.mit.edu/hubert/pyaudio/) - Real-time audio I/O
- [NumPy](https://numpy.org/) - High-performance audio processing and mixing
- [gpiod](https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/) - Modern GPIO control (Linux)
- [smbus2](https://github.com/kplindegaard/smbus2) - I2C communication for RGB buttons
- [zeroconf](https://github.com/python-zeroconf/python-zeroconf) - mDNS service discovery

---

## 📞 Support

- **Issues**: https://github.com/zeostjh/LanComm/issues
- **Discussions**: https://github.com/zeostjh/LanComm/discussions
- **Email**: Contact via GitHub

---

---

<div align="center">

## 🚀 Ready to Get Started?

<table>
<tr>
<td align="center" width="33%">

### ⚡ Quick Deploy
```bash
git clone https://github.com/zeostjh/LanComm.git
cd LanComm
pip install -r requirements.txt
python server.py
```
**[→ Quick Start Guide](docs/QUICK_START.md)**

</td>
<td align="center" width="33%">

### 📚 Documentation
Complete setup guides for  
server and beltpacks  
with wiring diagrams
  
**[→ View Docs](docs/)**

</td>
<td align="center" width="33%">

### 💬 Get Help
Join our community  
for support and  
feature requests
  
**[→ Discussions](https://github.com/zeostjh/LanComm/discussions)**

</td>
</tr>
</table>

---

### 🎯 Project Stats

![GitHub code size](https://img.shields.io/github/languages/code-size/zeostjh/LanComm?style=flat-square)
![Lines of code](https://img.shields.io/tokei/lines/github/zeostjh/LanComm?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/zeostjh/LanComm?style=flat-square)

**Lines of Code**: ~3,000  
**Development Time**: 200+ hours  
**Cost Savings**: 75-80% vs commercial  

---

### 💪 Built With

<table>
<tr>
<td align="center"><img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/></td>
<td align="center"><img src="https://img.shields.io/badge/PyQt6-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6"/></td>
<td align="center"><img src="https://img.shields.io/badge/NumPy-Audio-013243?style=for-the-badge&logo=numpy&logoColor=white" alt="NumPy"/></td>
<td align="center"><img src="https://img.shields.io/badge/asyncio-Network-2C5BB4?style=for-the-badge" alt="asyncio"/></td>
</tr>
</table>

---

### 🏆 Why LanComm?

| Feature | LanComm | Commercial | Advantage |
|---------|---------|------------|-----------|
| **Cost** | $210/pack | $1,000-$2,500 | **75-80% savings** |
| **Latency** | <50ms | 20-50ms | **Competitive** |
| **Users** | 20 | 64-128 | Scalable for small-mid productions |
| **Open Source** | ✅ | ❌ | **Fully customizable** |
| **4-Wire Bridge** | 2 interfaces | 1-2 | **Equal/better** |
| **Audio Quality** | 48kHz/16-bit PCM | Varies | **Uncompressed** |

---

### 🌟 Community Showcase

*Have you built a LanComm system? Share your setup!*

<table>
<tr>
<td align="center" width="50%">
<img src="https://via.placeholder.com/400x300/1a1a1d/5096ff?text=Your+Setup+Photo" alt="Community Setup 1"/>
<br/>
<b>Your Production</b>
<br/>
<i>Share your deployment story</i>
</td>
<td align="center" width="50%">
<img src="https://via.placeholder.com/400x300/1a1a1d/5096ff?text=Submit+Your+Photo" alt="Community Setup 2"/>
<br/>
<b>Open a PR!</b>
<br/>
<i>Add your setup to the showcase</i>
</td>
</tr>
</table>

---

### 📬 Stay Connected

<div align="center">

[![GitHub followers](https://img.shields.io/github/followers/zeostjh?style=social)](https://github.com/zeostjh)

**Questions? Feature requests? Bug reports?**  
[Open an issue](https://github.com/zeostjh/LanComm/issues/new) or start a [discussion](https://github.com/zeostjh/LanComm/discussions)

</div>

---

<div align="center">

### Made with ❤️ for the live production community

**© 2025 LanComm Project**  
*Professional communication shouldn't cost a fortune*

[⬆ Back to top](#lancomm)

</div>

</div>
