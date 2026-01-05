# LanComm Beltpack Hardware Recommendations
**Date**: December 21, 2025  
**Purpose**: Professional SBC selection for IP intercom beltpacks

---

## 🎯 Requirements Summary

Your beltpack needs:
- ✅ **PoE Power**: 802.3af (15.4W) or 802.3at (25.5W)
- ✅ **Audio I/O**: 48kHz 16-bit, low-latency (<10ms codec delay)
- ✅ **GPIO**: 4+ pins for RGB button control
- ✅ **I2C Bus**: For Gravity RGB LED buttons (addresses 0x23-0x26)
- ✅ **SPI or ADC**: For 4 volume rotary encoders
- ✅ **CPU**: ARM Cortex-A53+ quad-core for real-time audio mixing
- ✅ **RAM**: 1GB minimum (2GB+ recommended for PyQt6 GUI)
- ✅ **Network**: Gigabit Ethernet with PoE
- ✅ **Display**: HDMI or DSI for 3" OLED touchscreen (480×320)

---

## 🏆 Top Recommendations (Ranked)

### 1. **Orange Pi 5 Pro (16GB) + Waveshare PoE HAT** ⭐⭐⭐⭐⭐
**SELECTED PLATFORM - Best Performance with Built-in Audio**

#### Specs
- **CPU**: Rockchip RK3588S, Octa-core (4× Cortex-A76 @ 2.4GHz + 4× Cortex-A55 @ 1.8GHz)
- **RAM**: 16GB LPDDR4X (massive headroom for audio processing)
- **Network**: 2.5 Gigabit Ethernet (2.5× faster than Raspberry Pi)
- **GPIO**: 40-pin header (Raspberry Pi compatible pinout)
- **Audio**: **Built-in ES8388 codec** (no external HAT needed!)
- **PoE**: Waveshare PoE HAT (802.3af/at, up to 25.5W)
- **Size**: 100×72mm

#### Pros
✅ **Built-in professional audio codec** - ES8388 stereo I/O, 48kHz native, <5ms latency  
✅ **No audio HAT needed** - Saves cost, complexity, and GPIO conflicts  
✅ **8-core powerhouse** - 2× the cores of RPi 4, better real-time audio  
✅ **2.5Gb Ethernet** - Native 2.5× faster network throughput  
✅ **16GB RAM** - Runs PyQt6 GUI smoothly with audio processing  
✅ **PCIe M.2** - Can add NVMe SSD for OS and logging  
✅ **Better thermals** - Large heatsink, no throttling under load  

#### Cons
❌ Higher cost than Raspberry Pi (~$130 vs $55)  
❌ Smaller community than RPi (but growing fast)  
❌ Waveshare PoE HAT requires separate purchase  

#### Cost Breakdown
- **Orange Pi 5 Pro (16GB)**: $110
- **Waveshare PoE HAT**: $20-25
- **Total**: ~$135 (vs $75 for RPi 4 + PoE HAT + Audio HAT)

---

### 2. **Raspberry Pi 4 Model B (2GB/4GB) + PoE HAT** ⭐⭐⭐⭐
**Budget Alternative - Requires Audio HAT**

#### Specs
- **CPU**: Broadcom BCM2711, Quad-core Cortex-A72 @ 1.5GHz
- **RAM**: 2GB or 4GB LPDDR4
- **Network**: Gigabit Ethernet (full speed, not USB-limited like Pi 3)
- **GPIO**: 40-pin header (28 usable GPIO)
- **Audio**: PWM stereo + I2S for pro audio HATs (requires HiFiBerry or similar)
- **PoE**: Official PoE HAT (802.3af, 15.4W max)
- **Size**: 85×56mm (credit card size)

#### Pros
✅ **Best software support** - Massive community, tons of tutorials  
✅ **Proven reliability** - Used in thousands of production systems  
✅ **Excellent audio HATs** - HiFiBerry, IQaudio, Adafruit I2S  
✅ **Official PoE HAT** - $20, plug-and-play, includes fan  
✅ **Python optimized** - NumPy/PyAudio run great  
✅ **Long-term availability** - Production guaranteed until 2026+  

