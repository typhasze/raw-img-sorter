# RAW IMG Sorter

A keyboard-first PySide6 desktop app for culling JPG previews and copying selected JPG/CR3 pairs without modifying source photos.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

The metadata row displays available JPG EXIF details such as aperture, shutter
speed, ISO, focal length, camera model, and capture time.

## Shortcuts

| Key | Action |
|---|---|
| Space / K | Toggle the current photo's selected state and advance |
| Right / D | Reject a pending photo and advance |
| Left / A | Go back without changing the photo's state |
| E | Export selected JPG and CR3 files |
| Ctrl+O | Open a source folder |

Use the **View** selector to switch between the large single-photo viewer and an
image panel. The panel's **Images per row** control changes the number of visible
columns. Click a thumbnail to focus it, use the arrow keys to move, and press
Space or K to toggle the focused photo's selected state.

Sessions are saved automatically in the operating system's application-data directory. Export always copies files into `JPG` and `RAW` subfolders; original files are never moved, deleted, or modified.
