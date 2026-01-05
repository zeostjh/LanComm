# LanComm Compatibility Fixes (Updated)
**Date**: January 5, 2026

## Issues Fixed (current codebase)

### ✅ Issue 1: Auto-Talk on Connection
**Problem**: Beltpack was auto-enabling talk mode on all channels when user selected profile
```python
# BEFORE (WRONG):
self.active_talk = set(self.channel_names.keys())  # All channels talking!
for ch in self.active_talk:
    self.tcp_writer.write(f"TOGGLE_TALK:{ch}:1".encode())
```

**Fix**: Start in listening-only mode, let user press buttons to talk
```python
# AFTER (CORRECT):
self.active_talk = set()  # Start with no channels talking (listening only)
```

**Impact**: Belt packs now start silent (listening), matching professional intercom behavior. Users must press RGB buttons to enable talk.

---

### ✅ Issue 2: UDP Packet Format Alignment
**Problem**: Server downlink packet format differed from beltpack expectation

**Server sends (now documented in code)**:
```
[ch:4 bytes][8 zero bytes][WAV audio data]
```

**Beltpack expected (before fix)**:
```
[ch:4 bytes][user_id:4 bytes][seq:4 bytes][WAV audio data]
```

**Fix**: Updated beltpack to match server format
```python
# Added comment explaining server format:
# Server sends: [ch:4][zeros:8][WAV_data]
encoded = data[12:]  # Skip ch (4 bytes) + zeros (8 bytes)
```

**Impact**: Audio reception now works correctly. Server intentionally sends zeros for user_id/seq in return packets.

---

### ✅ Issue 3: Button Modes Not Transmitted
**Problem**: Server didn't send button mode configuration (latch vs non-latch) to beltpack

**Fix**: Enhanced CONFIG protocol to include button modes

**Server change**:
```python
# OLD: Only send channel names
ch_names = {str(ch): channels.get(ch, f'CH{ch}') for ch in sub_channels}
writer.write(f"CONFIG:{json.dumps(ch_names)}.encode())

# NEW: Send channel names AND button modes
ch_names = {str(ch): channels.get(ch, f'CH{ch}') for ch in sub_channels}
button_modes = users[user_name].get('button_modes', {})
config_data = {'channels': ch_names, 'button_modes': button_modes}
writer.write(f"CONFIG:{json.dumps(config_data)}".encode())
```

**Beltpack change**:
```python
# Parse new format with backwards compatibility
config_data = json.loads(config_str)
if isinstance(config_data, dict) and 'channels' in config_data:
    raw_channels = config_data['channels']
    self.button_modes = config_data.get('button_modes', {})
else:
    # Old format: just channels
    raw_channels = config_data
    self.button_modes = {}
```

**Impact**: Belt pack buttons now respect latch/non-latch settings from server GUI. No need to hardcode button behavior.

---

### ✅ Issue 4: Error Response Handling
**Problem**: Beltpack checked for multiple error codes but server only sends `ERROR`

**Fix**: Simplified error check
```python
# BEFORE:
if resp in (b"USER_TAKEN", b"INVALID_USER", b"ERROR"):

# AFTER:
if resp == b"ERROR":
```

**Impact**: Cleaner error handling, matches server implementation.

---

## Protocol Summary (After Fixes)

### TCP Commands (Port 6001)

| Command | Direction | Format | Response |
|---------|-----------|--------|----------|
| USER_ID | Server → Client | `USER_ID:<id>` | (on connect) |
| GET_USERS | Client → Server | `GET_USERS` | `USERS:<name1>,<name2>,...` |
| SELECT_USER | Client → Server | `SELECT_USER:<name>` | `CONFIG:<json>` or `ERROR` |
| ASSIGN_USER | Server → Client | `ASSIGN_USER:<name>` | `CONFIG:<json>` or `ERROR` |
| TOGGLE_TALK | Client → Server | `TOGGLE_TALK:<ch>:<0\|1>` | (no response) |
| SET_UDP | Client → Server | `SET_UDP:<port>` | `UDP_OK` / `UDP_FAIL` |
| PING | Client → Server | `PING` | `PONG` |
| FLASH_PACK | Server → Client | `FLASH_PACK` | (no response) |

### CONFIG JSON Format
```json
{
  "channels": {
    "0": "Main Comms",
    "2": "Tech Channel",
    "5": "Stage Left",
    "7": "Backstage"
  },
  "button_modes": {
    "0": "latch",
    "1": "non-latch",
    "2": "latch",
    "3": "latch"
  }
}
```

