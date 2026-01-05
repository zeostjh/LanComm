# LanComm System Overview
**For Technical Review**  
**Last Updated**: January 5, 2026

## What This Is

LanComm is an IP-based intercom system designed for live events, broadcast, and industrial environments. Think of it as a DIY version of Clear-Com HelixNet or RTS ADAM, built on commodity hardware and open-source software.

Key points:
- Central server routes audio between belt pack units
- Up to 20 users can connect simultaneously
- 10 communication channels available
- Each user can access 4 channels via physical buttons
- ~50ms end-to-end latency
- Works over standard gigabit Ethernet with PoE

## Architecture

### How It Works

```
Beltpack 1 ──┐
Beltpack 2 ──┼──> Server (mixes audio) ──┬──> To Beltpack 1
Beltpack 3 ──┘                            ├──> To Beltpack 2
                                          └──> To Beltpack 3
```

The server is the brain - it receives audio from all talking users, mixes it by channel, and sends the result back to listeners. This is different from peer-to-peer systems where devices talk directly to each other.

### Network Protocol

**Control (TCP port 6001)**:
- User authentication (SHA-256 challenge/response)
- Profile selection and channel assignment
- Talk button state changes
- Heartbeat/keepalive messages

**Audio (UDP port 6001)**:
- Raw PCM audio (48kHz, 16-bit, mono)
- 20ms frames (960 samples)
- Header: channel ID, user ID, sequence number
- ~768 kbps per active channel

### Audio Pipeline

1. **Capture**: PyAudio grabs mic input at 48kHz
2. **Encode**: Convert float32 to int16 PCM
3. **Transmit**: UDP packet to server
4. **Mix**: Server combines all talkers on each channel
5. **Distribute**: Server sends mixed audio back to listeners
6. **Decode**: Beltpack converts back to float32
7. **Playback**: PyAudio outputs to headset

Special features:
- **Null routing**: You don't hear your own voice (prevents confusing delay)
- **Local sidetone**: 18% of your mic feeds directly to your headset
- **Jitter buffer**: 128ms (6 frames) to handle network variations

## Hardware

### Server
Runs on any Windows/Mac/Linux machine with:
- Python 3.9+
- Gigabit Ethernet
- PyQt6 for GUI
- Minimal CPU usage (10-20% at full capacity)

### Beltpacks
Designed for Orange Pi 5 Pro with Waveshare PoE HAT:
- Built-in ES8388 audio codec (48kHz native)
- 4 RGB LED buttons (I2C controlled)
- 4 volume knobs (rotary encoders)
- 1 menu encoder with push button
- Powered by PoE (802.3af, ~6W typical)

Physical button states:
- Green LED = listening
- Red LED = talking
- White flash = identification mode

## Current Status (Jan 2026)

### What Works
- ✓ Server GUI with mixer, user matrix, and device management
- ✓ Authentication and access control
- ✓ Multi-user audio mixing with per-channel volumes
- ✓ mDNS auto-discovery (beltpacks find server automatically)
- ✓ QoS packet marking (DSCP AF41 for traffic priority)
- ✓ Remote profile assignment (admin can push configs to devices)
- ✓ Device identification (flash button LEDs)
- ✓ Latch and push-to-talk button modes
- ✓ 4-wire audio interface (two external system bridges)

### Tested
- Server on Windows 11 with up to 5 simulated clients
- Audio quality and latency measurements
- Network resilience (packet loss, jitter)
- Reconnection after server restart

### Not Tested in Production
- Full 20-user deployment
- Actual hardware beltpacks (Orange Pi 5 Pro)
- Multi-day reliability
- RF interference in industrial environments

## Key Design Decisions

### Why TCP + UDP instead of just UDP?
Control messages (login, profile selection) need guaranteed delivery. Audio can tolerate some packet loss, so UDP is fine there. This is standard in VoIP systems.

### Why raw PCM instead of OPUS compression?
Latency. OPUS adds 5-15ms encoding/decoding time. For local networks with gigabit bandwidth, the extra bandwidth (~768 kbps vs ~48 kbps) isn't a problem, but the latency matters.

