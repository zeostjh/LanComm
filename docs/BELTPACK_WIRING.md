# LanComm Pro Beltpack Wiring Diagram
**Platform**: Raspberry Pi 4 Model B (2GB) + Official PoE HAT + HiFiBerry DAC+ Zero  
**Updated**: December 21, 2025

## ⚠️ CRITICAL: I2S Audio HAT Pin Reservation

The **HiFiBerry DAC+ Zero** uses these GPIO pins for I2S audio:  
- **GPIO 18**: I2S Bit Clock (BCK) - **RESERVED**
- **GPIO 19**: I2S Word Select (LRCK) - **INPUT OK** (safe for rotary encoder DT)
- **GPIO 20**: I2S Data In (DIN) - **RESERVED**
- **GPIO 21**: I2S Data Out (DOUT) - **RESERVED**

**DO NOT connect other devices to GPIO 18, 20, or 21**. All encoder wiring below avoids these pins.

---

# Raspberry Pi 4 GPIO Pinout Reference

```
     3.3V  (1) (2)  5V
    GPIO2  (3) (4)  5V          ← I2C SDA
    GPIO3  (5) (6)  GND         ← I2C SCL
    GPIO4  (7) (8)  GPIO14
      GND  (9) (10) GPIO15
   GPIO17 (11) (12) GPIO18 ⚠️ I2S BCK
   GPIO27 (13) (14) GND
   GPIO22 (15) (16) GPIO23
     3.3V (17) (18) GPIO24
   GPIO10 (19) (20) GND
    GPIO9 (21) (22) GPIO25
   GPIO11 (23) (24) GPIO8
      GND (25) (26) GPIO7
    GPIO0 (27) (28) GPIO1
    GPIO5 (29) (30) GND
    GPIO6 (31) (32) GPIO12
   GPIO13 (33) (34) GND
   GPIO19 (35) (36) GPIO16 ⚠️ I2S LRCK (INPUT OK)
   GPIO26 (37) (38) GPIO20 ⚠️ I2S DIN
      GND (39) (40) GPIO21 ⚠️ I2S DOUT
```

---

## I2C Bus (RGB LED Buttons)

```
SBC I2C Bus 1 (pins 3 & 5 on Raspberry Pi/Radxa)
│
├─ 0x23 ─ Gravity RGB LED Button Module #1 (Channel 1)
├─ 0x24 ─ Gravity RGB LED Button Module #2 (Channel 2)
├─ 0x25 ─ Gravity RGB LED Button Module #3 (Channel 3)
└─ 0x26 ─ Gravity RGB LED Button Module #4 (Channel 4)

Notes:
- SDA: Data line (pull-up 4.7kΩ to 3.3V)
- SCL: Clock line (pull-up 4.7kΩ to 3.3V)
- VCC: 3.3V or 5V (check module spec)
- GND: Common ground
```

## GPIO (Volume Rotary Encoders)

**Updated Pin Assignments** (avoiding I2S: GPIO 18, 20, 21)

```
Volume Encoder 1 (Channel 1):
├─ CLK → GPIO 5  (Pin 29)
├─ DT  → GPIO 6  (Pin 31)
└─ GND → Ground  (Pin 30)

Volume Encoder 2 (Channel 2):
├─ CLK → GPIO 13 (Pin 33)
├─ DT  → GPIO 19 (Pin 35) ⚠️ I2S pin but safe for INPUT
└─ GND → Ground  (Pin 34)

Volume Encoder 3 (Channel 3):
├─ CLK → GPIO 26 (Pin 37)
├─ DT  → GPIO 12 (Pin 32)
└─ GND → Ground  (Pin 39)

Volume Encoder 4 (Channel 4):
├─ CLK → GPIO 16 (Pin 36)
├─ DT  → GPIO 7  (Pin 26)
└─ GND → Ground  (Pin 25)
└─ GND → Ground

Volume Encoder 3 (Channel 3):
├─ CLK → GPIO 26
├─ DT → GPIO 20
└─ GND → Ground

Volume Encoder 4 (Channel 4):
├─ CLK → GPIO 21
├─ DT → GPIO 16
└─ GND → Ground

Notes:
- CLK: Clock output A
- DT: Data output B
- Common pin: Ground
- Optional: Pull-up resistors if encoder doesn't have them
```

## GPIO (Menu Rotary Encoder)