#### Cons
❌ Requires PoE HAT (adds $20 + height)  
❌ **Requires audio HAT** (adds $20-30 + complexity)  
❌ Slower CPU than Orange Pi 5 Pro  
❌ Only 1Gb Ethernet (not 2.5Gb)  

#### Cost Breakdown
- **Pi 4 Model B (2GB)**: $35
- **Official PoE HAT**: $20
- **HiFiBerry DAC+ Zero**: $20
- **Audio HAT** (optional): $15-40
- **Case**: $10
- **Total**: **~$80-105**

#### Recommended Audio HAT
**HiFiBerry DAC+ Zero** ($15):
- 24-bit/192kHz DAC
- Line out + headphone jack
- I2S interface (no USB latency)
- Compact, sits on GPIO header
- Perfect for 48kHz intercom audio

---

### 2. **Raspberry Pi 5 (4GB) + PoE HAT** ⭐⭐⭐⭐⭐
**Most Powerful - Future-Proof**

#### Specs
- **CPU**: Broadcom BCM2712, Quad-core Cortex-A76 @ 2.4GHz
- **RAM**: 4GB or 8GB LPDDR4X
- **Network**: Gigabit Ethernet (dedicated MAC, not USB)
- **GPIO**: 40-pin header (backward compatible)
- **Audio**: I2S for HATs
- **PoE**: New PoE+ HAT (802.3at, 25.5W)
- **Size**: 85×56mm

#### Pros
✅ **3x faster than Pi 4** - Overkill for audio, but handles PyQt6 GUI smoothly  
✅ **PCIe support** - Can add high-end audio cards via M.2  
✅ **Better thermals** - Less throttling under load  
✅ **USB 3.0 hub** - No more bandwidth bottlenecks  
✅ **Official PoE+ HAT** - More power for peripherals  

#### Cons
❌ **More expensive** ($60 board + $25 PoE HAT)  
❌ **Overkill for audio** (Pi 4 is sufficient)  
❌ **Higher power draw** (may need 802.3at PoE switch)  

#### Cost
- **Pi 5 (4GB)**: $60
- **PoE+ HAT**: $25
- **Audio HAT**: $15-40
- **Total**: **~$100-125**

**Verdict**: Choose if you want **maximum headroom** for future features (OPUS codec, GUI effects, etc.).

---

### 3. **Radxa Rock Pi 4 Model C Plus** ⭐⭐⭐⭐
**PoE Onboard - No HAT Needed**

#### Specs
- **CPU**: Rockchip RK3399, Hexa-core (A72×2 + A53×4) @ 2.0GHz
- **RAM**: 4GB LPDDR4
- **Network**: Gigabit Ethernet with **native PoE** (802.3af)
- **GPIO**: 40-pin Raspberry Pi compatible
- **Audio**: I2S + SPDIF
- **PoE**: **Built-in PoE module** (no HAT needed!)
- **Size**: 85×56mm

#### Pros
✅ **Native PoE onboard** - No HAT required, cleaner design  
✅ **Powerful CPU** - Faster than Pi 4  
✅ **4GB RAM standard** - Great for multitasking  
✅ **PCIe M.2 slot** - Add NVMe SSD or audio card  
✅ **Pi-compatible GPIO** - Use Pi HATs and tutorials  

#### Cons
❌ **Less software support** than Raspberry Pi  
❌ **Armbian/Ubuntu required** (not Raspberry Pi OS)  
❌ **Harder to find** in stock  
❌ **Power draw** (~6W, close to PoE limit)  

#### Cost
- **Rock Pi 4C Plus (4GB + PoE)**: $75
- **Audio HAT**: $15-40
- **Total**: **~$90-115**

**Verdict**: **Best value** if you want native PoE without extra HATs.

---

### 4. **Orange Pi 5 Plus** ⭐⭐⭐⭐
**Extreme Performance - Overkill but Cheap**

#### Specs
- **CPU**: Rockchip RK3588, Octa-core (A76×4 + A55×4) @ 2.4GHz
- **RAM**: 4GB/8GB/16GB LPDDR4X
- **Network**: 2.5Gb Ethernet (no native PoE)
- **GPIO**: 40-pin header
- **Audio**: I2S + HDMI audio
- **PoE**: **Requires PoE splitter** (USB-C PD)
- **Size**: 100×62mm (larger)

