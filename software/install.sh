#!/usr/bin/env bash
# Installs the Pi Heart-Sound Shaker player on Raspberry Pi OS.
# Usage (from this folder):  sudo bash install.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo bash install.sh" >&2
  exit 1
fi

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST=/opt/heart-shaker
RUN_USER="${SUDO_USER:-pi}"

echo "==> Installing packages"
apt-get update -qq
apt-get install -y -qq python3-gpiozero alsa-utils

echo "==> Copying player to $DEST"
install -d "$DEST/sounds"
install -m 755 "$SRC/heart_player.py" "$DEST/heart_player.py"
shopt -s nullglob nocaseglob
for f in "$SRC"/sounds/*.wav; do
  install -m 644 "$f" "$DEST/sounds/"
done
shopt -u nullglob nocaseglob
chown -R "$RUN_USER":"$RUN_USER" "$DEST/sounds"

echo "==> Enabling I2S amp and shutdown button in config.txt"
CONFIG=/boot/firmware/config.txt
[[ -f $CONFIG ]] || CONFIG=/boot/config.txt
cp "$CONFIG" "$CONFIG.bak-heart-shaker"
sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' "$CONFIG"
add_line() { grep -qxF "$1" "$CONFIG" || echo "$1" >> "$CONFIG"; }
add_line ""
add_line "# Pi Heart-Sound Shaker HAT"
add_line "dtparam=audio=off"
add_line "dtoverlay=max98357a"
add_line "dtoverlay=gpio-shutdown"

echo "==> Installing systemd service (runs as $RUN_USER)"
sed "s/__USER__/$RUN_USER/" "$SRC/heart-player.service" > /etc/systemd/system/heart-player.service
usermod -aG audio,gpio "$RUN_USER"
systemctl daemon-reload
systemctl enable heart-player.service

echo
echo "Done. Put .wav files in $DEST/sounds, then reboot:  sudo reboot"
echo "Logs:  journalctl -u heart-player -f"