```
Menu Encoder with Push Button:
├─ CLK → GPIO 17
├─ DT → GPIO 27
├─ SW → GPIO 22 (push button, active low)
└─ GND → Ground

Notes:
- SW pin goes LOW when button pressed
- Internal pull-up configured in software
```

## Audio Interface

```
USB Audio Adapter or I2S Interface:
├─ Microphone Input (mono, 48kHz, 16-bit)
└─ Headphone/Speaker Output (mono, 48kHz, 16-bit)

Recommended:
- USB Audio: Standard USB soundcard
- I2S Audio: PCM5102 DAC + MAX9814 Mic Amp
```

## Network Interface

```
Ethernet (Recommended):
- 100Mbps or 1Gbps Ethernet
- PoE+ support (IEEE 802.3at) for single-cable deployment

Wi-Fi (Optional):
- 802.11ac or better
- Not recommended for production (latency/reliability)
```

## Power Supply

```
Option 1: PoE+ (Recommended)
- IEEE 802.3at (25.5W)
- Single cable for power + data
- No external power adapter needed

Option 2: USB-C PD
- 5V 3A (15W) minimum
- Separate from Ethernet

Option 3: DC Barrel Jack
- 5V 3A regulated supply
- 2.1mm x 5.5mm jack
```

## Complete Pin Map (Raspberry Pi Header)

```
Pin 1  (3.3V)    ─ Power for encoders/buttons
Pin 2  (5V)      ─ (Not used or for Gravity modules if 5V)
Pin 3  (SDA1)    ─ I2C Data (RGB buttons)
Pin 4  (5V)      ─ (Not used)
Pin 5  (SCL1)    ─ I2C Clock (RGB buttons)
Pin 6  (GND)     ─ Ground
Pin 7  (GPIO 4)  ─ (Reserved)
Pin 8  (GPIO 14) ─ (Reserved for UART TX)
Pin 9  (GND)     ─ Ground
Pin 10 (GPIO 15) ─ (Reserved for UART RX)
Pin 11 (GPIO 17) ─ Menu Encoder CLK
Pin 12 (GPIO 18) ─ (Reserved for I2S audio)
Pin 13 (GPIO 27) ─ Menu Encoder DT
Pin 14 (GND)     ─ Ground
Pin 15 (GPIO 22) ─ Menu Encoder SW (button)
Pin 16 (GPIO 23) ─ (Reserved)
Pin 17 (3.3V)    ─ Power
Pin 18 (GPIO 24) ─ (Reserved)
Pin 19 (GPIO 10) ─ (SPI MOSI - not used)
Pin 20 (GND)     ─ Ground
Pin 21 (GPIO 9)  ─ (SPI MISO - not used)
Pin 22 (GPIO 25) ─ (Reserved)
Pin 23 (GPIO 11) ─ (SPI SCLK - not used)
Pin 24 (GPIO 8)  ─ (SPI CE0 - not used)
Pin 25 (GND)     ─ Ground
Pin 26 (GPIO 7)  ─ (SPI CE1 - not used)
Pin 27 (ID_SD)   ─ (HAT EEPROM - not used)
Pin 28 (ID_SC)   ─ (HAT EEPROM - not used)
Pin 29 (GPIO 5)  ─ Volume Encoder 1 CLK
Pin 30 (GND)     ─ Ground
Pin 31 (GPIO 6)  ─ Volume Encoder 1 DT
Pin 32 (GPIO 12) ─ (Reserved)
Pin 33 (GPIO 13) ─ Volume Encoder 2 CLK
Pin 34 (GND)     ─ Ground
Pin 35 (GPIO 19) ─ Volume Encoder 2 DT
Pin 36 (GPIO 16) ─ Volume Encoder 4 DT
Pin 37 (GPIO 26) ─ Volume Encoder 3 CLK
Pin 38 (GPIO 20) ─ Volume Encoder 3 DT
Pin 39 (GND)     ─ Ground
Pin 40 (GPIO 21) ─ Volume Encoder 4 CLK
```

## Bill of Materials (BOM)

### Core Components
| Qty | Part | Description | Source |
|-----|------|-------------|--------|
| 1 | SBC | Radxa Rock Pi S or Raspberry Pi 4B | Amazon/AliExpress |
| 4 | RGB Button | Gravity I2C RGB LED Button Module (DFRobot SEN0409) | DFRobot |
| 4 | Rotary Encoder | EC11 Rotary Encoder (20 detents, 20mm) | Amazon |
| 1 | Menu Encoder | EC11 with Push Button | Amazon |
| 1 | USB Audio | USB Sound Card (CM108/CM119 chipset) | Amazon |
| 4 | Knob | Aluminum knob 6mm shaft | Amazon |
| 1 | Enclosure | ABS/Aluminum case (~150x100x50mm) | Amazon |
| 1 | Ethernet Cable | Cat6 cable with RJ45 connector | Amazon |
| 1 | PoE Splitter | 5V 2.4A PoE splitter (if using PoE) | Amazon |

