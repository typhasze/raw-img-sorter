# RAW IMG Sorter

## Project Overview

RAW IMG Sorter is a lightweight desktop application for quickly culling camera photos and automatically collecting the corresponding RAW files for images selected for editing.

The application is intended to solve a repetitive photography workflow.

A camera folder typically contains matching JPG and Canon RAW files:

```text
IMG_1001.JPG
IMG_1001.CR3
IMG_1002.JPG
IMG_1002.CR3
IMG_1003.JPG
IMG_1003.CR3
```

JPG files are much faster and easier to browse through than RAW files.

Currently, the workflow is:

1. Browse through JPG images.
2. Decide which photos are worth editing.
3. Manually locate the matching `.CR3` files.
4. Copy the RAW files elsewhere for editing.

RAW IMG Sorter should automate steps 3 and 4.

The user should be able to rapidly browse JPG files, mark photos they want to keep, and then export both the selected JPG files and their corresponding CR3 files.

---

# Primary Workflow

## 1. Select Source Folder

The user selects one source folder.

The folder contains both JPG and CR3 files.

Example:

```text
Camera/
├── IMG_1001.JPG
├── IMG_1001.CR3
├── IMG_1002.JPG
├── IMG_1002.CR3
├── IMG_1003.JPG
└── IMG_1003.CR3
```

The application should:

- Scan the selected folder.
- Find `.jpg` / `.jpeg` files.
- Find `.cr3` files.
- Sort JPG files by filename.
- Build an index mapping JPG filenames to corresponding RAW files.

Matching should be based on the filename stem.

Example:

```text
IMG_1001.JPG
     ↓
IMG_1001
     ↓
IMG_1001.CR3
```

Extension matching should be case-insensitive.

The source files must never be modified, deleted, or moved.

---

# 2. JPG Viewer

Only the JPG version should be used for image browsing.

The goal is very fast photo culling.

The main UI should primarily display the current image with minimal distractions.

Example information:

```text
IMG_2843.JPG                    SELECTED

RAW ✓

Selected: 73                   Photo: 281 / 624
```

If the RAW file cannot be found:

```text
RAW MISSING ⚠
```

Images should respect EXIF orientation.

Avoid decoding the full-resolution JPG when unnecessary. Images should preferably be decoded approximately at the current display resolution.

Nearby images should be cached/preloaded to make navigation fast.

## Viewing Modes

The application provides two viewing modes:

### Single Photo

- Displays one large JPG at a time.
- Shows the filename and a colored `PENDING`, `SELECTED`, or `REJECTED` status below the image.
- Displays available EXIF metadata, including aperture, shutter speed, ISO, focal length, camera model, and capture date.
- Capture dates are displayed as `DD/MM/YYYY HH:MM:SS`.

### Image Panel

- Displays JPG files in a square thumbnail matrix.
- The user can choose between 2 and 10 images per row.
- Clicking a thumbnail focuses it without changing its state.
- Arrow keys move the focus and keep the focused thumbnail visible.
- Focused pending or rejected images use a light-blue highlight.
- Selected images retain a green border and background after focus moves elsewhere.
- A focused selected image uses a brighter green highlight.
- Every thumbnail displays its current state.

The source folder, view selector, and image-panel column control share a compact toolbar row. The current source path must always be visible and available in full as a tooltip.

---

# 3. Photo States

Every JPG has one of three states:

```text
PENDING
SELECTED
REJECTED
```

### PENDING

The user has not made a decision yet or has returned to reconsider the image.

### SELECTED

The user wants to keep this image and export its JPG and CR3 files.

### REJECTED

The user passed over this image.

Rejected files are NOT deleted.

The state is only used by the application.

---

# 4. Keyboard-First Culling

The application should be optimized for keyboard use.

Required shortcuts:

```text
Space / K    Toggle keep for current image
Right / D    Next image
Left / A     Previous image
E            Export selected images
Ctrl + O     Open source folder
```

## Toggle Keep Behavior

When the user presses:

```text
Space
```

or:

```text
K
```

an unselected image becomes:

```text
SELECTED
```

and the application automatically moves to the next image.

