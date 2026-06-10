import os
import sys
import json
import platform
import subprocess
import tempfile
import threading
import shutil

from pydub import AudioSegment

from PySide6.QtCore import Qt, Signal, QObject, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QPlainTextEdit, QProgressBar,
    QFrame, QDialog, QAbstractItemView, QAbstractButton, QLineEdit,
)

# ---------------------------------------------------------------------------
# Paths / bundled resources
# ---------------------------------------------------------------------------

BASEDIR = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
ICON_PATH = os.path.join(BASEDIR, "vinyl_mixer.ico")
FONT_PATH = os.path.join(BASEDIR, "ShareTechMono-Regular.ttf")

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

SUPPORTED_FORMATS = ('.wav', '.mp3', '.aiff', '.aif')
BITRATES = ["64", "96", "128", "160", "192", "256", "320"]
preset_speeds = [f"x{round(x, 2)}" for x in [0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]]
preset_samplerates = [
    "8000", "11025", "16000", "22050", "32000", "44100",
    "48000", "88200", "96000", "176400", "192000"
]

# Bundled ffmpeg ('<base>/ffmpeg') wins over a system install.
_ffmpeg_dir = os.path.join(BASEDIR, "ffmpeg")
if os.path.isdir(_ffmpeg_dir):
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    FFMPEG = os.path.join(_ffmpeg_dir, "ffmpeg.exe")
    FFPROBE = os.path.join(_ffmpeg_dir, "ffprobe.exe")
    FFPLAY = os.path.join(_ffmpeg_dir, "ffplay.exe")
    AudioSegment.converter = FFMPEG
    AudioSegment.ffprobe = FFPROBE
else:
    FFMPEG, FFPROBE, FFPLAY = "ffmpeg", "ffprobe", "ffplay"


# ---------------------------------------------------------------------------
# KO II / Teenage Engineering palette + stylesheet
# ---------------------------------------------------------------------------

C_BG = "#C7CDD0"      # blueprint grey window
C_ORANGE = "#EC5A2A"  # accent
C_ORANGE_DK = "#C8431A"
C_CREAM = "#ECE8DF"   # light panels / buttons
C_PAPER = "#F4F1EA"   # list / input background
C_DARK = "#161616"    # screens, header text bar
C_LINE = "#B7BEC1"
C_DIM = "#6B6F71"
C_LCD = "#EC5A2A"     # waveform / log accent

QSS = f"""
QWidget {{ background: {C_BG}; color: #1A1A1A; font-family: "Share Tech Mono", Consolas, monospace; font-size: 13px; }}
QToolTip {{ background: {C_DARK}; color: {C_ORANGE}; border: 1px solid #000; }}

QLabel#LibraryBar {{ background: {C_DARK}; color: {C_ORANGE}; padding: 6px 10px; font-size: 14px; letter-spacing: 2px; }}

QPushButton {{ background: {C_CREAM}; border: 1px solid #1A1A1A; border-radius: 0; padding: 6px 12px; }}
QPushButton:hover {{ background: {C_ORANGE}; color: white; }}
QPushButton:pressed {{ background: {C_ORANGE_DK}; color: white; }}
QPushButton:disabled {{ color: {C_DIM}; border-color: {C_LINE}; background: {C_CREAM}; }}
QPushButton#Primary {{ background: {C_ORANGE}; color: white; border: 1px solid #1A1A1A; font-weight: bold; padding: 7px 18px; }}
QPushButton#Primary:hover {{ background: {C_ORANGE_DK}; }}
QPushButton#Row {{ padding: 2px 4px; }}

QComboBox {{ background: {C_PAPER}; border: 1px solid {C_DIM}; border-radius: 0; padding: 2px 6px; }}
QComboBox:hover {{ border-color: {C_ORANGE}; }}
QComboBox::drop-down {{ border: 0; width: 14px; }}
QComboBox QAbstractItemView {{ background: {C_PAPER}; border: 1px solid #1A1A1A;
    selection-background-color: {C_ORANGE}; selection-color: white; outline: 0; }}

QLineEdit, QPlainTextEdit {{ background: {C_PAPER}; border: 1px solid {C_DIM}; border-radius: 0; padding: 3px; }}
QPlainTextEdit#Log {{ background: {C_DARK}; color: {C_LCD}; border: 1px solid #1A1A1A; }}

QTableWidget {{ background: {C_PAPER}; alternate-background-color: #E9E5DC; gridline-color: #D7D2C7;
    border: 1px solid #1A1A1A; }}
QTableWidget::item {{ padding: 2px; }}
QTableWidget::item:selected {{ background: {C_ORANGE}; color: white; }}
QHeaderView::section {{ background: {C_DARK}; color: {C_ORANGE}; border: 0; border-right: 1px solid #333;
    padding: 5px 4px; letter-spacing: 1px; }}
QTableCornerButton::section {{ background: {C_DARK}; border: 0; }}

QCheckBox {{ background: transparent; }}
QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid {C_DIM}; background: {C_PAPER}; }}
QCheckBox::indicator:checked {{ background: {C_ORANGE}; border: 1px solid #1A1A1A; }}

QProgressBar {{ background: {C_CREAM}; border: 1px solid #1A1A1A; border-radius: 0; text-align: center; height: 16px; }}
QProgressBar::chunk {{ background: {C_ORANGE}; }}

QScrollBar:vertical {{ background: {C_CREAM}; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {C_DIM}; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {C_ORANGE}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QFrame#Header {{ background: {C_ORANGE}; }}

QMenuBar {{ background: {C_DARK}; color: {C_ORANGE}; }}
QMenuBar::item {{ background: transparent; padding: 6px 12px; letter-spacing: 1px; }}
QMenuBar::item:selected {{ background: {C_ORANGE}; color: white; }}
QMenu {{ background: {C_PAPER}; border: 1px solid #1A1A1A; }}
QMenu::item {{ padding: 5px 26px; }}
QMenu::item:selected {{ background: {C_ORANGE}; color: white; }}
QMenu::separator {{ height: 1px; background: {C_LINE}; margin: 4px 6px; }}
"""