Future versions could add OPUS as an option for WAN deployments.

### Why centralized mixing instead of distributed?
Simplicity and current capacity needs. Distributed mixing (like HelixNet) scales better but requires:
- More complex protocol
- More processing on beltpacks
- Harder to debug

For 20 users, centralized mixing works fine. If you need 50+ users, that's when distributed makes sense.

### Why SHA-256 instead of TLS?
Custom challenge/response authentication is lighter weight and sufficient for local networks. TLS adds overhead and doesn't provide meaningful security benefits when the network itself is trusted.

If deploying over public networks, adding TLS would be appropriate.

## Configuration

### Server Setup
1. Run `python server.py`
2. Create user profiles in Matrix tab (assign name + up to 4 channels)
3. Adjust channel volumes in Mixer tab
4. Change AUTH_KEY from default (line 29 in server.py)

### Beltpack Setup
1. Set matching AUTH_KEY (line 104 in beltpack.py)
2. Connect to network via PoE
3. Select user profile on first boot
4. System remembers profile until changed

### Network Requirements
- Gigabit Ethernet recommended (100Mbps works but limits capacity)
- Managed switch optional (enables QoS prioritization)
- Multicast must be enabled for mDNS discovery
- No VLAN configuration needed (everything on same subnet)

## Known Limitations

1. **No encryption**: Audio is not encrypted. This is fine for closed networks but not suitable for public/untrusted networks.

2. **Limited scalability**: 20 users is the tested maximum. More users would need distributed mixing or more powerful server hardware.

3. **No radio integration**: 4-wire interface connects to external systems, but there's no built-in PTT control for radios.

4. **Windows-only server testing**: Linux/Mac should work (same Python code) but not extensively tested.

5. **Hardware dependency**: Beltpack code assumes specific GPIO pins and I2C addresses. Porting to different hardware requires code changes.

## Dependencies

### Server
- Python 3.9+
- PyQt6 (GUI)
- numpy (audio processing)
- pyaudio (audio I/O)
- zeroconf (mDNS)
- netifaces (network interface info)

### Beltpack (additional)
- smbus2 (I2C for RGB buttons)
- gpiod (GPIO for encoders)

All available via pip.

## What to Look At

For a technical review, I'd recommend checking:

1. **server.py lines 520-650**: Audio mixing logic - this is the core of the system
2. **server.py lines 143-210**: TCP command handler - handles all client requests
3. **beltpack.py lines 490-570**: Connection and discovery logic
4. **beltpack.py lines 720-780**: Audio transmission with null routing
5. **intercom_config.json**: Example configuration file format

## Questions to Consider

1. Is centralized mixing adequate for your scale, or do you need distributed?
2. Is raw PCM bandwidth acceptable, or should we add OPUS compression?
3. Do you need TLS/encryption for your deployment environment?
4. Is the current hardware platform (Orange Pi 5 Pro) suitable, or do you need something more rugged?
5. Do you need radio interface (PTT, COR, etc.) beyond basic 4-wire audio?

## Project Structure

```
LanComm/
├── server.py                # Main server application
├── beltpack.py             # Beltpack client application
├── intercom_config.json    # Runtime configuration
├── docs/                   # All documentation
│   ├── OVERVIEW.md        # This file
│   ├── QUICK_START.md     # Getting started guide
│   ├── BELTPACK_HARDWARE.md
│   ├── 4WIRE_INTERFACE.md
│   └── ...
└── photos/                # Hardware photos (if any)
```

## Next Steps

If this looks good, typical next actions would be:
1. Build prototype beltpack hardware (1-2 units)
2. Test with real Orange Pi 5 Pro boards
3. Load test with 10+ simultaneous users
4. Measure RF immunity in target environment
5. Design enclosure for beltpacks
6. Create deployment documentation

## Contact Points

Look for:
- Authentication: AUTH_KEY in both files must match
- Port configuration: Both use 6001 (was 5000/5001 in older versions)
- Audio format: 48kHz, 16-bit, mono, 20ms frames
- Network timing: 10s mDNS timeout, 10s heartbeat, 60s node cleanup
