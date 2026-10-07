#!/usr/bin/env bash
#
# Dell Power Manager Uninstaller
#
set -e

echo "Uninstalling Dell Power Manager..."

sudo systemctl disable --now dell-power.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/dell-power.service
sudo systemctl daemon-reload

sudo rm -f /usr/local/bin/dell-power /usr/local/bin/dell-power-gui
sudo rm -f /etc/sudoers.d/dell-power-manager
sudo rm -f /usr/share/applications/dell-power-manager.desktop
sudo rm -f /usr/share/icons/hicolor/scalable/apps/dell-power-manager.svg
rm -f "$HOME/.local/share/applications/dell-power-manager.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/dell-power-manager.svg"
sudo rm -rf /etc/dell-power

echo "Dell Power Manager uninstalled successfully."