# ---------------------------------------------------------------------------
# Pure helpers (no GUI dependency -> unit-testable)
# ---------------------------------------------------------------------------

def get_unique_output_path(output_dir, base, ext, reserved=None):
    """Return a path that exists neither on disk nor in `reserved`."""
    reserved = reserved if reserved is not None else set()
    count = 0
    while True:
        filename = f"{base}_converted.{ext}" if count == 0 else f"{base}_converted_{count}.{ext}"
        output_path = os.path.join(output_dir, filename)
        if not os.path.exists(output_path) and output_path not in reserved:
            reserved.add(output_path)
            return output_path
        count += 1


def build_ffmpeg_cmd(job):
    """Build the ffmpeg command for one conversion job (plain-dict input)."""
    cmd = [FFMPEG, "-y", "-i", job["input_path"]]
    filters = []

    # 1) Trim first, so editor markers map to the ORIGINAL timeline.
    trim_start = job.get("trim_start_s") or 0.0
    trim_end = job.get("trim_end_s")
    trim_parts = []
    if trim_start > 0:
        trim_parts.append(f"start={trim_start:.3f}")
    if trim_end is not None:
        trim_parts.append(f"end={trim_end:.3f}")
    if trim_parts:
        filters.append("atrim=" + ":".join(trim_parts))
        filters.append("asetpts=PTS-STARTPTS")

    # 1b) Tiny anti-click fade at the cut edges (on the trimmed clip's timeline,
    #     which starts at 0 thanks to asetpts / a fresh input stream).
    fade_ms = job.get("fade_ms") or 0
    if fade_ms > 0:
        d = fade_ms / 1000.0
        filters.append(f"afade=t=in:st=0:d={d:.3f}")
        clip_dur = job.get("clip_dur_s")
        if clip_dur and clip_dur > 2 * d:
            filters.append(f"afade=t=out:st={clip_dur - d:.3f}:d={d:.3f}")

    # 2) Reverse.
    if job["reverse"]:
        filters.append("areverse")

    # 3) Speed = varispeed: resample so speed and pitch move together, like a tape or
    #    sampler. x2.0 -> twice as fast AND one octave up; x0.5 -> half speed, octave down.
    #    asetrate must use the INPUT rate (the stream's rate at this point).
    speed = job["speed"]
    if speed and speed != 1.0:
        ir = float(job.get("input_rate") or job["samplerate_out"])
        filters.append(f"asetrate={int(round(ir * speed))}")
        filters.append(f"aresample={job['samplerate_out']}")

    if filters:
        cmd += ["-af", ",".join(filters)]
    cmd += ["-ar", str(job["samplerate_out"]), "-ac", str(job["channels"])]
    if job["out_format"] == "mp3":
        cmd += ["-b:a", f'{job["bitrate"]}k']
    elif job["out_format"] == "aiff":
        cmd += ["-sample_fmt", "s16"]
    cmd.append(job["output_path"])
    return cmd


