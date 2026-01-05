# 4-Wire Audio Interface

## Overview
The 4-wire interface allows LanComm to connect to external communication systems (like FreeSpeak II wireless intercoms) via a standard 4-wire audio bridge. This creates seamless interoperability between LanComm and other professional comm systems.



## Architecture

### Virtual Beltpack Approach
The 4-wire interface acts as a "virtual beltpack" on the LanComm system:
- Has its own special user ID (-2) to avoid conflicts with real users
- Appears as an always-connected user on the assigned channel
- Operates entirely in the audio mixing domain (no UDP overhead)



### Audio Flow

#### Input Path (External → LanComm)
1. External system audio → USB audio interface input
2. PyAudio input stream captures audio (48kHz, 16-bit mono)
3. Apply input gain (configurable 0-100%)
4. Inject directly into assigned channel's buffer queue
5. Mix engine treats it like any other beltpack

#### Output Path (LanComm → External)
1. Mix engine processes channel audio from all talkers
2. Tap the mixed output for assigned channel
3. Exclude 4-wire's own input (prevents feedback loop)
4. Apply output gain and channel volume
5. Audio output stream sends to serial bus DAC
6. External system receives audio



## Hardware Requirements

### Recommended USB Audio Interfaces
- **Focusrite Scarlett 4i4** (4×4, USB-C, low latency)
- **MOTU M4** (4×4, USB-C, professional grade)
- **Behringer UMC404HD** (4×4, budget-friendly)

### Specifications
- **Sample Rate**: 48kHz (matches LanComm system)
- **Bit Depth**: 16-bit
- **Channels**: Mono (1 channel in/out minimum)
- **Latency**: <10ms round-trip preferred

### Wiring Example (Focusrite Scarlett 4i4)
```
External System                 Scarlett 4i4
┌──────────────┐               ┌─────────────┐
│              │               │             │
│  TX Audio ───┼──────────────>│ Input 1     │
│              │               │             │
│  RX Audio <──┼───────────────│ Output 1    │
│              │               │             │
│  Common   ───┼───────────────│ Ground      │
└──────────────┘               └─────────────┘
```



## Configuration

### Server GUI Controls

#### Header Section
Located in the server GUI header (top bar):

1. **4-Wire Enable Toggle**
   - Button: "OFF" / "ON" (green when enabled)
   - Validates that devices are configured before enabling
   - Starts/stops audio streaming threads

2. **Channel Assignment Dropdown**
   - Shows only enabled channels (CH0-CH9)
   - Selects which LanComm channel to bridge

3. **Configuration Button (⚙)**
   - Opens device configuration dialog

#### Configuration Dialog
Accessed via ⚙ button:

1. **Input Device Section**
   - Dropdown: Lists all available audio input devices
   - Gain Slider: 0-100% (default 80%)
   - Shows channel count for each device

2. **Output Device Section**
   - Dropdown: Lists all available audio output devices
   - Gain Slider: 0-100% (default 80%)
   - Shows channel count for each device

3. **Save/Cancel Buttons**
   - Save: Applies configuration and persists to JSON
   - If 4-wire is running, restarts with new settings

### Configuration File
Settings persist in `intercom_config.json`:

```json
{
  "fourwire_enabled": false,
  "fourwire_input_device": 3,
  "fourwire_output_device": 3,
  "fourwire_channel": 0,
  "fourwire_input_gain": 0.8,
  "fourwire_output_gain": 0.8
}
```

## Operation

### Setup Procedure
1. Connect USB audio interface to base station
2. Connect external comm system to interface (4-wire connection)
3. Open LanComm server GUI
4. Click **⚙** configuration button
5. Select input device (from external system)
6. Select output device (to external system)
7. Adjust input/output gain levels (start at 80%)
8. Click **Save Configuration**
9. Select channel assignment from dropdown
10. Click **ON** to enable 4-wire bridge

### Testing
1. Have someone talk on the external system
2. Verify audio appears on assigned LanComm channel
3. Have LanComm user talk on same channel
4. Verify audio reaches external system
5. Adjust gain levels as needed (prevent clipping/distortion)

