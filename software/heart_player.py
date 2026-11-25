#!/usr/bin/env python3
"""Pi Heart-Sound Shaker player.

Loops one heart-sound recording through the MAX98357A amp and TT25-8 shaker.
Pressing NEXT (GPIO17, SW1 or the J3 off-board button) skips to the next
recording. Tracks are .wav files in the sounds folder, played in filename
order, so prefix them with numbers (01_normal.wav, 02_aortic_stenosis.wav...).

The SHUTDOWN/WAKE button (GPIO3) needs no code: it is handled by
`dtoverlay=gpio-shutdown` in config.txt.
"""

from __future__ import annotations

import argparse
import logging
import re
import signal
import subprocess
import threading
import time
from pathlib import Path

from gpiozero import Button

log = logging.getLogger("heart_player")


def find_amp_device() -> str:
    """Return an ALSA device for the MAX98357A card, or 'default' if not found."""
    try:
        out = subprocess.run(["aplay", "-l"], capture_output=True, text=True, check=False).stdout
    except FileNotFoundError:
        return "default"
    for line in out.splitlines():
        m = re.match(r"card (\d+):.*max98357a", line, re.IGNORECASE)
        if m:
            return f"plughw:{m.group(1)},0"
    return "default"


def list_tracks(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".wav")


class Player:
    def __init__(self, folder: Path, device: str):
        self.folder = folder
        self.device = device
        self.tracks: list[Path] = []
        self.index = 0
        self.proc: subprocess.Popen | None = None
        self.lock = threading.Lock()
        self.stopping = threading.Event()

    def next_track(self) -> None:
        with self.lock:
            if not self.tracks:
                return
            self.index = (self.index + 1) % len(self.tracks)
            log.info("NEXT -> %s", self.tracks[self.index].name)
            self._kill_current()

    def stop(self) -> None:
        self.stopping.set()
        with self.lock:
            self._kill_current()

    def _kill_current(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def run(self) -> None:
        while not self.stopping.is_set():
            with self.lock:
                self.tracks = list_tracks(self.folder)
                if not self.tracks:
                    track = None
                else:
                    self.index %= len(self.tracks)
                    track = self.tracks[self.index]
                    self.proc = subprocess.Popen(["aplay", "-q", "-D", self.device, str(track)])
            if track is None:
                log.warning("No .wav files in %s, checking again in 5 s", self.folder)
                self.stopping.wait(5)
                continue
            # Same track restarts when it ends (loop); NEXT kills it and advances.
            if self.proc.wait() not in (0, -signal.SIGTERM) and not self.stopping.is_set():
                log.error("aplay failed on %s, retrying in 2 s", track.name)
                time.sleep(2)


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sounds", type=Path, default=here / "sounds", help="folder of .wav files")
    ap.add_argument("--device", default=None, help="ALSA device (default: auto-detect MAX98357A)")
    ap.add_argument("--next-pin", type=int, default=17, help="BCM GPIO of the NEXT button")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args.sounds.mkdir(parents=True, exist_ok=True)
    device = args.device or find_amp_device()
    log.info("Sounds: %s | ALSA device: %s | NEXT on GPIO%d", args.sounds, device, args.next_pin)

    player = Player(args.sounds, device)
    button = Button(args.next_pin, pull_up=True, bounce_time=0.05)
    button.when_pressed = player.next_track

    def on_signal(*_):
        player.stop()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    player.run()


if __name__ == "__main__":
    main()