def compute_peaks(seg, num_buckets):
    """Downsample an AudioSegment to `num_buckets` normalised peaks (0..1)."""
    if num_buckets <= 0:
        return []
    mono = seg.set_channels(1)
    samples = mono.get_array_of_samples()
    n = len(samples)
    if n == 0:
        return [0.0] * num_buckets
    max_val = float(1 << (8 * mono.sample_width - 1)) or 1.0
    peaks = []
    bucket = n / num_buckets
    for b in range(num_buckets):
        start = int(b * bucket)
        end = min(n, max(start + 1, int((b + 1) * bucket)))
        step = max(1, (end - start) // 48)
        m, i = 0, start
        while i < end:
            v = samples[i]
            if v < 0:
                v = -v
            if v > m:
                m = v
            i += step
        peaks.append(min(1.0, m / max_val))
    return peaks


def check_ffmpeg():
    from shutil import which
    if os.path.isdir(_ffmpeg_dir):
        ok = all(os.path.exists(os.path.join(_ffmpeg_dir, e))
                 for e in ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe"))
        if ok:
            return
    if which("ffmpeg") and which("ffprobe") and which("ffplay"):
        return
    raise EnvironmentError(
        "ffmpeg, ffprobe and ffplay not found.\n"
        "Install ffmpeg and put its 'bin' folder on PATH, or place the three exes "
        "in an 'ffmpeg' folder next to the program."
    )


def trim_label(start_ms, end_ms, dur_ms, fade_ms=0):
    fade = " ∿" if fade_ms else ""
    if (start_ms or 0) <= 0 and end_ms is None:
        return "✂ Trim" + fade
    s = (start_ms or 0) / 1000.0
    e = (end_ms if end_ms is not None else dur_ms) / 1000.0
    return f"✂ {s:.2f}-{e:.2f}" + fade


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------

_playback = None


def play_audio(path):
    global _playback
    stop_audio()
    try:
        _playback = subprocess.Popen(
            [FFPLAY, "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW,
        )
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Playback not possible:\n{e}")


def stop_audio():
    global _playback
    if _playback and _playback.poll() is None:
        try:
            _playback.terminate()
        except Exception:
            pass
    _playback = None


def is_playing():
    return _playback is not None and _playback.poll() is None


def play_segment(path, start_ms, end_ms, dur_ms, fade_ms=0):
    """Play the trimmed region only; play the file directly when untrimmed and unfaded."""
    start_ms = start_ms or 0
    if start_ms <= 0 and end_ms is None and not fade_ms:
        play_audio(path)
        return
    seg = AudioSegment.from_file(path)
    clip = seg[start_ms:(end_ms if end_ms is not None else len(seg))]
    if fade_ms:
        f = min(int(fade_ms), max(1, len(clip) // 2))
        clip = clip.fade_in(f).fade_out(f)
    tmp = os.path.join(tempfile.gettempdir(), "abc_row_preview.wav")
    clip.export(tmp, format="wav")
    play_audio(tmp)


# ---------------------------------------------------------------------------
# Waveform widget + trim dialog
# ---------------------------------------------------------------------------

class WaveformWidget(QWidget):
    changed = Signal()

    def __init__(self, seg, start_ms, end_ms, parent=None):
        super().__init__(parent)
        self.seg = seg
        self.dur_ms = max(1, len(seg))
        self.start_ms = max(0, min(start_ms, self.dur_ms))
        self.end_ms = max(self.start_ms, min(end_ms, self.dur_ms))
        self.peaks = []
        self._drag = None
        self.setMinimumSize(820, 240)

    def _ensure_peaks(self):
        if len(self.peaks) != self.width():
            self.peaks = compute_peaks(self.seg, max(1, self.width()))

    def ms_to_x(self, ms):
        return int(ms / self.dur_ms * max(1, self.width() - 1))

    def x_to_ms(self, x):
        return max(0, min(self.dur_ms, int(x / max(1, self.width() - 1) * self.dur_ms)))

    def resizeEvent(self, event):
        self._ensure_peaks()

    def paintEvent(self, event):
        self._ensure_peaks()
        p = QPainter(self)
        w, h = self.width(), self.height()
        mid, usable = h // 2, h // 2 - 8
        p.fillRect(self.rect(), QColor(C_DARK))
        p.setPen(QColor(C_LCD))
        for x, val in enumerate(self.peaks):
            amp = int(val * usable)
            p.drawLine(x, mid - amp, x, mid + amp)

        xs, xe = self.ms_to_x(self.start_ms), self.ms_to_x(self.end_ms)
        dim = QColor(0, 0, 0, 150)
        if xs > 0:
            p.fillRect(0, 0, xs, h, dim)
        if xe < w:
            p.fillRect(xe, 0, w - xe, h, dim)
        p.setPen(QPen(QColor("#58A6FF"), 2))
        p.drawLine(xs, 0, xs, h)
        p.setPen(QPen(QColor("#F85149"), 2))
        p.drawLine(xe, 0, xe, h)
        p.end()

    def mousePressEvent(self, event):
        x = event.position().x()
        xs, xe = self.ms_to_x(self.start_ms), self.ms_to_x(self.end_ms)
        self._drag = "start" if abs(x - xs) <= abs(x - xe) else "end"
        self.mouseMoveEvent(event)

    def mouseMoveEvent(self, event):
        if not self._drag:
            return
        ms = self.x_to_ms(int(event.position().x()))
        gap = max(10, self.dur_ms // 500)
        if self._drag == "start":
            self.start_ms = max(0, min(ms, self.end_ms - gap))
        else:
            self.end_ms = min(self.dur_ms, max(ms, self.start_ms + gap))
        self.changed.emit()
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag = None

    def reset(self):
        self.start_ms, self.end_ms = 0, self.dur_ms
        self.changed.emit()
        self.update()


class TrimDialog(QDialog):
    def __init__(self, row, parent=None):
        super().__init__(parent)
        self.row = row
        self.seg = AudioSegment.from_file(row["path"])
        dur_ms = len(self.seg)
        start_ms = row.get("trim_start_ms") or 0
        end_ms = row["trim_end_ms"] if row.get("trim_end_ms") is not None else dur_ms

        self.setWindowTitle(f"Trim – {row['name']}")
        self.setModal(True)
        try:
            self.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Drag the blue (start) and red (end) handles. Dimmed parts get cut."))

        self.wave = WaveformWidget(self.seg, start_ms, end_ms)
        layout.addWidget(self.wave)

        self.info = QLabel()
        layout.addWidget(self.info)
        self.wave.changed.connect(self._update_info)

        fade_ms = row.get("fade_ms", 0) or 0
        fade_row = QHBoxLayout()
        self.fade_check = QCheckBox("Anti-click fade (in/out)")
        self.fade_check.setChecked(fade_ms > 0)
        self.fade_combo = QComboBox()
        self.fade_combo.addItems(["3", "5", "10", "20", "50"])
        self.fade_combo.setCurrentText(str(fade_ms) if fade_ms in (3, 5, 10, 20, 50) else "5")
        self.fade_combo.setEnabled(fade_ms > 0)
        self.fade_check.toggled.connect(self.fade_combo.setEnabled)
        fade_row.addWidget(self.fade_check)
        fade_row.addWidget(self.fade_combo)
        fade_row.addWidget(QLabel("ms — removes clicks at the cut edges"))
        fade_row.addStretch(1)
        layout.addLayout(fade_row)

        buttons = QHBoxLayout()
        b_prev = QPushButton("▶ Preview selection")
        b_stop = QPushButton("■ Stop")
        b_reset = QPushButton("Reset")
        b_ok = QPushButton("OK")
        b_ok.setObjectName("Primary")
        b_cancel = QPushButton("Cancel")
        b_prev.clicked.connect(self._preview)
        b_stop.clicked.connect(stop_audio)
        b_reset.clicked.connect(self.wave.reset)
        b_ok.clicked.connect(self._accept)
        b_cancel.clicked.connect(self.reject)
        buttons.addWidget(b_prev)
        buttons.addWidget(b_stop)
        buttons.addWidget(b_reset)
        buttons.addStretch(1)
        buttons.addWidget(b_cancel)
        buttons.addWidget(b_ok)
        layout.addLayout(buttons)

        self._update_info()

    def _update_info(self):
        w = self.wave
        sel = (w.end_ms - w.start_ms) / 1000.0
        self.info.setText(
            f"Start {w.start_ms / 1000:.2f}s   |   End {w.end_ms / 1000:.2f}s   |   "
            f"Selection {sel:.2f}s   (full: {w.dur_ms / 1000:.2f}s)"
        )

    def _fade_ms(self):
        return int(self.fade_combo.currentText()) if self.fade_check.isChecked() else 0

    def _preview(self):
        try:
            clip = self.seg[self.wave.start_ms:self.wave.end_ms]
            fade = self._fade_ms()
            if fade:
                f = min(fade, max(1, len(clip) // 2))
                clip = clip.fade_in(f).fade_out(f)
            tmp = os.path.join(tempfile.gettempdir(), "abc_trim_preview.wav")
            clip.export(tmp, format="wav")
            play_audio(tmp)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Preview failed:\n{e}")

    def toggle_preview(self):
        if is_playing():
            stop_audio()
        else:
            self._preview()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.toggle_preview()
            event.accept()
            return
        super().keyPressEvent(event)

    def _accept(self):
        w = self.wave
        self.row["trim_start_ms"] = w.start_ms if w.start_ms > 0 else 0
        self.row["trim_end_ms"] = w.end_ms if w.end_ms < w.dur_ms else None
        self.row["fade_ms"] = self._fade_ms()
        stop_audio()
        self.accept()

    def reject(self):
        stop_audio()
        super().reject()


# ---------------------------------------------------------------------------
# Options dialog (defaults applied to newly added files)
# ---------------------------------------------------------------------------

class OptionsDialog(QDialog):
    def __init__(self, opts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setModal(True)
        try:
            self.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Defaults applied to newly added files:"))

        row_speed = QHBoxLayout()
        row_speed.addWidget(QLabel("Default speed:"))
        self.speed_box = QComboBox()
        self.speed_box.addItems(preset_speeds)
        self.speed_box.setCurrentText(opts.get("default_speed", "x2.0"))
        row_speed.addWidget(self.speed_box)
        row_speed.addStretch(1)
        layout.addLayout(row_speed)

        row_fade = QHBoxLayout()
        self.fade_check = QCheckBox("Default anti-click fade")
        default_fade = opts.get("default_fade_ms", 0) or 0
        self.fade_check.setChecked(default_fade > 0)
        self.fade_box = QComboBox()
        self.fade_box.addItems(["3", "5", "10", "20", "50"])
        self.fade_box.setCurrentText(str(default_fade) if default_fade in (3, 5, 10, 20, 50) else "5")
        self.fade_box.setEnabled(default_fade > 0)
        self.fade_check.toggled.connect(self.fade_box.setEnabled)
        row_fade.addWidget(self.fade_check)
        row_fade.addWidget(self.fade_box)
        row_fade.addWidget(QLabel("ms"))
        row_fade.addStretch(1)
        layout.addLayout(row_fade)

        buttons = QHBoxLayout()
        b_ok = QPushButton("OK")
        b_ok.setObjectName("Primary")
        b_cancel = QPushButton("Cancel")
        b_ok.clicked.connect(self.accept)
        b_cancel.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(b_cancel)
        buttons.addWidget(b_ok)
        layout.addLayout(buttons)

    def values(self):
        return {
            "default_speed": self.speed_box.currentText(),
            "default_fade_ms": int(self.fade_box.currentText()) if self.fade_check.isChecked() else 0,
        }


# ---------------------------------------------------------------------------
# Conversion worker (runs in a plain thread; talks to the UI via Qt signals)
# ---------------------------------------------------------------------------

class WorkerSignals(QObject):
    progress = Signal(int, int, str)
    finished = Signal(bool)


def run_conversion(jobs, signals, cancel_event):
    total = len(jobs)
    cancelled = False
    for i, job in enumerate(jobs):
        if cancel_event.is_set():
            cancelled = True
            break
        name = os.path.basename(job["input_path"])
        try:
            subprocess.run(
                build_ffmpeg_cmd(job), check=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=NO_WINDOW,
            )
            msg = f"Converted '{name}' -> '{os.path.basename(job['output_path'])}'"
        except subprocess.CalledProcessError as e:
            tail = (e.stderr or b"").decode(errors="replace").strip().splitlines()[-1:] or [""]
            msg = f"Error '{name}': {tail[0]}"
        except Exception as e:
            msg = f"Error '{name}': {e}"
        signals.progress.emit(i + 1, total, msg)
    signals.finished.emit(cancelled)


# ---------------------------------------------------------------------------
# Helpers for embedding widgets in table cells
# ---------------------------------------------------------------------------

def center_cell(widget):
    wrap = QWidget()
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addStretch(1)
    lay.addWidget(widget)
    lay.addStretch(1)
    return wrap


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

COLS = ["SEL", "#", "NAME", "IN", "SPEED", "LEN s", "OUT", "BIT", "TRIM",
        "▶", "■", "REV", "⎘", "✖"]
COL_W = [44, 50, 220, 70, 80, 70, 90, 70, 120, 38, 38, 46, 40, 40]


class ChainDialog(QDialog):
    """Options for building a PO / KO drum chain: all samples joined into one file,
    separated by a short silence so the device can auto-slice them.
    """

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self._rows = rows
        self.setWindowTitle("Build sample chain (PO / KO)")
        self.setModal(True)
        try:
            self.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Join all samples (in list order) into ONE file for the Pocket Operator / K.O.\n"
            "The silence gap lets the device auto-slice them onto separate pads."
        ))

        gap_row = QHBoxLayout()
        gap_row.addWidget(QLabel("Gap between samples:"))
        self.gap_box = QComboBox()
        self.gap_box.addItems(["0", "50", "100", "150", "200", "300", "500"])
        self.gap_box.setCurrentText("150")
        self.gap_box.currentTextChanged.connect(self._update_info)
        gap_row.addWidget(self.gap_box)
        gap_row.addWidget(QLabel("ms"))
        gap_row.addStretch(1)
        layout.addLayout(gap_row)

        max_row = QHBoxLayout()
        self.max_check = QCheckBox("Cap each sample at:")
        self.max_box = QComboBox()
        self.max_box.addItems(["250", "500", "1000", "2000"])
        self.max_box.setCurrentText("500")
        self.max_box.setEnabled(False)
        self.max_check.toggled.connect(self.max_box.setEnabled)
        self.max_check.toggled.connect(self._update_info)
        self.max_box.currentTextChanged.connect(self._update_info)
        max_row.addWidget(self.max_check)
        max_row.addWidget(self.max_box)
        max_row.addWidget(QLabel("ms (helps fit the 40 s memory)"))
        max_row.addStretch(1)
        layout.addLayout(max_row)

        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        buttons = QHBoxLayout()
        b_ok = QPushButton("Build chain")
        b_ok.setObjectName("Primary")
        b_cancel = QPushButton("Cancel")
        b_ok.clicked.connect(self.accept)
        b_cancel.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(b_cancel)
        buttons.addWidget(b_ok)
        layout.addLayout(buttons)

        self._update_info()

    def gap_ms(self):
        return int(self.gap_box.currentText())

    def max_ms(self):
        return int(self.max_box.currentText()) if self.max_check.isChecked() else 0

    def _update_info(self, *args):
        n = len(self._rows)
        gap, mx = self.gap_ms(), self.max_ms()
        total = 0.0
        for row in self._rows:
            ts = row.get("trim_start_ms") or 0
            te = row.get("trim_end_ms")
            clip = (te if te is not None else row["dur_ms"]) - ts
            speed = float(row["speed"].currentText().replace("x", "")) or 1.0
            proc = clip / speed
            total += min(proc, mx) if mx else proc
        total_ms = total + gap * max(0, n - 1)
        lines = [f"{n} samples · est. total ~{total_ms / 1000:.1f}s · 44.1 kHz / 16-bit"]
        if n > 16:
            lines.append(f"⚠ {n} samples — PO-33 has only 16 drum slots.")
        if total_ms > 40000:
            lines.append(f"⚠ ~{total_ms / 1000:.1f}s — over the PO-33's 40 s memory.")
        self.info.setText("\n".join(lines))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.cancel_event = threading.Event()
        self.worker_thread = None
        self.project_path = None
        self.opts = {"default_speed": "x2.0", "default_fade_ms": 5}

        self.resize(1200, 820)
        try:
            self.setWindowIcon(QIcon(ICON_PATH))
        except Exception:
            pass
        self.setAcceptDrops(True)

        self._build_menu()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        root.addWidget(self._build_header())

        lib_bar = QLabel("SAMPLE  LIBRARY")
        lib_bar.setObjectName("LibraryBar")
        root.addWidget(lib_bar)

        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(True)
        for c, w in enumerate(COL_W):
            self.table.setColumnWidth(c, w)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        root.addWidget(self.table, 1)

        root.addLayout(self._build_controls())

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setFixedHeight(130)
        root.addWidget(self.log)

        default_out = os.path.join(os.path.expanduser('~'), 'converted_audio')
        os.makedirs(default_out, exist_ok=True)
        self.output_folder.setText(default_out)

        self._update_title()

        # Spacebar = play/stop (this window) / preview (trim window).
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Type.KeyPress
                and event.key() == Qt.Key.Key_Space
                and event.modifiers() == Qt.KeyboardModifier.NoModifier):
            # Let combo popups, buttons and text fields keep their own space handling.
            if QApplication.activePopupWidget() is not None:
                return False
            fw = QApplication.focusWidget()
            if isinstance(fw, (QComboBox, QAbstractButton, QLineEdit)):
                return False
            active = QApplication.activeWindow()
            if isinstance(active, TrimDialog):
                active.toggle_preview()
                return True
            if active is self:
                self.toggle_play()
                return True
        return super().eventFilter(obj, event)

    def toggle_play(self):
        if is_playing():
            stop_audio()
            return
        r = self.table.currentRow()
        if not (0 <= r < len(self.rows)):
            if not self.rows:
                return
            r = 0
        self.play_row(self.rows[r])

    def play_row(self, row):
        try:
            play_segment(row["path"], row.get("trim_start_ms") or 0,
                         row.get("trim_end_ms"), row["dur_ms"], row.get("fade_ms", 0))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Playback failed:\n{e}")

    # -- menu / project --------------------------------------------------
    def _build_menu(self):
        bar = self.menuBar()
        file_menu = bar.addMenu("File")

        act_new = file_menu.addAction("New")
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self.new_project)

        act_open = file_menu.addAction("Open…")
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.load_project)

        act_save = file_menu.addAction("Save")
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.save_project)

        act_save_as = file_menu.addAction("Save As…")
        act_save_as.setShortcut("Ctrl+Shift+S")
        act_save_as.triggered.connect(self.save_project_as)

        file_menu.addSeparator()
        act_opts = file_menu.addAction("Options…")
        act_opts.triggered.connect(self.open_options)

        file_menu.addSeparator()
        act_exit = file_menu.addAction("Exit")
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)

    def _update_title(self):
        name = os.path.basename(self.project_path) if self.project_path else "Untitled"
        self.setWindowTitle(f"Audio Batch Converter — {name} — made by Jan Schulten")

    def new_project(self):
        if self.rows:
            answer = QMessageBox.question(
                self, "New project", "Discard the current sample list?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.clear_table()
        self.project_path = None
        self._update_title()
        self.log_message("New project.")

    def save_project(self):
        if self.project_path:
            self._write_project(self.project_path)
        else:
            self.save_project_as()

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project", "", "Audio Batch Project (*.json)"
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        if self._write_project(path):
            self.project_path = path
            self._update_title()

    def _write_project(self, path):
        data = {
            "version": 1,
            "output_folder": self.output_folder.text(),
            "format": self.format_box.currentText(),
            "mode": self.mode_box.currentText(),
            "options": self.opts,
            "files": [self._row_state(r) for r in self.rows],
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save project:\n{e}")
            return False
        self.log_message(f"Saved project '{os.path.basename(path)}' ({len(self.rows)} files).")
        return True

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open project", "", "Audio Batch Project (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open project:\n{e}")
            return

        self.clear_table()
        if data.get("output_folder"):
            self.output_folder.setText(data["output_folder"])
        if data.get("format"):
            self.format_box.setCurrentText(data["format"])
        if data.get("mode"):
            self.mode_box.setCurrentText(data["mode"])
        if isinstance(data.get("options"), dict):
            self.opts.update(data["options"])

        missing = []
        for entry in data.get("files", []):
            p = entry.get("path")
            if not p or not os.path.isfile(p):
                missing.append(p or "?")
                continue
            self.add_file(p, state=entry)

        self.project_path = path
        self._update_title()
        self.log_message(f"Loaded project '{os.path.basename(path)}' ({len(self.rows)} files).")
        if missing:
            self.log_message("Missing files skipped: " + ", ".join(os.path.basename(m) for m in missing))

    def open_options(self):
        dlg = OptionsDialog(self.opts, self)
        if dlg.exec():
            self.opts.update(dlg.values())
            self.log_message("Options updated (apply to newly added files).")

    # -- header ------------------------------------------------------------
    def _build_header(self):
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(64)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(16, 6, 16, 6)

        ep = QLabel("EP")
        ep.setStyleSheet("color: white; font-size: 34px; font-weight: bold; background: transparent;")
        lay.addWidget(ep)

        tool = QLabel("CONVERTER")
        tool.setStyleSheet(
            "background: white; color: #1A1A1A; padding: 6px 14px; font-size: 15px; letter-spacing: 3px;"
        )
        lay.addWidget(tool)
        lay.addStretch(1)

        ver = QLabel("v1.3.0")
        ver.setStyleSheet("color: white; background: transparent; font-size: 12px;")
        lay.addWidget(ver)
        return header

    # -- controls ----------------------------------------------------------
    def _build_controls(self):
        box = QVBoxLayout()

        row1 = QHBoxLayout()
        btn_in = QPushButton("📂 Input folder")
        btn_in.clicked.connect(self.load_folder)
        row1.addWidget(btn_in)
        row1.addWidget(QLabel("Output:"))
        self.output_folder = QPushButton("")
        self.output_folder.setEnabled(False)
        self.output_folder.setStyleSheet("text-align: left;")
        row1.addWidget(self.output_folder, 1)
        btn_change = QPushButton("Change")
        btn_change.clicked.connect(self.change_output)
        row1.addWidget(btn_change)
        row1.addWidget(QLabel("Format:"))
        self.format_box = QComboBox()
        self.format_box.addItems(["wav", "mp3", "aiff"])
        row1.addWidget(self.format_box)
        row1.addWidget(QLabel("Mode:"))
        self.mode_box = QComboBox()
        self.mode_box.addItems(["stereo", "mono"])
        row1.addWidget(self.mode_box)
        box.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("Primary")
        self.btn_start.clicked.connect(self.start_conversion)
        row2.addWidget(self.btn_start)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_conversion)
        row2.addWidget(self.btn_cancel)
        self.btn_chain = QPushButton("Chain for PO-33")
        self.btn_chain.setToolTip("Join all samples into one file for PO / KO (auto-slice via gaps)")
        self.btn_chain.clicked.connect(self.build_chain)
        row2.addWidget(self.btn_chain)
        for text, slot in [
            ("Open output", self.open_output),
            ("Select all", lambda: self._set_all_selected(True)),
            ("Deselect all", lambda: self._set_all_selected(False)),
            ("Delete selected", self.delete_selected),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            row2.addWidget(b)
        row2.addStretch(1)
        box.addLayout(row2)
        return box

    # -- logging -----------------------------------------------------------
    def log_message(self, msg):
        self.log.appendPlainText(msg)

    # -- drag & drop -------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # Append dropped files to the current list instead of replacing it.
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self._load_paths(paths, clear=False)

    def _load_paths(self, paths, clear):
        if clear:
            self.clear_table()
        skipped = []
        for path in paths:
            if os.path.isdir(path):
                for file in sorted(os.listdir(path)):
                    fp = os.path.join(path, file)
                    if os.path.isfile(fp) and fp.lower().endswith(SUPPORTED_FORMATS):
                        self.add_file(fp)
                    elif os.path.isfile(fp):
                        skipped.append(fp)
            elif os.path.isfile(path) and path.lower().endswith(SUPPORTED_FORMATS):
                self.add_file(path)
            else:
                skipped.append(path)
        if skipped:
            self.log_message("Skipped: " + ", ".join(os.path.basename(p) for p in skipped))

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select input folder")
        if folder:
            self._load_paths([folder], clear=True)

    # -- table population --------------------------------------------------
    def add_file(self, filepath, state=None, at_index=None):
        try:
            sound = AudioSegment.from_file(filepath)
        except Exception as e:
            self.log_message(f"Could not load {os.path.basename(filepath)}: {e}")
            return None

        dur_ms = len(sound)
        row = {
            "path": filepath,
            "name": os.path.basename(filepath),
            "dur_ms": dur_ms,
            "sr_in": sound.frame_rate,
            "trim_start_ms": 0,
            "trim_end_ms": None,
            "fade_ms": self.opts.get("default_fade_ms", 0),
        }

        r = self.table.rowCount() if at_index is None else at_index
        self.table.insertRow(r)
        self.table.setRowHeight(r, 30)

        sel = QCheckBox()
        row["sel"] = sel
        self.table.setCellWidget(r, 0, center_cell(sel))

        num = QTableWidgetItem(f"{r + 1:03d}")
        num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(r, 1, num)

        name_item = QTableWidgetItem(row["name"])
        name_item.setToolTip(filepath)
        self.table.setItem(r, 2, name_item)

        in_item = QTableWidgetItem(str(sound.frame_rate))
        in_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(r, 3, in_item)

        speed = QComboBox()
        speed.addItems(preset_speeds)
        speed.setCurrentText(self.opts.get("default_speed", "x2.0"))
        row["speed"] = speed
        speed.currentTextChanged.connect(lambda v, d=row: self._apply_combo(d, "speed", v))
        self.table.setCellWidget(r, 4, speed)

        len_item = QTableWidgetItem(f"{dur_ms / 1000:.2f}")
        len_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(r, 5, len_item)

        sr = QComboBox()
        sr.addItems(preset_samplerates)
        sr.setCurrentText("44100")
        row["sr"] = sr
        sr.currentTextChanged.connect(lambda v, d=row: self._apply_combo(d, "sr", v))
        self.table.setCellWidget(r, 6, sr)

        bit = QComboBox()
        bit.addItems(BITRATES)
        bit.setCurrentText("128")
        row["bitrate"] = bit
        bit.currentTextChanged.connect(lambda v, d=row: self._apply_combo(d, "bitrate", v))
        self.table.setCellWidget(r, 7, bit)

        trim_btn = QPushButton(trim_label(0, None, dur_ms, row["fade_ms"]))
        trim_btn.setObjectName("Row")
        row["trim_btn"] = trim_btn
        trim_btn.clicked.connect(lambda _=False, d=row: self.open_trim(d))
        self.table.setCellWidget(r, 8, trim_btn)

        play_btn = QPushButton("▶")
        play_btn.setObjectName("Row")
        play_btn.clicked.connect(lambda _=False, d=row: self.play_row(d))
        self.table.setCellWidget(r, 9, play_btn)

        stop_btn = QPushButton("■")
        stop_btn.setObjectName("Row")
        stop_btn.clicked.connect(stop_audio)
        self.table.setCellWidget(r, 10, stop_btn)

        rev = QCheckBox()
        row["rev"] = rev
        rev.toggled.connect(lambda v, d=row: self._apply_check(d, "rev", v))
        self.table.setCellWidget(r, 11, center_cell(rev))

        dup_btn = QPushButton("⎘")
        dup_btn.setObjectName("Row")
        dup_btn.setToolTip("Duplicate this sample (independent trim)")
        dup_btn.clicked.connect(lambda _=False, d=row: self.duplicate_row(d))
        self.table.setCellWidget(r, 12, dup_btn)

        delete_btn = QPushButton("✖")
        delete_btn.setObjectName("Row")
        delete_btn.clicked.connect(lambda _=False, d=row: self.delete_row(d))
        self.table.setCellWidget(r, 13, delete_btn)

        if at_index is None:
            self.rows.append(row)
        else:
            self.rows.insert(r, row)

        if state:
            self._apply_state(row, state)

        self._renumber()
        return row

    def _apply_state(self, row, state):
        """Apply a saved/duplicated per-row state without firing batch-apply signals."""
        self._set_combo(row["speed"], state.get("speed"))
        self._set_combo(row["sr"], state.get("sr"))
        self._set_combo(row["bitrate"], state.get("bitrate"))
        if "rev" in state:
            row["rev"].blockSignals(True)
            row["rev"].setChecked(bool(state["rev"]))
            row["rev"].blockSignals(False)
        row["trim_start_ms"] = state.get("trim_start_ms") or 0
        row["trim_end_ms"] = state.get("trim_end_ms")
        row["fade_ms"] = state.get("fade_ms", 0) or 0
        row["trim_btn"].setText(
            trim_label(row["trim_start_ms"], row["trim_end_ms"], row["dur_ms"], row["fade_ms"])
        )

    @staticmethod
    def _set_combo(combo, text):
        if text is None:
            return
        combo.blockSignals(True)
        combo.setCurrentText(str(text))
        combo.blockSignals(False)

    def _row_state(self, row):
        """Serialisable snapshot of one row's settings."""
        return {
            "path": row["path"],
            "speed": row["speed"].currentText(),
            "sr": row["sr"].currentText(),
            "bitrate": row["bitrate"].currentText(),
            "rev": row["rev"].isChecked(),
            "trim_start_ms": row.get("trim_start_ms") or 0,
            "trim_end_ms": row.get("trim_end_ms"),
            "fade_ms": row.get("fade_ms", 0) or 0,
        }

    def duplicate_row(self, row):
        if row not in self.rows:
            return
        idx = self.rows.index(row)
        new = self.add_file(row["path"], state=self._row_state(row), at_index=idx + 1)
        if new:
            self.log_message(f"Duplicated '{row['name']}'.")

    def clear_table(self):
        self.table.setRowCount(0)
        self.rows.clear()

    def _renumber(self):
        for i in range(self.table.rowCount()):
            self.table.item(i, 1).setText(f"{i + 1:03d}")

    def delete_row(self, row):
        if row not in self.rows:
            return
        idx = self.rows.index(row)
        self.table.removeRow(idx)
        self.rows.pop(idx)
        self._renumber()
        self.log_message(f"Removed '{row['name']}'.")

    def delete_selected(self):
        selected = [r for r in self.rows if r["sel"].isChecked()]
        for row in selected:
            self.delete_row(row)
        self.log_message(f"{len(selected)} selected file(s) removed.")

    def _set_all_selected(self, value):
        for row in self.rows:
            row["sel"].setChecked(value)

    # -- batch apply to checked rows --------------------------------------
    def _apply_combo(self, source, key, value):
        for row in self.rows:
            if row is not source and row["sel"].isChecked():
                cb = row[key]
                cb.blockSignals(True)
                cb.setCurrentText(value)
                cb.blockSignals(False)

    def _apply_check(self, source, key, value):
        for row in self.rows:
            if row is not source and row["sel"].isChecked():
                c = row[key]
                c.blockSignals(True)
                c.setChecked(value)
                c.blockSignals(False)

    # -- trim --------------------------------------------------------------
    def _on_double_click(self, r, c):
        if 0 <= r < len(self.rows):
            self.open_trim(self.rows[r])

    def open_trim(self, row):
        try:
            dialog = TrimDialog(row, self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load audio:\n{e}")
            return
        if dialog.exec():
            row["trim_btn"].setText(
                trim_label(row["trim_start_ms"], row["trim_end_ms"], row["dur_ms"], row.get("fade_ms", 0))
            )
            self.log_message(
                f"Trim '{row['name']}': "
                f"{(row['trim_start_ms'] or 0) / 1000:.2f}s – "
                f"{(row['trim_end_ms'] if row['trim_end_ms'] is not None else row['dur_ms']) / 1000:.2f}s"
            )

    # -- output / folders --------------------------------------------------
    def change_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        if folder:
            self.output_folder.setText(folder)

    def open_output(self):
        folder = self.output_folder.text()
        if os.path.isdir(folder):
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        else:
            QMessageBox.warning(self, "Folder not found", "The output folder does not exist.")

    # -- conversion --------------------------------------------------------
    def start_conversion(self):
        if not self.rows:
            QMessageBox.information(self, "Nothing to do", "No files loaded for conversion.")
            return
        out_dir = os.path.normpath(self.output_folder.text())
        out_format = self.format_box.currentText()
        channels = 2 if self.mode_box.currentText() == "stereo" else 1
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Output folder could not be created:\n{e}")
            return

        reserved = set()
        jobs = []
        for row in self.rows:
            base = os.path.splitext(os.path.basename(row["path"]))[0]
            output_path = get_unique_output_path(out_dir, base, out_format, reserved)
            ts = row.get("trim_start_ms") or 0
            te = row.get("trim_end_ms")
            clip_ms = (te if te is not None else row["dur_ms"]) - ts
            jobs.append({
                "input_path": row["path"],
                "output_path": output_path,
                "speed": float(row["speed"].currentText().replace("x", "")),
                "samplerate_out": row["sr"].currentText(),
                "reverse": row["rev"].isChecked(),
                "bitrate": row["bitrate"].currentText(),
                "channels": channels,
                "out_format": out_format,
                "input_rate": row.get("sr_in"),
                "trim_start_s": ts / 1000.0 if ts > 0 else None,
                "trim_end_s": te / 1000.0 if te is not None else None,
                "fade_ms": row.get("fade_ms", 0) or 0,
                "clip_dur_s": clip_ms / 1000.0 if clip_ms > 0 else None,
            })

        self.cancel_event.clear()
        self.progress.setValue(0)
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.signals = WorkerSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.finished.connect(self._on_finished)
        self.worker_thread = threading.Thread(
            target=run_conversion, args=(jobs, self.signals, self.cancel_event), daemon=True
        )
        self.worker_thread.start()

    def cancel_conversion(self):
        self.cancel_event.set()
        self.log_message("Cancelling after the current file…")

    def _on_progress(self, done, total, msg):
        self.progress.setValue(int(done / total * 100) if total else 0)
        self.log_message(msg)

    def _on_finished(self, cancelled):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if cancelled:
            QMessageBox.information(self, "Cancelled", "Conversion was cancelled.")
        else:
            QMessageBox.information(self, "Done", "All files have been converted.")

    # -- PO / KO sample chain ---------------------------------------------
    def build_chain(self):
        if not self.rows:
            QMessageBox.information(self, "Nothing to do", "No samples loaded.")
            return
        dialog = ChainDialog(self.rows, self)
        if not dialog.exec():
            return
        gap_ms, max_ms = dialog.gap_ms(), dialog.max_ms()

        out_format = self.format_box.currentText()
        default_name = os.path.join(self.output_folder.text(), f"po_chain.{out_format}")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save chain as", default_name, f"{out_format.upper()} (*.{out_format})"
        )
        if not path:
            return

        self.btn_chain.setEnabled(False)
        self.btn_start.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._render_chain(path, gap_ms, max_ms, out_format)
            self.log_message(f"Chain written: {path}")
            QMessageBox.information(self, "Done", f"Sample chain saved:\n{path}")
        except Exception as e:
            self.log_message(f"Chain failed: {e}")
            QMessageBox.critical(self, "Error", f"Could not build chain:\n{e}")
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_chain.setEnabled(True)
            self.btn_start.setEnabled(True)
            self.progress.setValue(0)

    def _render_chain(self, out_path, gap_ms, max_ms, out_format):
        common_sr = 44100
        channels = 2 if self.mode_box.currentText() == "stereo" else 1
        gap = (AudioSegment.silent(duration=gap_ms, frame_rate=common_sr).set_channels(channels)
               if gap_ms > 0 else None)
        tmpdir = tempfile.mkdtemp(prefix="abc_chain_")
        n = len(self.rows)
        try:
            parts = []
            for i, row in enumerate(self.rows):
                ts = row.get("trim_start_ms") or 0
                te = row.get("trim_end_ms")
                clip_ms = (te if te is not None else row["dur_ms"]) - ts
                tmp = os.path.join(tmpdir, f"{i:03d}.wav")
                job = {
                    "input_path": row["path"],
                    "output_path": tmp,
                    "speed": float(row["speed"].currentText().replace("x", "")),
                    "samplerate_out": str(common_sr),
                    "reverse": row["rev"].isChecked(),
                    "bitrate": "320",
                    "channels": channels,
                    "out_format": "wav",
                    "input_rate": row.get("sr_in"),
                    "trim_start_s": ts / 1000.0 if ts > 0 else None,
                    "trim_end_s": te / 1000.0 if te is not None else None,
                    "fade_ms": row.get("fade_ms", 0) or 0,
                    "clip_dur_s": clip_ms / 1000.0 if clip_ms > 0 else None,
                }
                subprocess.run(build_ffmpeg_cmd(job), check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               creationflags=NO_WINDOW)
                seg = AudioSegment.from_file(tmp).set_frame_rate(common_sr).set_channels(channels)
                if max_ms:
                    seg = seg[:max_ms]
                if gap is not None and parts:
                    parts.append(gap)
                parts.append(seg)
                self.progress.setValue(int((i + 1) / n * 100))
                QApplication.processEvents()

            combined = parts[0]
            for p in parts[1:]:
                combined += p
            combined = combined.set_frame_rate(common_sr).set_channels(channels).set_sample_width(2)
            export_params = {"bitrate": "320k"} if out_format == "mp3" else {}
            combined.export(out_path, format=out_format, **export_params)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def closeEvent(self, event):
        stop_audio()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)

    if os.path.exists(FONT_PATH):
        fid = QFontDatabase.addApplicationFont(FONT_PATH)
        fams = QFontDatabase.applicationFontFamilies(fid)
        if fams:
            app.setFont(QFont(fams[0], 10))
    app.setStyleSheet(QSS)

    try:
        check_ffmpeg()
    except EnvironmentError as e:
        QMessageBox.critical(None, "ffmpeg missing", str(e))
        return

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
