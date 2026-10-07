# Dell Power Manager for Linux 🔋🛡️

A native, open-source Linux replacement for **Dell Power Manager** built for Dell laptops (Dell G15, Inspiron, XPS, Alienware, Latitude, Precision).

Easily limit battery charging to **50%** (for maximum battery health while plugged into AC) or **80%** (for longevity with mobility), switch charging profiles, monitor live battery health, and control charging thresholds directly via a **native GTK3 graphical interface** or a **fast command-line tool**.

---

## 🌟 Key Features

* **🛡️ Battery Health Charging Limits:**
  * **Limit to 50% (Recommended for Desk/Gaming):** Starts charging below 50%, stops at 55%. Keeps battery chemistry at optimal voltage to prevent cell degradation and swelling.
  * **Limit to 80% (Balanced Daily Use):** Starts charging below 75%, stops at 80%. Ideal balance for portability and longevity.
  * **⚙️ Custom Thresholds:** Set any start percentage (50–95%) and stop percentage (55–100%).
* **🔌 Native Dell SMBIOS Charging Profiles:**
  * **Primarily AC Use:** Dell BIOS hardware mode designed for continuous AC operation.
  * **Adaptive:** Dynamically learns and optimizes charging based on your usage habits.
  * **Standard (100%):** Standard safe full charging to 100%.
  * **ExpressCharge:** Dell high-speed rapid charge to 100%.
* **📊 Live Battery Telemetry:**
  * Real-time battery capacity percentage & progress bar.
  * Health indicator (current capacity vs design capacity).
  * Current power draw in Watts and battery voltage.
  * AC adapter status and cycle count.
* **🖥️ Beautiful GTK3 Interface (`dell-power-gui`):**
  * Sleek UI matching Zorin OS, GNOME, and modern Linux desktops.
  * One-click profile selection and live status feedback.
  * Native desktop launcher with custom Dell Power icon in your app menu.
* **⚡ Persistence Across Reboots:**
  * Includes a systemd service (`dell-power.service`) that automatically re-enforces your chosen charging threshold on boot and resume from sleep/suspend.

---

## 🚀 Quick Installation

### Prerequisites

* Linux kernel 5.x+ / 6.x+
* Python 3.10+
* [Poetry](https://python-poetry.org/) package manager
* `smbios-utils` (Dell SMBIOS user tools)

On Ubuntu / Zorin OS / Debian:
```bash
sudo apt update
sudo apt install -y python3-poetry smbios-utils python3-libsmbios python3-gi
```

### Install with Installer Script

```bash
git clone https://github.com/moalmatry/dell-power-manager.git
cd dell-power-manager
./install.sh
```

The installer will:
1. Build the Poetry environment and dependencies.
2. Symlink global binaries `/usr/local/bin/dell-power` and `/usr/local/bin/dell-power-gui`.
3. Configure passwordless sudoers permissions for hardware SMBIOS calls.
4. Install the desktop launcher and custom SVG icon.
5. Enable the systemd service for boot/resume threshold persistence.
6. Automatically apply the **50% battery health limit**.

---

## 🖥️ Graphical Interface (GUI)

Launch from your desktop application launcher by searching for **"Dell Power Manager"**, or launch from terminal:

```bash
dell-power-gui
```

---

## 💻 Command-Line Interface (CLI)

### View Battery Status & Health
```bash
dell-power status
```

**Example Output:**
```text
=======================================================
           Dell Power Manager - Battery Status          
=======================================================
  Level:      [███████████████████░░░░░░░░░░░] 65%
  State:      Charging
  Power:      10.27 W @ 11.59 V
  AC Adapter: Connected (Online)
-------------------------------------------------------
  Health:     45.9% (3466 / 7544 mAh)
  Cycles:     0
-------------------------------------------------------
  Active Profile: 🛡️  Custom Limit (Start: 50%, Stop: 55%)
=======================================================
```

### Limit Charging to 50% (Maximum Longevity)
```bash
dell-power limit 50
```

### Limit Charging to 80% (Balanced Daily Use)
```bash
dell-power limit 80
```

### Set Custom Start & Stop Thresholds
```bash
dell-power custom 50 60
```
*(Start must be between 50–95%, Stop between 55–100%, and Stop must be at least 5% higher than Start).*

### Set Predefined Charging Profile
```bash
dell-power mode primarily_ac   # Optimized for laptops mostly plugged in
dell-power mode standard       # Full 100% normal charge
dell-power mode adaptive       # Auto-adapting
dell-power mode express        # Dell ExpressCharge fast charging
```

---

## 🔄 Service & Persistence

The systemd service keeps your preferred charging limit active even after reboots, shut downs, and sleep/suspend events:

```bash
# Check service status
systemctl status dell-power.service

# Manually trigger re-application
dell-power apply
```

---

## 🛠️ Uninstallation

To cleanly remove Dell Power Manager:
```bash
cd dell-power-manager
./uninstall.sh
```

---

## 📜 License

MIT License. Copyright (c) 2026 Mohamed Almatry.