#### Pros
✅ **Insanely powerful** - Desktop-class CPU  
✅ **Cheap for specs** ($60 for 4GB)  
✅ **2.5Gb Ethernet** - Future-proof bandwidth  
✅ **PCIe 3.0 x4** - Pro audio cards possible  

#### Cons
❌ **No native PoE** (need splitter)  
❌ **Overkill** (wastes power/money)  
❌ **Larger size** (harder to fit in belt pack)  
❌ **Higher power draw** (~10W)  

#### Cost (with PoE)
- **Orange Pi 5 (4GB)**: $60
- **PoE to USB-C splitter**: $15-25
- **Audio HAT**: $15-40
- **Total**: **~$90-125**

**Verdict**: Only if you need **extreme processing** for OPUS encoding or 20+ channel local mixing.

---

### 5. **Radxa Rock Pi S (Your Current Choice)** ⭐⭐⭐
**Ultra-Compact but Limited**

#### Specs
- **CPU**: Rockchip RK3308, Quad-core Cortex-A35 @ 1.3GHz
- **RAM**: 256MB/512MB DDR3
- **Network**: 100Mb Ethernet (optional PoE module)
- **GPIO**: 26-pin header
- **Audio**: Built-in codec (48kHz), I2S
- **PoE**: Optional module (802.3af)
- **Size**: 42×42mm (tiny!)

#### Pros
✅ **Smallest size** - Easy to fit in compact belt pack  
✅ **Built-in audio codec** - No HAT needed  
✅ **Low power** (~2W, well under PoE limit)  
✅ **PoE option available** ($10 module)  
✅ **Cheap** ($15-25)  

#### Cons
❌ **Weak CPU** - A35 cores struggle with real-time mixing  
❌ **Limited RAM** - 512MB barely runs Python + GUI  
❌ **100Mb Ethernet** - Bottleneck for 10 channels  
❌ **Small community** - Less support  
❌ **Audio quality** - Onboard codec is "okay" not great  

#### Cost
- **Rock Pi S (512MB)**: $25
- **PoE module**: $10
- **Total**: **~$35**

**Verdict**: **Not recommended** for professional use. RAM and CPU are too weak for PyQt6 + real-time audio mixing + 10 channels. **Use for prototyping only.**

---

### 6. **Raspberry Pi Compute Module 4 (CM4) + Carrier Board** ⭐⭐⭐⭐⭐
**Industrial/Professional Choice**

#### Specs (CM4 Lite 2GB)
- **CPU**: Same as Pi 4 (BCM2711, Quad A72 @ 1.5GHz)
- **RAM**: 1GB/2GB/4GB/8GB options
- **Network**: Via carrier board (Gigabit + PoE)
- **GPIO**: Exposed via carrier board
- **Audio**: I2S via carrier board
- **PoE**: Depends on carrier board
- **Size**: 55×40mm (module), carrier varies

#### Pros
✅ **Industrial-grade** - Designed for embedded products  
✅ **Custom carrier boards** - Many with native PoE  
✅ **Compact when integrated** - Module is tiny  
✅ **Reliable** - Used in commercial products  
✅ **Same software as Pi 4** - Full compatibility  

#### Cons
❌ **Requires carrier board** - Extra cost/complexity  
❌ **More expensive** ($40 module + $50-100 carrier)  
❌ **Harder to prototype** - Not breadboard-friendly  

#### Recommended Carrier Board
**Waveshare CM4-PoE-UPS-BASE (C)** ($60):
- Native PoE (802.3af)
- USB 2.0 + Ethernet
- GPIO breakout
- UPS battery backup option
- Compact (90×56mm)

#### Cost
- **CM4 Lite 2GB/Wireless**: $40
- **Carrier with PoE**: $60
- **Audio codec board**: $15
- **Total**: **~$115**

**Verdict**: **Best for production units** if you're building >10 belt packs. Requires more integration work.

---

## 📊 Quick Comparison Table

