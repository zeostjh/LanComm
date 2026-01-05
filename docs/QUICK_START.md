# LanComm Quick Start Guide
**Version**: 2.0  
**Last Updated**: January 5, 2026

## Getting Started (3 Steps)

### 1. Configure Firewall
Run these commands as Administrator in PowerShell:

```powershell
netsh advfirewall firewall add rule name="LanComm Server" dir=in action=allow protocol=TCP localport=6001
netsh advfirewall firewall add rule name="LanComm Audio" dir=in action=allow protocol=UDP localport=6001
```

### 2. Start the Server
```powershell
python server.py
```

You should see:
```
✓ QoS enabled: DSCP AF41 (priority audio)
🌐 mDNS service registered: 192.168.1.10:6001
🚀 Server starting on TCP:6001, UDP:6001
```

### 3. Connect Beltpacks
```powershell
python beltpack.py
```

When connected properly, you'll see:
```
🌐 Server discovered: 192.168.1.10:6001
✓ QoS enabled on beltpack
✓ Authenticated client 192.168.1.100:xxxxx as user_id 0
Connected with user_id 0
```

## Configuration

### Change Authentication Key (Important for Production)

The default key is insecure. Change it before deployment:

**server.py** (line 29):
```python
AUTH_KEY = "your-secure-key-minimum-16-characters"
```

**beltpack.py** (line 104):
```python
AUTH_KEY = "your-secure-key-minimum-16-characters"  # Must match server exactly
```

**Note**: Both keys must match character-for-character or beltpacks won't connect.

### Enable VOX (Optional)

VOX automatically mutes your mic when you're not talking, helping reduce background noise.

**beltpack.py** (line 427):
```python
self.vox_enabled = True  # Change from False
```

Adjust sensitivity if needed (lines 426):
```python
self.vox_gates = [VOXGate(threshold_db=-40, hold_time_ms=500) for _ in range(MAX_NODE_CHANNELS)]

# threshold_db: -40 to -20 (lower = picks up quieter sounds)
# hold_time_ms: 200 to 2000 (how long to stay open after you stop talking)
```

### Network Switch Setup (Optional but Recommended)

If you have a managed network switch, configure it to prioritize audio traffic:

**What you need to do**:
1. Enable QoS/802.1p on your switch
2. Set ports to trust DSCP markings
3. Create a high-priority queue for DSCP 34 (AF41)
4. Turn off Energy Efficient Ethernet (EEE) - it can cause audio dropouts

**For Cisco switches**:
```
mls qos
interface range GigabitEthernet1/0/1-24
 mls qos trust dscp
 priority-queue out
```

If you don't have a managed switch, the system still works fine - you just won't get traffic prioritization.

## Using the System

### Server Interface

**Mixer Tab**: Adjust volume levels for each channel using the faders

**Matrix Tab**: 
- Click "Add User" to create new user profiles
- Assign up to 10 channels per user (hardware supports 4 buttons, but can rotate channels)
- Set button behavior - latch (toggle on/off) or push-to-talk

**Beltpacks Tab**: 
- See all connected devices in real-time
- Push user profiles to specific devices
- Flash LEDs to identify which physical unit is which

### Beltpack Usage

When you first turn on a beltpack:
1. Select your user profile from the list
2. Your assigned channels appear with green LEDs (listening)
3. Press a button to talk - LED turns red
4. Depending on settings:
   - **Latch mode**: Press once to talk, press again to stop
   - **PTT mode**: Hold to talk, release to stop
5. Use volume knobs to adjust how loud each channel is in your headset

## System Capabilities

| What | Maximum | Notes |
|------|---------|-------|
| Users | 20 | Simultaneous connections |
| Channels | 10 | Total system channels |
| Buttons per beltpack | 4 | Physical hardware limit |
| Latency | <50ms | End-to-end audio delay |
| Jitter tolerance | 128ms | Network variation buffer |
| Bandwidth per user | ~768 kbps | When talking on all channels |
| Audio quality | 48kHz 16-bit | Professional broadcast quality |

## Troubleshooting

### "Authentication failed - check AUTH_KEY"
Your beltpack and server have different authentication keys.

**Fix**: Check that the AUTH_KEY in server.py (line 29) matches beltpack.py (line 104) exactly.

### "QoS setup failed (requires admin)"
The server needs admin rights to mark packets for Quality of Service.

**Fix**: Run `python server.py` as Administrator, or configure QoS on your network switch instead. The system works either way - this just optimizes network traffic priority.

### "mDNS discovery timeout, using fallback"
The beltpack can't auto-discover the server on your network.

**Fix**: 
1. Enable "Network Discovery" in Windows network settings
2. Allow UDP port 5353 in your firewall
3. Or just set the server IP manually in beltpack.py (line 97: SERVER_HOST)

### Can't hear other users
Check these in order:
1. Are you both assigned to the same channel?
2. Is the talk button actually pressed? (LED should be red)
3. Is your volume knob turned up?
4. Does the server show active talkers in the status bar?

## Features Explained

### Authentication
Keeps unauthorized users off your system. Uses a shared password with SHA-256 encryption. Default is `lancomm-secure-2025` - **change this before deployment**.

### VOX (Voice-Operated Transmit)
Automatically mutes your mic when you're not talking, reducing background noise. Disabled by default - you can enable it in beltpack.py. When enabled, it opens the mic when you speak and closes it 500ms after you stop.

### QoS (Quality of Service)
Tells your network to prioritize audio packets over regular data. The system marks audio packets with DSCP AF41. If your switch is configured to trust DSCP markings, you'll get better audio quality under network load.

### mDNS Discovery
Lets beltpacks find the server automatically without needing to know the IP address. If it can't find the server in 10 seconds, it falls back to the hardcoded IP in the beltpack.py file.

### Null Routing
Prevents you from hearing your own voice with a delay (which is confusing). The server excludes your audio from the mix it sends back to you. You still hear yourself through local sidetone at 18% volume.

## Performance Tips

### Get the Best Audio Quality
- Use wired Ethernet, not WiFi
- Enable QoS on your network switch if you have one
- Keep network jitter under 50ms (test with `ping -t server_ip`)
- During critical events, minimize other network traffic

### At Full Capacity
20 users each talking on 4 channels = 80 audio streams simultaneously:
- Uses about 60 Mbps bandwidth (no problem for gigabit)
- Server CPU around 10-20% on a quad-core 2GHz processor
- Beltpack CPU around 30-40% on typical SBC hardware

### Reduce Latency Further
- Turn off WiFi power saving on laptops
- Use Cat6 cables instead of Cat5
- Enable jumbo frames (MTU 9000) if all your devices support it
- Configure portfast on your switch ports

## Additional Documentation

- **CHANGES_IMPLEMENTED.md** - What's been added and changed
- **PORT_MIGRATION_GUIDE.md** - If you're upgrading from an older version
- **BELTPACK_HARDWARE.md** - Hardware specs and setup
- **BELTPACK_WIRING.md** - Physical wiring diagrams
- **NETWORK_SETUP.md** - Advanced network configuration
- **4WIRE_INTERFACE.md** - Connecting external systems

## Getting Help

### Save Logs
```powershell
# Capture server output to file
python server.py > server_log.txt 2>&1

# Capture beltpack output to file
python beltpack.py > beltpack_log.txt 2>&1
```

### Check System Status
- Server status bar: Shows connected clients, active talkers, and network ports
- Beltpack display: Shows user profile, channel assignments, and volume levels

### Test Basic Connectivity
```powershell
# From the beltpack machine:
ping 192.168.1.10
telnet 192.168.1.10 6001  # Press Ctrl+C to exit
```