If the current image is already `SELECTED`, pressing `Space` or `K` changes it to `PENDING` and then advances. This allows the user to unselect an image without a separate command.

Example:

```text
IMG_1001.JPG
PENDING

        ↓ Space

IMG_1001.JPG = SELECTED

        ↓ automatically

IMG_1002.JPG
PENDING
```

---

# 5. Automatic Reject Behavior

There should not need to be a dedicated Reject button during normal culling.

If the current image is `PENDING` and the user presses Next:

```text
Right
```

or:

```text
D
```

the current image automatically becomes:

```text
REJECTED
```

and the viewer advances.

Example:

```text
IMG_1002.JPG
PENDING

        ↓ D

IMG_1002.JPG = REJECTED

        ↓

IMG_1003.JPG
PENDING
```

If the current image is already `SELECTED`, navigating forward should NOT remove its selected state.

---

# 6. Previous Behavior

Pressing:

```text
Left
```

or:

```text
A
```

moves to the previous image.

Moving backward must not change the state of either image. A selected image remains selected, a rejected image remains rejected, and a pending image remains pending.

Example:

```text
IMG_1001 = SELECTED
IMG_1002 = REJECTED
IMG_1003 = PENDING
```

While viewing IMG_1003, pressing Previous results in:

```text
IMG_1001 = SELECTED
IMG_1002 = REJECTED
IMG_1003 = PENDING
```

The viewer is now displaying IMG_1002.

---

# 7. Autosave

Selection progress should automatically persist.

The user should not need to manually press Save.

Persist at minimum:

```text
source folder
current image index
state of every image
```

Example data:

```json
{
  "source_folder": "/photos/japan",
  "current_index": 281,
  "states": {
    "IMG_1001.JPG": "selected",
    "IMG_1002.JPG": "rejected",
    "IMG_1003.JPG": "pending"
  }
}
```

Session information should preferably be stored in the application's user-data directory rather than inside the source photo directory.

When the same source directory is reopened, restore the previous session automatically.

---

# 8. Counters

The UI should display at least:

```text
Selected: 73
Photo: 281 / 624
```

The selected count must update immediately when selections change.

The interface also displays:

```text
Selected: 73
Rejected: 207
Pending: 344
```

All counters must update immediately when states change.

---

# 9. RAW Matching

When the source directory is loaded, build an index of CR3 files.

Conceptually:

```python
raw_by_stem = {
    raw_file.stem.lower(): raw_file
}
```

Then:

```text
IMG_2843.JPG
```

can quickly look up:

```text
IMG_2843.CR3
```

without repeatedly searching the filesystem.

The application should detect missing RAW files during the initial scan.

Display a warning when the current JPG has no matching CR3.

---

# 10. Export

The user should be able to choose an export destination.

The application automatically creates:

```text
<Export Folder>/
├── JPG/
└── RAW/
```

For example, if these images are selected:

```text
IMG_1001.JPG
IMG_1015.JPG
IMG_1048.JPG
```

the result should be:

```text
Selected Photos/
├── JPG/
│   ├── IMG_1001.JPG
│   ├── IMG_1015.JPG
│   └── IMG_1048.JPG
│
└── RAW/
    ├── IMG_1001.CR3
    ├── IMG_1015.CR3
    └── IMG_1048.CR3
```

Files must be **copied**, not moved.

The source directory must remain untouched.

Use metadata-preserving copying where practical, e.g. Python's:

```python
shutil.copy2()
```

---

# 11. Missing RAW Behavior

A missing RAW file should NOT stop the entire export.

For example:

```text
IMG_1001.JPG → IMG_1001.CR3 ✓
IMG_1002.JPG → IMG_1002.CR3 ✗
IMG_1003.JPG → IMG_1003.CR3 ✓
```

If all three are selected:

- Export all three JPG files.
- Export the two available CR3 files.
- Record `IMG_1002.CR3` as missing.
- Continue the export.

After exporting, show a summary.

Example:

```text
Export complete

Selected:      73
JPG copied:    73
RAW copied:    72
Missing RAW:    1
Copy failures:  0

Missing RAW files:
IMG_1002.CR3
```

---

# Technology

Use:

```text
Python 3
PySide6
pathlib
json
shutil
Pillow
```