| Model | CPU | RAM | PoE | Audio | Size | Cost | Score |
|-------|-----|-----|-----|-------|------|------|-------|
| **Pi 4 + PoE HAT** | A72×4 1.5GHz | 2GB | HAT | I2S HAT | 85×56mm | $80-105 | ⭐⭐⭐⭐⭐ |
| **Pi 5 + PoE HAT** | A76×4 2.4GHz | 4GB | HAT | I2S HAT | 85×56mm | $100-125 | ⭐⭐⭐⭐⭐ |
| **Rock Pi 4C+** | A72/A53 | 4GB | **Native** | I2S HAT | 85×56mm | $90-115 | ⭐⭐⭐⭐ |
| **Orange Pi 5** | A76/A55 | 4GB | Splitter | I2S HAT | 100×62mm | $90-125 | ⭐⭐⭐⭐ |
| **Rock Pi S** | A35×4 1.3GHz | 512MB | Module | Onboard | 42×42mm | $35 | ⭐⭐⭐ |
| **CM4 + Carrier** | A72×4 1.5GHz | 2GB | Native | I2S | 90×56mm | $115 | ⭐⭐⭐⭐⭐ |

---

## 🎯 Final Recommendation

### **For Professional Deployment: Raspberry Pi 4 (2GB) + Official PoE HAT + HiFiBerry DAC**

**Why?**
1. ✅ **Proven reliability** in production systems
2. ✅ **Best community support** (critical for troubleshooting)
3. ✅ **Excellent audio quality** with HiFiBerry
4. ✅ **Sufficient power** for real-time mixing + PyQt6 GUI
5. ✅ **Long-term availability** (not EOL anytime soon)
6. ✅ **Reasonable cost** ($80-105 per unit)

**Performance Headroom**:
- CPU: 30-40% usage under full load (plenty of room)
- RAM: 2GB is enough for Python + PyQt6 + 10 audio channels
- Network: Gigabit handles 60 Mbps peak (20 users × 10 channels)
- Audio: <5ms total latency (PyAudio + I2S HAT)

---

### **If Native PoE is Critical: Radxa Rock Pi 4C Plus**

**Why?**
1. ✅ **No PoE HAT needed** - cleaner design, lower profile
2. ✅ **More powerful than Pi 4** (hexa-core)
3. ✅ **4GB RAM standard** - better multitasking
4. ✅ **Pi-compatible GPIO** - use Pi tutorials/HATs

**Trade-off**: Less software support, but Armbian works well.

---

### **If Budget is Tight: Raspberry Pi 4 (2GB) + Generic PoE Splitter**

Instead of Official PoE HAT, use a **PoE splitter**:
- **TP-Link TL-PoE10R** ($15): PoE to 5V micro-USB
- **Pros**: Saves $5, no height increase
- **Cons**: External adapter (less integrated)

**Total Cost**: $35 (Pi) + $15 (splitter) + $15 (audio HAT) = **$65**

---

## 🔧 Audio HAT Recommendations

### **Budget: HiFiBerry DAC+ Zero** ($15)
- 24-bit/192kHz capable
- Low latency I2S
- Headphone + line out
- Compact (mounts on GPIO)

### **Mid-Range: Adafruit I2S Audio Bonnet** ($25)
- Stereo 24-bit/48kHz
- Built-in amp (3W per channel)
- Direct speaker connection
- MEMS mic input option

### **Professional: IQaudio Codec Zero** ($30)
- Full-duplex codec (ADC + DAC)
- 48kHz native
- Mic preamp + phantom power
- Professional XLR connectors possible

### **Onboard Audio (Not Recommended)**
- Pi 4 has PWM audio via 3.5mm jack
- **Quality**: Poor (audible hiss, distortion)
- **Latency**: 20-40ms additional buffering
- **Use only for testing**, not production

---

## ⚡ Power Considerations

### PoE Power Budget
- **802.3af** (PoE): 15.4W at PSE, **12.95W at PD** (after cable loss)
- **802.3at** (PoE+): 25.5W at PSE, **21.90W at PD**

### Typical Consumption
| Component | Power Draw |
|-----------|------------|
| Raspberry Pi 4 | 3.0-5.0W (idle-load) |
| PoE HAT | 1.0-2.0W (conversion loss) |
| Audio HAT | 0.5-1.0W |
| OLED Display | 0.5-1.0W |
| USB Accessories | 0.5-2.0W |
| **Total** | **5.5-11.0W** |

**Verdict**: 802.3af (15.4W PoE) is sufficient. Use PoE+ only if adding USB peripherals (camera, etc.).

