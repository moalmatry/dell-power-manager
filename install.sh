#!/usr/bin/env bash
#
# Dell Power Manager for Linux - Installer (Poetry Package Manager)
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================================="
echo "         Dell Power Manager for Linux - Installer         "
echo "=========================================================="
echo ""

# Ensure user local bin is in PATH
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

# 1. Check Dependencies
echo "[1/6] Checking system dependencies..."
if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is required."
    exit 1
fi

if ! command -v poetry &>/dev/null; then
    echo "Error: Poetry is required. Please install via: pipx install poetry or sudo apt install python3-poetry."
    exit 1
fi

if ! command -v smbios-battery-ctl &>/dev/null; then
    echo "Installing smbios-utils dependency..."
    sudo apt-get update -qq && sudo apt-get install -y -qq smbios-utils python3-libsmbios
fi

# 2. Setup Poetry environment
echo "[2/6] Building Poetry environment..."
cd "$SCRIPT_DIR"
poetry install

VENV_PATH="$(poetry env info -p)"
if [ -z "$VENV_PATH" ] || [ ! -d "$VENV_PATH" ]; then
    echo "Error: Failed to locate Poetry virtual environment."
    exit 1
fi

# Enable system-site-packages for PyGObject (GTK3) access
if [ -f "$VENV_PATH/pyvenv.cfg" ]; then
    sed -i 's/include-system-site-packages = false/include-system-site-packages = true/' "$VENV_PATH/pyvenv.cfg"
fi

# 3. Install global executables
echo "[3/6] Setting up global executables in /usr/local/bin..."
sudo ln -sf "$VENV_PATH/bin/dell-power" /usr/local/bin/dell-power
sudo ln -sf "$VENV_PATH/bin/dell-power-gui" /usr/local/bin/dell-power-gui
sudo chmod +x /usr/local/bin/dell-power /usr/local/bin/dell-power-gui

# 4. Sudoers permissions for passwordless hardware access
echo "[4/6] Configuring hardware execution permissions..."
sudo bash -c 'cat << "EOF" > /etc/sudoers.d/dell-power-manager
# Dell Power Manager passwordless SMBIOS execution
ALL ALL=(ALL) NOPASSWD: /usr/sbin/smbios-battery-ctl
ALL ALL=(ALL) NOPASSWD: /usr/local/bin/dell-power
EOF'
sudo chmod 0440 /etc/sudoers.d/dell-power-manager

# 5. Desktop Application & Icons
echo "[5/6] Installing desktop launcher & icon..."
sudo mkdir -p /usr/share/icons/hicolor/scalable/apps /usr/share/applications
sudo cp "$SCRIPT_DIR/data/icons/hicolor/scalable/apps/dell-power-manager.svg" /usr/share/icons/hicolor/scalable/apps/
sudo cp "$SCRIPT_DIR/data/dell-power-manager.desktop" /usr/share/applications/

mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps" "$HOME/.local/share/applications"
cp "$SCRIPT_DIR/data/icons/hicolor/scalable/apps/dell-power-manager.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/"
cp "$SCRIPT_DIR/data/dell-power-manager.desktop" "$HOME/.local/share/applications/"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

# 6. Enable systemd boot/resume persistence service
echo "[6/6] Enabling boot/resume persistence service..."
sudo cp "$SCRIPT_DIR/systemd/dell-power.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dell-power.service

# Apply default 50% limit
/usr/local/bin/dell-power limit 50 || true

echo ""
echo "=========================================================="
echo "               Installation Successful!                   "
echo "=========================================================="
echo ""
echo "Dell Power Manager is ready to use!"
echo "  • Open GUI: Search 'Dell Power Manager' in your app menu"
echo "              Or run: dell-power-gui"
echo "  • CLI Commands:"
echo "      dell-power status         # View live battery stats & health"
echo "      dell-power limit 50       # Limit charging to 50% (Max health)"
echo "      dell-power limit 80       # Limit charging to 80% (Longevity)"
echo "      dell-power mode standard  # Charge to 100% normally"
echo "      dell-power custom 50 60   # Custom start & stop percentages"
echo ""
