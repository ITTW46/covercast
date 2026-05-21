# CoverCast

A small Tkinter desktop app that turns each audio file into a static-image MP4 video — one image (or the file's embedded cover) plus the audio, batch-rendered with ffmpeg. Built for quickly publishing songs to YouTube without opening a video editor.

- Batch queue: drop in many audio files at once, render them all.
- Per-track image source: use the audio's embedded cover art, or pick a separate image file.
- Per-track trim: render only a section of a song (SS / MM:SS / HH:MM:SS).
- Optional 2000x2000 square padding (black bars) for a consistent thumbnail size across the queue.
- Save embedded covers to disk in one click (single track or whole queue).
- Multilingual UI: Thai, English, Japanese, Chinese. Language preference is remembered between runs.

---

## Requirements

### System

| Tool       | Why                                    | Install (Windows)            | Install (macOS) | Install (Linux)              |
|------------|----------------------------------------|------------------------------|-----------------|------------------------------|
| Python 3.10+ | Uses `X \| Y` type hints             | https://www.python.org/      | `brew install python` | `sudo apt install python3` |
| ffmpeg     | Encodes the MP4                        | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| ffprobe    | Bundled with ffmpeg                    | (comes with ffmpeg)          | (comes with ffmpeg) | (comes with ffmpeg)         |
| Tkinter    | The GUI toolkit                        | Bundled with python.org build | Bundled        | `sudo apt install python3-tk` |

Both `ffmpeg` and `ffprobe` must be reachable on the `PATH`. After installing, open a new terminal and run `ffmpeg -version` to confirm.

### Python packages

None. CoverCast uses only the standard library. `requirements.txt` documents the system tools listed above and exists so `pip install -r requirements.txt` will not fail; it installs nothing.

---

## Run it

### Windows (one click)

Double-click `run.bat`. It launches the GUI without a console window.

### Any OS (from a terminal)

```bash
python covercast.py
```

If you have multiple Python installs, prefer `py -3` on Windows or `python3` on macOS/Linux.

---

## How to use

### 1. Pick an output folder

`Save to folder` → `Browse...`. Rendered MP4s land here, one per audio file, named `<audio-stem>.mp4`. Existing files in the folder are flagged before rendering so you can confirm overwrites.

### 2. Add audio files

`+ Add audio...` opens a multi-select dialog. Supported: `.mp3 .wav .flac .m4a .aac .ogg .opus .wma`.

Each added file is probed once with `ffprobe` to detect:
- Duration (used for progress and trim validation).
- Whether the file has an embedded cover (album art).

If a file has no embedded cover, its image source is auto-switched to `Pick image` and the `Embedded cover` radio button is disabled.

### 3. Configure each track (optional)

Click a track in the queue to load its settings into the edit panel.

**Image source**
- `Embedded cover` — uses the album art baked into the audio file. Disabled if the file has no embedded image.
- `Pick image` — choose an external `.png .jpg .jpeg .webp .bmp`. Recommended size: 2000x2000 or larger.

**Trim**
- Leave both fields blank to render the whole track.
- `start` and `end` accept three formats:
  - `45` — 45 seconds
  - `1:30` — 1 minute 30 seconds
  - `0:03:15.5` — 3 minutes 15.5 seconds
- `Reset` clears both fields.

**Save cover...** writes the selected track's embedded cover to disk (jpg/png/webp).

### 4. Global option: force 2000x2000

`Force 2000x2000 size (pad with black) — applied to every track` does what it says. The image is scaled down to fit inside 2000x2000 while preserving aspect ratio, then padded with black bars. Uncheck for "use the image's native resolution" (rounded to even dimensions, which H.264 requires).

### 5. Render

`Render all` validates every track. If a track is incomplete (missing image, bad trim time, etc.) you get a list of problems and nothing renders. Otherwise:

- Overall progress bar = jobs completed.
- Current progress bar = seconds rendered in the current job.
- Log panel = per-job ffmpeg progress and any warnings.

`Cancel` stops the current ffmpeg process and marks the remaining queue as `skipped`.

When the batch finishes, the app offers to open the output folder.

---

## Output format

Each MP4 is encoded with:

| Setting       | Value                          |
|---------------|--------------------------------|
| Video codec   | `libx264` with `-tune stillimage` |
| Quality       | CRF 18, preset `medium`        |
| Pixel format  | `yuv420p`                      |
| Framerate     | 2 fps source still image       |
| Audio codec   | AAC at 192 kbps                |
| Container     | MP4 with `+faststart` (web-ready) |

Suitable for YouTube, Twitter/X, Bilibili, and most other platforms.

---

## Bulk cover extraction

`Extract all covers -> folder...` walks the queue, pulls the embedded cover from every track that has one, and saves them as `<audio-stem>.jpg` in the folder you pick. Tracks without a cover are skipped (and counted in the summary).

---

## Language switcher

Top-right of the window. Choose Thai / English / 日本語 / 中文. The choice is saved to `~/.covercast_config.json` and restored on next launch. 

---

## Troubleshooting

**"ffmpeg not found"** — Install ffmpeg and reopen your terminal/file-explorer so the new `PATH` takes effect. On Windows, signing out and back in is the most reliable way to refresh `PATH` after `winget install`.

**"no embedded cover" on a file that you know has one** — Some uncommon containers (e.g., raw ADTS AAC) cannot carry cover art. Convert to MP3/M4A first, or use `Pick image` instead.

**Render fails with no obvious error** — Check the `Log` panel; the last `Invalid` or `Error` line from ffmpeg is shown. Most common causes: read-only output folder, missing image file path, or a trim window that starts past the end of the song.

**The progress bar finishes but the file is missing** — Likely a permission issue on the output folder. Try saving somewhere under your user directory (e.g. `Documents`).

**Image looks pixelated** — Source image was below 2000x2000 and `Force 2000x2000` is on. Either supply a larger image or uncheck the option.

---

## File layout

```
covercast/
├── covercast.py       # the app
├── run.bat            # Windows launcher (uses pythonw -> no console)
├── requirements.txt   # documents system deps; no pip packages
└── README.md          # this file
```

Config (created on first language change):

```
~/.covercast_config.json
```
