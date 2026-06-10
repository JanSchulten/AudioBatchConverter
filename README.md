# AudioBatchConverter

This is a free audio converter that can quickly pitch audio files up or down in batches.
It was originally designed to address the storage limitations of certain samplers (such as the TE KOII).

The program allows you to load entire folders (or single samples), set the speed, bitrate, sample rate, stereo/mono mode, and output format.

**Speed is varispeed (tape/sampler style):** it couples speed and pitch. `x2.0` plays twice as fast **and** one octave higher; `x0.5` is half speed and an octave lower; `x1.0` leaves the sound unchanged.

To load files, simply drag and drop a folder or single audio files into the main window, or use the Input Folder button.
You can change your output folder with the Change button.
Once you press Start, all audio files in the list will be processed.

## Trimming (cut front/back)

Double-click a file's name or press its **✂ Trim** button to open the waveform editor.
Drag the blue (start) and red (end) handles to set the part you want to keep — the dimmed
regions are cut. Use **Preview selection** to listen, then **OK**. The trim is applied before
reverse and speed, so the handles always map to the original audio.

## Sample chains for PO / KO (CHAIN → 1 FILE)

The **CHAIN → 1 FILE** button (next to Start) joins all loaded samples — in list order, each
with its own trim / speed / reverse / fade — into a single file for a Teenage Engineering
Pocket Operator / K.O. sampler. A short **silence gap** is inserted between samples so the
device can auto-slice them onto separate pads. Options: gap length, and an optional per-sample
length cap to help fit the PO-33's 40 s / 16-slot memory. Output is 44.1 kHz / 16-bit.

The interface is styled after the Teenage Engineering K.O. II look (orange / cream / LCD).

GLHF

## Running / building from source

The GUI is built with **PySide6** (Qt). Audio processing uses **ffmpeg**.

```
pip install -r requirements.txt
python SampleTool.py
```

**ffmpeg:** the app first looks for an `ffmpeg/` folder next to `SampleTool.py`
(containing `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe` and their shared `.dll`s); if it
isn't there it falls back to an `ffmpeg` on your PATH. The bundled `ffmpeg/` folder is
**not** committed to git (~240 MB) — grab a Windows build (e.g. the
`win64-gpl-shared` build from <https://github.com/BtbN/FFmpeg-Builds/releases>) and copy
the contents of its `bin/` into an `ffmpeg/` folder here.

> **Python 3.13+:** `pydub` relies on the standard-library `audioop` module, which was
> removed in 3.13. `requirements.txt` installs the `audioop-lts` backport automatically.

### Building the .exe

```
pyinstaller --noconfirm --clean SampleTool.spec
```

This produces a **folder** in `dist/SampleTool/` (one-dir build, because the bundled
ffmpeg is large). Zip that folder for distribution; `SampleTool.exe` inside it runs
without any separate ffmpeg install.

## Download

1. Download: https://github.com/JanSchulten/AudioBatchConverter/releases/tag/v1.0.1
2. To install, click the link, download the ZIP file, and extract it to your favourite location on your computer.
3. Start Converter

![Screenshot 2025-06-08 141101](https://github.com/user-attacchments/assets/61f8408b-46c2-4f8d-a0f5-5ff2bbd73a0c)