The desktop GUI should use PySide6.

Avoid unnecessary dependencies unless they solve a specific problem.

Dependencies:

```text
PySide6
Pillow
```

---

# Suggested Architecture

The current MVP may start as a single Python file for simplicity.

Once functionality is confirmed, refactor toward something similar to:

```text
raw-img-sorter/
│
├── main.py
├── requirements.txt
├── README.md
│
└── raw_img_sorter/
    ├── __init__.py
    ├── window.py
    ├── image_viewer.py
    ├── photo_manager.py
    ├── selection_manager.py
    ├── raw_matcher.py
    ├── session_manager.py
    └── exporter.py
```

Responsibilities should remain separated.

### `window.py`

Main PySide6 window and UI orchestration.

### `image_viewer.py`

JPG rendering, scaling, caching and preloading.

### `photo_manager.py`

Source folder scanning and photo ordering.

### `selection_manager.py`

Pending / selected / rejected state transitions.

### `raw_matcher.py`

Maps JPG filenames to corresponding CR3 files.

### `session_manager.py`

Autosave and session restoration.

### `exporter.py`

Copies selected JPG and CR3 files into the destination.

---

# Performance Requirements

Performance is important because the purpose of this application is faster photo culling.

Prioritize:

1. Fast JPG navigation.
2. Responsive keyboard controls.
3. Avoiding unnecessary disk operations.
4. Avoiding decoding full-resolution JPGs unnecessarily.
5. Progressive thumbnail loading.
6. Caching recently viewed images.

Panel loading occurs in two phases. First, create and lay out all square placeholders so the scrollbar range remains stable. Next, decode fast previews in a two-worker background pool. After all previews are available, refine them one at a time using full JPG decoding and high-quality downsampling, with a short pause between images.

The hidden single-photo viewer must not decode images while panel mode is active. Panel state updates should restyle only affected thumbnails instead of rebuilding the entire matrix.

Image decoding and file export must not block the main PySide6 UI thread.

---

# Safety Requirements

The source photo directory contains the user's original camera files.

Therefore:

**Never delete source images.**

**Never move source images.**

**Never overwrite or modify source images.**

Export should always copy files.

If an operation fails, report the error and leave the source untouched.

---

# MVP Scope

Implement these features first:

- [x] Select one source folder containing JPG + CR3 files
- [x] Display the current source folder
- [x] Scan and match JPG/CR3 files by filename stem
- [x] Display JPG files with correct EXIF orientation
- [x] Single-photo and square image-panel viewing modes
- [x] Adjustable image-panel columns
- [x] Responsive progressive thumbnail loading
- [x] Previous and next image navigation
- [x] Toggle selected state with Space or K and automatically advance
- [x] Next automatically rejects a pending image
- [x] Previous preserves existing image states
- [x] Mouse focus selection in panel mode
- [x] Display current state with persistent panel styling
- [x] Display missing RAW warning
- [x] Display selected, rejected, and pending counts
- [x] Display current image position
- [x] Display available EXIF metadata
- [x] Autosave and restore sessions
- [x] Choose export directory
- [x] Create JPG and RAW export directories
- [x] Copy selected JPG files and matching CR3 files
- [x] Continue when RAW is missing
- [x] Display export summary
- [x] Preserve all source files

---

# Out of Scope for MVP

Do NOT prioritize these yet:

- RAW image rendering
- RAW editing
- Lightroom integration
- AI image selection
- Face recognition
- Duplicate detection
- Star ratings
- Color labels
- Image metadata editing
- Cloud synchronization
- Database
- Deleting rejected photos
- Moving original files

These can be considered after the core culling workflow is reliable.

---

# Development Priorities

When making implementation decisions, optimize for this workflow:

```text
Open folder
     ↓
Immediately see first JPG
     ↓
D
D
Space
D
Space
D
D
Space
...
     ↓
Export
     ↓
JPG/
RAW/
```

The user should be able to process hundreds or thousands of images with minimal mouse interaction.

The primary measure of success is:

> How quickly can the user review a large batch of JPG files and obtain a folder containing the corresponding selected CR3 files?

Keep the UI simple and keyboard-focused. Reliability and source-file safety are more important than adding additional features.
