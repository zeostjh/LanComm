# LanComm: Local Network Intercom System

## Architecture Overview

This is a low-latency, full-duplex IP-based intercom system with central server routing and distributed belt-pack clients. Not a peer-to-peer system—all audio flows through the server for mixing and redistribution.

**Key Components:**
- [server.py](../server.py): Central hub (PC/Mac/Linux) handling routing, PCM encoding/mixing, PyQt6 GUI for config
- [beltpack.py](../beltpack.py): Client nodes on Orange Pi 5 Pro SBCs with built-in audio I/O, GPIO controls, OLED touchscreen
- Network: Local LAN only (10Gb backbone, 1Gb/2.5Gb edge, PoE-powered nodes)

**Data Flow:**
1. Node captures mic audio → PCM encode → UDP to server (with channel/user_id/seq header)
2. Server decodes, mixes per-channel (sum/normalize/volume/clip), re-encodes → UDP multicast to listeners
3. Node decodes, applies per-channel volume, mixes locally → headset output

## Critical Design Constraints

- **Max 10 channels, 30 nodes, 4 channels/user**: Hard limits in `MAX_CHANNELS`, `MAX_USER_CHANNELS`
- **20ms PCM chunks (960 samples @ 48kHz)**: Fixed `CHUNK=960`, do not change without codec adjustments
- **Jitter buffer = 3 frames**: `JITTER_BUFFER_SIZE=3` for latency/stability tradeoff
- **No authentication**: Simplified for ease-of-use, local network trust model
- **Float32 audio pipeline**: Int16 I/O (PyAudio), but all mixing in float32 for precision

## Key Patterns

### Audio Pipeline
- **Server**: `wave` module for PCM decode, NumPy for mixing (per-talker normalization), `wave` for PCM encode
- **Node**: PyAudio callback for zero-copy I/O, `io.BytesIO` for in-memory PCM codec ops (no file I/O)
- **Volume Control**: Server applies global `channel_volumes[ch]` (0-1.0), nodes apply per-channel `volumes[idx]/100` locally

### Network Protocol
- **TCP (port 5000)**: Client-server control (user select, talk toggle). Commands: `GET_USERS`, `SELECT_USER:<name>`, `TOGGLE_TALK:<ch>:<0|1>`
- **UDP (port 5001)**: Audio transport. Packet: `[ch:4][user_id:4][seq:4][raw_pcm_int16]` (big-endian ints)
- **Connection Management**: Nodes auto-reconnect on TCP/UDP errors (5s backoff), server tracks via `client_data[addr]`

### GPIO/Hardware (Node Only)
- **Talk Buttons**: 4 GPIO inputs (gpiochip0, pins 0-3) with pull-up, polled at 200Hz (5ms sleep). Low = toggle talk
- **Volume Knobs**: MCP3008 ADC via SPI bus 0, 4 pots on channels 0-3. Polled at 20Hz (50ms Qt timer)
- **Display**: 3" OLED on SBC, fullscreen PyQt6 app (`showFullScreen()`)

## Developer Workflows

### Running the System
```powershell
# Server (Windows/Mac/Linux)
python server.py  # Opens PyQt6 GUI, starts async TCP/UDP servers

# Node (on SBC with systemd auto-start)
python beltpack.py  # Fullscreen user-select GUI, connects to server

# For production, create systemd service:
# /etc/systemd/system/beltpack.service -> ExecStart=/usr/bin/python3 /path/to/beltpack.py
```

### Configuration
- **Edit config**: Server GUI tabs (Channels/Users/Matrix), then File → Save
- **JSON format** (`intercom_config.json`):
  ```json
  {
    "users": {"Bob": {"channels": [0,1,4,5]}},
    "channels": ["CH0", "CH1", ...],
    "channel_volumes": {"0": 1.0, ...}
  }
  ```
- **Matrix View**: Visual grid of user-to-channel assignments (read-only, update via Users tab)

### Testing Without Hardware
- **Node simulation**: Comment out GPIO/SPI imports in [beltpack.py](../beltpack.py), replace `read_pot()` with `return 50.0`, mock talk button presses
- **Audio loopback**: Use virtual audio cables (VB-Cable on Windows, PulseAudio loopback on Linux)
- **Network**: Run server and node on same machine, change `SERVER_HOST = '127.0.0.1'` in [beltpack.py](../beltpack.py#L19)

## Common Modifications

### Adding Channels
- Update `MAX_CHANNELS` in both files, extend `channels` list, regenerate config
- Server GUI auto-sizes table rows

### Adjusting Latency
- Lower latency: Reduce `CHUNK` (e.g., 480 = 10ms) + `JITTER_BUFFER_SIZE = 1`
- Higher stability: Increase `JITTER_BUFFER_SIZE = 3-4`

### Volume Defaults
- Per-channel global: [server.py](../server.py#L28) `channel_volumes = {ch: 0.8 for ch in range(MAX_CHANNELS)}`
- Per-node initial: [beltpack.py](../beltpack.py#L58) `self.volumes = [75.0] * MAX_NODE_CHANNELS`

### AES Encryption (Removed)
- Original design had optional AES, stripped for simplicity
- Re-add: Wrap encoded OPUS data with `cryptography.fernet` before UDP send, decrypt on receive

## Dependencies
- **Server**: `PyQt6`, `numpy` (no GPIO/SPI)
- **Node**: Same + `pyaudio`, `spidev`, `gpiod` (SBC hardware libs)
- Install: `pip install PyQt6 numpy pyaudio` (add `spidev gpiod` on SBC)

## Debugging Tips
- **No audio**: Check `RATE=48000` matches hardware, verify UDP packets with Wireshark on port 5001
- **Choppy audio**: Increase jitter buffer, check LAN bandwidth (expect ~200kbps/user for 4 channels)
- **Node not connecting**: Verify `SERVER_HOST` IP, check firewall allows TCP 5000 + UDP 5001
- **User already taken**: [server.py](../server.py#L82) prevents multi-client per user, disconnect old client first

## Project Context
Inspired by Unity Intercom (app-based) and Clear-Com HelixNet (hardware partyline), but fully open-source and SBC-based. Total BOM ~$120/node (vs. $500-$1000 commercial). Designed for live events, broadcast, or construction site deployments where low-latency local comms trump cloud/mobile flexibility.