### Troubleshooting

#### No Audio Input
- Check device selection in configuration
- Verify external system is sending audio
- Increase input gain slider
- Check USB interface input level/routing

#### No Audio Output
- Check device selection in configuration
- Verify channel has active talkers
- Increase output gain slider
- Check USB interface output level/routing

#### Feedback/Echo
- Verify 4-wire is operating in 2-way mode (not party-line)
- Check external system for local echo settings
- Reduce input/output gain levels
- Ensure proper 4-wire isolation

#### High Latency
- Use low-latency USB interface (ASIO/DirectSound drivers)
- Check system CPU usage
- Close unnecessary applications
- Consider dedicated audio interface hardware

## Integration Examples

### FreeSpeak II Wireless
```
FreeSpeak II Base Station
    ↓ (4-wire port)
USB Audio Interface
    ↓ (USB)
LanComm Server
    ↓ (LAN)
LanComm Beltpacks
```

### Clear-Com Partyline
```
Clear-Com Partyline
    ↓ (via 2-wire to 4-wire converter)
USB Audio Interface
    ↓ (USB)
LanComm Server
```

### Analog Radio/Phone Patch
```
Radio/Phone Hybrid
    ↓ (4-wire audio)
USB Audio Interface
    ↓ (USB)
LanComm Server
```



## Technical Details

### Thread Architecture
- **Main GUI Thread**: Qt event loop, user interactions
- **Async Server Thread**: TCP/UDP network handling
- **Audio Mixer Thread**: Channel mixing, distribution
- **4-Wire Thread**: Dedicated audio I/O loop

### Audio Processing
- **Sample Rate**: 48kHz
- **Chunk Size**: 960 samples (20ms @ 48kHz)
- **Format**: Int16 PCM (network), Float32 (processing)
- **User ID**: -2 (special 4-wire identifier)

### Buffer Management
- Input: Injected into `channel_buffers[fourwire_channel][-2]`
- Output: Tapped from mixed channel before UDP send
- Null routing: 4-wire excludes its own input from output mix
- Jitter buffer: Uses same 6-frame buffer as beltpacks (128ms)

### Performance
- **Latency**: ~40-60ms round-trip (includes interface + processing)
- **CPU Usage**: <1% per 4-wire interface
- **Bandwidth**: Local only (no network overhead)

## Advanced Usage

### Multiple 4-Wire Interfaces
To add multiple interfaces, modify code:
1. Create array of 4-wire configs: `fourwire_configs[0..n]`
2. Duplicate thread/stream management per interface
3. Add GUI tabs or accordion for multiple configs
4. Each interface gets unique negative user ID (-2, -3, -4...)

### Dynamic Channel Switching
4-wire channel can be changed on-the-fly:
1. Select new channel from dropdown
2. System automatically:
   - Removes user ID from old channel's talkers
   - Adds user ID to new channel's talkers
   - Redirects audio buffers
3. No restart required

### Gain Automation
For AGC (Automatic Gain Control):
1. Monitor input audio levels
2. Adjust `fourwire_input_gain` dynamically
3. Target -12dB to -6dB peak levels
4. Prevents clipping and ensures consistent volume





## Safety & Best Practices

### Prevent Feedback Loops
- 4-wire excludes its own audio from output (null routing)
- External system should use proper 4-wire isolation
- Avoid connecting 4-wire output back to input directly

### Audio Levels
- Start with 80% gain on both input and output
- Monitor for clipping (status indicators in future versions)
- Adjust in 5-10% increments
- Peak levels should stay below 0dBFS

### System Integration
- Test 4-wire connection before production use
- Document which channel is assigned for 4-wire
- Train users that external system appears as "always talking"
- Consider dedicated channel for 4-wire (don't share with beltpacks)

### Backup Plan
- Keep external system operational independently
- 4-wire is supplement, not replacement
- Disable 4-wire if causing issues (single button click)




## Future Enhancements
### Hardware Expansion
- GPIO relay control (PTT for external radios)
- Contact closure inputs (signaling from external systems)
- LED status indicators (physical panel LEDs)
- Isolated 4-wire transformer coupling

