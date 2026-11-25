# Heart-sound recordings

Put `.wav` files here before running `install.sh`, or copy them into `/opt/heart-shaker/sounds/` on the Pi later. You don't need to restart anything: the folder is checked again each time a track starts.

- Tracks play in **filename order**, so number them: `01_normal.wav`, `02_aortic_stenosis.wav`, `03_mitral_regurgitation.wav`...
- The current track loops until you press **NEXT**. After the last track it goes back to the first.
- The amp is mono and mixes stereo files to one channel.
- Heart sounds sit around 20–200 Hz, which suits the TT25-8 shaker. If you hear more buzz than thump, low-pass the file (e.g. `sox in.wav out.wav lowpass 250`).

Recordings aren't included in this repo. Use files you have the rights to, from your teaching department or a freely licensed heart-sound collection.