### Optional Components
| Qty | Part | Description | Source |
|-----|------|-------------|--------|
| 1 | Screen | 3" HDMI display (for GUI) | Amazon |
| 1 | Belt Clip | Heavy duty spring clip | Amazon |
| 1 | XLR Jack | 4-pin XLR for headset | Neutrik |
| 4 | Pull-up Resistor | 4.7kΩ 1/4W (if needed for I2C) | Mouser |

### Cables & Connectors
| Qty | Part | Description |
|-----|------|-------------|
| 1 | Dupont Cables | Female-to-female 20cm (40-pack) |
| 1 | Heat Shrink | 2:1 ratio assortment |
| 1 | Cable Strain Relief | Rubber grommet |

## Assembly Notes

1. **I2C Bus Setup**
   - Enable I2C in raspi-config or device tree
   - Install: `apt-get install i2c-tools python3-smbus`
   - Test: `i2cdetect -y 1` (should show 0x23-0x26)

2. **GPIO Setup**
   - Install: `apt-get install python3-gpiod`
   - No device tree changes needed (standard GPIO)

3. **Audio Setup**
   - USB: Auto-detected by PyAudio
   - I2S: Requires device tree overlay

4. **Network Setup**
   - Static IP recommended: `192.168.1.100-199`
   - Server IP configured in beltpack.py line 36
   - Subnet: 255.255.255.0

5. **Testing Procedure**
   - Power on SBC
   - Check I2C devices: `i2cdetect -y 1`
   - Run beltpack.py: `python3 beltpack.py`
   - Select user profile from GUI
   - Test each button (should light up red/green)
   - Test volume knobs (adjust encoder values)
   - Test flash command from server

## Troubleshooting

**Issue**: RGB buttons not detected
- Check I2C wiring (SDA, SCL, GND, VCC)
- Verify I2C enabled: `ls /dev/i2c*`
- Check addresses: `i2cdetect -y 1`
- Try different I2C bus speed: Add `dtparam=i2c_arm_baudrate=50000` to /boot/config.txt

**Issue**: Rotary encoders not working
- Check GPIO wiring
- Verify gpiod installed: `gpioinfo`
- Test GPIO access: `gpioget gpiochip0 5`
- Check for GPIO conflicts

**Issue**: No audio
- Check USB audio detected: `arecord -l` and `aplay -l`
- Test PyAudio: `python3 -m pyaudio`
- Verify ALSA config: `aplay -L`

**Issue**: Flash command not received
- Check TCP connection: `netstat -an | grep 5000`
- Verify server IP in beltpack.py
- Check firewall rules

## Production Deployment

**Enclosure Layout**:
```
┌─────────────────────────────────┐
│   LanComm Pro Beltpack V1.0     │ ← Label
├─────────────────────────────────┤
│  [🔴] [🔴] [🔴] [🔴]            │ ← RGB LED Buttons (talk/listen)
│  CH1   CH2   CH3   CH4          │
│                                 │
│  [⟳]  [⟳]  [⟳]  [⟳]           │ ← Volume Knobs
│                                 │
│  ╔═══════════╗         [⟳]     │ ← Screen + Menu Encoder
│  ║ User: Bob ║                 │
│  ║ CH1: Main ║                 │
│  ║ CH2: Tech ║                 │
│  ╚═══════════╝                 │
│                                 │
│  [RJ45]                         │ ← Ethernet Port
└─────────────────────────────────┘
     ║                               ← Belt Clip (back)
```

**Startup Sequence**:
1. Power on via PoE or USB-C
2. SBC boots Linux (~15 seconds)
3. beltpack.py auto-starts (systemd service)
4. GUI shows user selection screen
5. User taps their name or uses menu encoder
6. Main screen shows channel status
7. RGB buttons show green (listening mode)
8. Press button to talk (red LED)

**Maintenance**:
- LED brightness: Adjust in RGBButton.set_color() (0-255 per channel)
- Volume curve: Modify RotaryEncoder min/max values
- Button debounce: Adjust hardware_poll() sleep time
- Flash pattern: Edit HardwareManager._flash_sequence()