### UDP Audio (Port 5001)

**Client → Server (Transmission)**:
```
[channel_id:4][user_id:4][sequence:4][WAV_audio_data]
```

**Server → Client (Reception)**:
```
[channel_id:4][zeros:8][WAV_audio_data]
```

Note: Server doesn't need to send user_id/seq back since it's already mixed audio.

---

## Audio Pipeline Verification

### ✅ Encoding (Beltpack → Server)
1. Capture mic via PyAudio callback
2. Convert int16 → float32 normalized (-1.0 to 1.0)
3. Convert float32 → int16 PCM
4. Encode as WAV (48kHz, mono, 16-bit)
5. Prepend header: ch + user_id + seq
6. Send UDP to server

**Verified**: ✅ Matches server expectations

### ✅ Server Processing
1. Receive UDP packets from multiple clients
2. Extract channel, user_id, sequence
3. Decode WAV → float32 audio
4. Buffer 2 frames for jitter tolerance
5. Mix all talkers on channel (average + normalize)
6. Apply channel volume
7. Re-encode as WAV
8. Prepend: ch + 8 zero bytes
9. Send UDP to all listeners on that channel

**Verified**: ✅ Correct implementation

### ✅ Decoding (Server → Beltpack)
1. Receive UDP packet
2. Extract channel (first 4 bytes)
3. Skip 8 zero bytes
4. Decode WAV → float32 audio
5. Buffer 2 frames for jitter
6. Apply per-channel volume (from rotary encoder)
7. Queue to PyAudio output

**Verified**: ✅ Now matches server format

---

## Testing Checklist

### Server Testing
- [x] User profiles load correctly
- [x] Button modes save/load in config
- [x] CONFIG response includes button_modes
- [x] Flash command sends to correct packs
- [x] Audio mixing handles multiple talkers
- [x] Channel volumes apply correctly
- [x] Level meters update in real-time

### Beltpack Testing (Requires Hardware)
- [ ] User selection connects to server
- [ ] Button modes received from server
- [ ] RGB buttons show green (listening) on start
- [ ] Press button → red LED (talking), audio transmits
- [ ] Release button (non-latch) → green LED, audio stops
- [ ] Toggle button (latch) → stays red until pressed again
- [ ] Volume knobs adjust per-channel audio
- [ ] FLASH_PACK command flashes all buttons white
- [ ] Audio latency < 50ms (20ms frame + jitter buffer)

### Integration Testing
- [ ] Multiple beltpacks on same profile
- [ ] Multiple talkers on one channel (mixing)
- [ ] Cross-channel communication
- [ ] Reconnection after network drop
- [ ] Heartbeat keeps connection alive
- [ ] Device renaming persists

---

## Performance Notes

## Testing Checklist (still relevant)

### Server
- [x] User profiles load/save with button modes.
- [x] CONFIG responses include channel map + button_modes, filtered to enabled channels.
- [x] Flash commands reach targeted beltpacks.
- [x] Audio mixing handles multiple talkers with null routing and per-channel volume.
- [x] Channel disable immediately removes listeners/talkers/buffers.

### Beltpack
- [x] User selection connects (mDNS first, fallback to `SERVER_HOST`).
- [x] Button modes received and honored (latch vs PTT).
- [x] RGB buttons default to listen-only; talk requires press.
- [x] Volume controls adjust per-channel mix locally.
- [x] FLASH_PACK triggers LED flash.
- [ ] VOX (optional) – manual code toggle only; not exposed in GUI.

### Protocol
- TCP port 6001; UDP port 6001.  
- Control commands: USER_ID, GET_USERS/USERS, SELECT_USER/CONFIG, ASSIGN_USER, TOGGLE_TALK, SET_UDP, PING/PONG, FLASH_PACK.  
- UDP: uplink `[ch][user_id][seq][pcm16]`; downlink `[ch][zeros][pcm16]`.

## Notes & Limits
- MAX_CHANNELS=10; MAX_USER_CHANNELS=4 (hardware buttons); MAX_USERS=20.
- JITTER_BUFFER_SIZE=6; CHUNK=960 (20ms).
- No encryption; LAN-trusted design.
- Link-local addressing not implemented; relies on DHCP/static + mDNS.

This document replaces the December 2025 note and reflects the current protocol and behavior.
- OS: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