---

## 🛠️ Assembly Tips

### Pi 4 + PoE HAT Stack
1. Mount PoE HAT on Pi 4 GPIO (includes spacers)
2. Connect 4-pin fan header (HAT has fan for cooling)
3. Mount audio HAT on remaining GPIO pins (requires stacking header)
4. Use **stacking header** to expose GPIO for buttons/encoders

### GPIO Pin Allocation (After HATs)
- **I2S Audio**: GPIO 18,19,20,21 (used by HAT)
- **I2C Buttons**: GPIO 2,3 (SDA/SCL)
- **SPI Encoders**: GPIO 7-11 (MOSI/MISO/SCLK/CE)
- **Remaining GPIO**: 4,5,6,12-17,22-27 for RGB button control

---

## 📦 Bill of Materials (Final Recommendation)

### Professional Beltpack BOM
| Item | Qty | Unit Cost | Total |
|------|-----|-----------|-------|
| Raspberry Pi 4 Model B (2GB) | 1 | $35 | $35 |
| Official PoE HAT | 1 | $20 | $20 |
| HiFiBerry DAC+ Zero | 1 | $15 | $15 |
| Gravity I2C RGB LED Button × 4 | 4 | $8 | $32 |
| Rotary Encoder (EC11) × 4 | 4 | $2 | $8 |
| 3" OLED Touchscreen (SPI) | 1 | $25 | $25 |
| Headset Jack (4-pole TRRS) | 1 | $3 | $3 |
| Enclosure (custom 3D print) | 1 | $10 | $10 |
| Micro-SD Card 16GB | 1 | $8 | $8 |
| **Total per Unit** | | | **$156** |

**Volume Discount** (20+ units): ~$120-130 per unit

---

## 🚀 Alternative: Use Commercial PoE Audio Endpoint

If DIY complexity is too high, consider:

### **Grandstream GXV3380** (Android Video Phone)
- **Native PoE**: 802.3af
- **Built-in Audio**: High-quality codec
- **Touchscreen**: 16:9 display
- **Android OS**: Run custom app
- **Cost**: ~$200
- **Pros**: Professional audio, reliable hardware
- **Cons**: Overkill for intercom, expensive

### **Fanvil i12** (SIP Audio Endpoint)
- **Native PoE**: 802.3af
- **Built-in Audio**: Headset jack
- **Button Array**: 12 programmable buttons
- **SIP Stack**: Can repurpose for custom protocol
- **Cost**: ~$80
- **Pros**: Purpose-built for comms
- **Cons**: Requires SIP stack modification

---

## 💡 Prototype Recommendation

**For initial testing/development:**
1. Use **Raspberry Pi 4 (2GB)** with **USB PoE splitter** ($50 total)
2. Use **onboard 3.5mm audio** (PWM) for testing ($0)
3. Simulate buttons via keyboard/mouse ($0)
4. Run GUI on HDMI monitor ($0)

**Upgrade to production hardware** once software is proven:
- Add Official PoE HAT
- Add HiFiBerry audio HAT
- Add Gravity RGB buttons
- Add rotary encoders
- Add compact OLED display

---

## ❓ FAQ

**Q: Why not use ESP32 for lower cost?**  
A: ESP32 lacks processing power for:
- PyQt6 GUI (needs Linux)
- Real-time audio mixing (10 channels)
- Python runtime overhead

**Q: Can I use USB audio instead of I2S HAT?**  
A: Yes, but:
- Higher latency (USB polling adds 5-20ms)
- CPU overhead (USB stack + audio driver)
- Less reliable (USB dropouts under load)

**Q: What about Raspberry Pi 3?**  
A: Not recommended:
- Slower CPU (bottleneck for mixing)
- USB 2.0 limits Ethernet to 300 Mbps (shared bus)
- Only 1GB RAM (tight for PyQt6)

**Q: Do I need eMMC storage?**  
A: No, micro-SD is fine for read-only OS. Use industrial-grade card (SanDisk High Endurance).

---

**Final Answer**: **Raspberry Pi 4 (2GB) + Official PoE HAT + HiFiBerry DAC+ Zero** is your best bet for professional, reliable, well-supported beltpack hardware at $80-105 per unit.

---

*Hardware guide generated December 21, 2025*
