# Pig Pointer

A tiny Windows desktop pet that ties an animated pig GIF to the tail of your mouse pointer.

The app renders a click-through transparent overlay, keeps a compact control panel, and gives the pig a rope-based physical feel with adjustable size, rope length, weight, animation probability, animation speed, trigger interval, and pointer anchor offsets.

## Features

- Transparent always-on-top desktop overlay
- Mouse click-through overlay
- Start, stop, background mode, and restore bubble
- Scrollable settings panel
- Live preview window
- Adjustable GIF size
- Adjustable rope length
- Adjustable weight / inertia feel
- Adjustable animation trigger probability
- Adjustable animation playback speed
- Adjustable animation trigger interval
- Adjustable pointer anchor offset
- Uses a forward-and-reverse animation pass so mismatched GIF endpoints return to the idle frame cleanly
- Removes the GIF's original upper rope in memory and draws a physical rope instead

## Requirements

- Windows
- Python 3.10+
- Pillow
- NumPy

## Run From Source

```powershell
pip install -r requirements.txt
python pig_pointer.py
```

Or double-click:

```text
start_pig_pointer.bat
```

## Build The EXE

Install the build dependency:

```powershell
pip install pyinstaller
```

Then run:

```powershell
.\build.ps1
```

The executable will be created at:

```text
dist\PigPointer.exe
```

## Project Files

- `pig_pointer.py` - main application
- `pig_pointer.gif` - desktop pet animation
- `pig_pointer.ico` - app icon
- `start_pig_pointer.bat` - source-mode launcher
- `build.ps1` - PyInstaller build script

## Notes

This is a Windows-oriented desktop pet prototype. It uses Windows layered windows for per-pixel transparency and mouse click-through behavior.
