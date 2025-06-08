import os
import platform
import signal
import subprocess
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from pydub import AudioSegment
from tkinterdnd2 import TkinterDnD, DND_FILES
import sys

def check_ffmpeg():
    from shutil import which
    if which("ffmpeg") is None or which("ffprobe") is None or which("ffplay") is None:
        raise EnvironmentError(
            "❌ ffmpeg, ffprobe ffplay  not found.\nPlease ensure C:\\ffmpeg\\bin is in your PATH."
        )
check_ffmpeg()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

app = TkinterDnD.Tk()
app.title("Audio Batch Converter made by Jan Schulten")


BASEDIR = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
ICON_PATH = os.path.join(BASEDIR, "vinyl_mixer.ico")
try:
    app.iconbitmap(ICON_PATH)
except Exception as e:
    print(f"Could not set window icon: {e}")

app.geometry("1100x760")
app.configure(bg="#2B2B2B")

SUPPORTED_FORMATS = ('.wav', '.mp3', '.aiff', '.aif')
audio_data = []
current_playback_process = None

default_output_folder = os.path.join(os.path.expanduser('~'), 'converted_audio')
os.makedirs(default_output_folder, exist_ok=True)
output_folder_var = ctk.StringVar(value=default_output_folder)

output_format_var = ctk.StringVar(value="wav")
stereo_mono_var = ctk.StringVar(value="stereo")

BITRATES = ["64", "96", "128", "160", "192", "256", "320"]
preset_speeds = [f"x{round(x,2)}" for x in [0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]]
preset_samplerates = [
    "8000", "11025", "16000", "22050", "32000", "44100",
    "48000", "88200", "96000", "176400", "192000"
]

headers = [
    "Select", "Name", "Sample Rate", "Speed", "Length(s)",
    "Sample Rate Out", "Bitrate", "", "Play", "Stop", "Reverse", "Pitch", "❌"
]
columns = [[] for _ in headers]

log_messages = []
def log_message(msg):
    log_messages.append(msg)
    log_text.configure(state="normal")
    log_text.delete("1.0", tk.END)
    log_text.insert(tk.END, "\n".join(log_messages[-200:]))
    log_text.configure(state="disabled")

def play_audio(path):
    global current_playback_process
    try:
        stop_audio()
        current_playback_process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        log_message(f"Error playing: {e}")
        messagebox.showerror("Error", f"Playback not possible:\n{e}")

def stop_audio():
    global current_playback_process
    if current_playback_process and current_playback_process.poll() is None:
        try:
            current_playback_process.send_signal(signal.SIGTERM)
        except Exception as e:
            log_message(f"Error stopping ffplay: {e}")
    current_playback_process = None

def open_output_folder():
    folder = output_folder_var.get()
    if os.path.isdir(folder):
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    else:
        messagebox.showwarning("Folder not found", "The output folder does not exist.")

def get_unique_output_path(output_dir, base, ext):
    count = 0
    while True:
        if count == 0:
            filename = f"{base}_converted.{ext}"
        else:
            filename = f"{base}_converted_{count}.{ext}"
        output_path = os.path.join(output_dir, filename)
        if not os.path.exists(output_path):
            return output_path
        count += 1

def convert_files():
    if not audio_data:
        messagebox.showinfo("Attenzione!", "No files loaded for conversion.")
        return

    total = len(audio_data)
    progress_bar.configure(mode="determinate")
    for i, data in enumerate(audio_data):
        input_path = data["path"]
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = os.path.normpath(output_folder_var.get())
        ext = output_format_var.get()
        output_path = get_unique_output_path(output_dir, base, ext)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        speed = float(data["speed_var"].get().replace("x", ""))
        samplerate_out = data["sr_out_var"].get()
        reverse = data["reverse_var"].get()
        pitch = data["pitch_var"].get()
        bitrate = data["bitrate_var"].get()
        channels = 2 if stereo_mono_var.get() == "stereo" else 1

        cmd = ["ffmpeg", "-y", "-i", input_path]
        filters = []
        if reverse:
            filters.append("areverse")
        if speed < 0.5:
            tempos = []
            s = speed
            while s < 0.5:
                tempos.append("0.5")
                s *= 2
            tempos.append(f"{round(s, 4)}")
            filters.extend([f"atempo={t}" for t in tempos])
        elif speed <= 100.0:
            filters.append(f"atempo={speed}")
        if pitch:
            filters.append(f"asetrate={samplerate_out}*1.05946,aresample={samplerate_out}")
        if filters:
            cmd += ["-af", ",".join(filters)]
        cmd += ["-ar", samplerate_out, "-ac", str(channels)]

        if output_format_var.get() == "mp3":
            cmd += ["-b:a", f"{bitrate}k"]
        elif output_format_var.get() == "aiff":
            cmd += ["-sample_fmt", "s16"]

        cmd.append(output_path)
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log_message(f"File '{input_path}' converted to '{output_path}'")
        except Exception as e:
            log_message(f"Error converting from {input_path}: {e}")
            messagebox.showerror("Error", f"Error converting :\n{input_path}\n{e}")

        progress_var.set((i + 1) / total)
        app.update_idletasks()

    messagebox.showinfo("Done", "All files have been converted.")

def refresh_table():
    
    pass

def delete_row(index):
    for col in columns:
        if index < len(col):
            widget = col.pop(index)
            if widget:
                widget.destroy()
    if index < len(audio_data):
        audio_data.pop(index)
    log_message(f"File in row {index+1} deleted.")

def select_all():
    for data in audio_data:
        data["select_var"].set(True)

def deselect_all():
    for data in audio_data:
        data["select_var"].set(False)

def delete_selected():
    indices = [i for i, data in enumerate(audio_data) if data["select_var"].get()]
    for idx in sorted(indices, reverse=True):
        delete_row(idx)
    log_message(f"{len(indices)} selected file(s) deleted.")

def batch_update_speed(new_value, source_idx):
    for idx, data in enumerate(audio_data):
        if data["select_var"].get() and idx != source_idx:
            data["speed_var"].set(new_value)

def batch_update_samplerate(new_value, source_idx):
    for idx, data in enumerate(audio_data):
        if data["select_var"].get() and idx != source_idx:
            data["sr_out_var"].set(new_value)

def batch_update_bitrate(new_value, source_idx):
    for idx, data in enumerate(audio_data):
        if data["select_var"].get() and idx != source_idx:
            data["bitrate_var"].set(new_value)

def batch_update_reverse(new_value, source_idx):
    for idx, data in enumerate(audio_data):
        if data["select_var"].get() and idx != source_idx:
            data["reverse_var"].set(new_value)

def batch_update_pitch(new_value, source_idx):
    for idx, data in enumerate(audio_data):
        if data["select_var"].get() and idx != source_idx:
            data["pitch_var"].set(new_value)

def add_file_to_table(filepath):
    try:
        sound = AudioSegment.from_file(filepath)
        samplerate = sound.frame_rate
        duration = round(len(sound) / 1000, 2)

        select_var = tk.BooleanVar(value=False)
        select_checkbox = ctk.CTkCheckBox(table_frame, text="", variable=select_var)

        speed_var = ctk.StringVar(value="x2.0")
        def on_speed_change(new_value, idx=len(audio_data)):
            batch_update_speed(new_value, idx)
        speed_menu = ctk.CTkOptionMenu(
            table_frame, values=preset_speeds, variable=speed_var,
            command=on_speed_change
        )

        name_label = ctk.CTkLabel(table_frame, text=os.path.basename(filepath))
        samplerate_label = ctk.CTkLabel(table_frame, text=str(samplerate))

        sr_out_var = ctk.StringVar(value="44100")
        def on_samplerate_change(new_value, idx=len(audio_data)):
            batch_update_samplerate(new_value, idx)
        sr_menu = ctk.CTkOptionMenu(
            table_frame, values=preset_samplerates, variable=sr_out_var,
            command=on_samplerate_change
        )

        bitrate_var = ctk.StringVar(value="128")
        def on_bitrate_change(new_value, idx=len(audio_data)):
            batch_update_bitrate(new_value, idx)
        bitrate_menu = ctk.CTkOptionMenu(
            table_frame, values=BITRATES, variable=bitrate_var,
            command=on_bitrate_change
        )

        length_label = ctk.CTkLabel(table_frame, text=str(duration))
        placeholder_label = ctk.CTkLabel(table_frame, text="-")
        play_button = ctk.CTkButton(table_frame, text="▶", width=30, command=lambda: play_audio(filepath))
        stop_button = ctk.CTkButton(table_frame, text="■", width=30, command=stop_audio)

        reverse_var = tk.BooleanVar()
        def on_reverse_change():
            batch_update_reverse(reverse_var.get(), len(audio_data))
        reverse_checkbox = ctk.CTkCheckBox(table_frame, text="", variable=reverse_var, command=on_reverse_change)

        pitch_var = tk.BooleanVar(value=True)
        def on_pitch_change():
            batch_update_pitch(pitch_var.get(), len(audio_data))
        pitch_checkbox = ctk.CTkCheckBox(table_frame, text="", variable=pitch_var, command=on_pitch_change)

        idx = len(audio_data)
        delete_button = ctk.CTkButton(table_frame, text="✖", width=30, command=lambda idx=idx: delete_row(idx))

        widgets = [
            select_checkbox, name_label, samplerate_label, speed_menu, length_label,
            sr_menu, bitrate_menu, placeholder_label,
            play_button, stop_button, reverse_checkbox, pitch_checkbox, delete_button
        ]

        for i, widget in enumerate(widgets):
            widget.grid(row=len(audio_data)+1, column=i, padx=5, pady=2)
            columns[i].append(widget)

        audio_data.append({
            "select_var": select_var,
            "name": os.path.basename(filepath),
            "path": filepath,
            "samplerate": samplerate,
            "duration": duration,
            "speed_var": speed_var,
            "sr_out_var": sr_out_var,
            "bitrate_var": bitrate_var,
            "reverse_var": reverse_var,
            "pitch_var": pitch_var,
        })

    except Exception as e:
        log_message(f"File could not be loaded: {filepath}\n{e}")
        messagebox.showerror("Error", f"File could not be loaded: {filepath}\n{e}")

def load_files():
    folder = filedialog.askdirectory()
    if folder:
        for col in columns:
            for widget in col:
                if hasattr(widget, "destroy"):
                    widget.destroy()
            col.clear()
        audio_data.clear()
        skipped_files = []
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path) and full_path.lower().endswith(SUPPORTED_FORMATS):
                add_file_to_table(full_path)
            else:
                skipped_files.append(full_path)
        if skipped_files:
            msg = "Some files were skipped:\n" + "\n".join(skipped_files)
            log_message(msg)
            messagebox.showinfo("Files skipped", msg)

def handle_drop(event):
    loading_progress_bar.pack(fill="x", padx=20, pady=10)
    loading_progress_bar.start()
    app.update_idletasks()
    paths = app.tk.splitlist(event.data)
    skipped_files = []
    for col in columns:
        for widget in col:
            if hasattr(widget, "destroy"):
                widget.destroy()
        col.clear()
    audio_data.clear()
    for path in paths:
        if os.path.isdir(path):
            for file in os.listdir(path):
                full_path = os.path.join(path, file)
                if os.path.isfile(full_path) and full_path.lower().endswith(SUPPORTED_FORMATS):
                    add_file_to_table(full_path)
                else:
                    skipped_files.append(full_path)
        elif os.path.isfile(path) and path.lower().endswith(SUPPORTED_FORMATS):
            add_file_to_table(path)
        else:
            skipped_files.append(path)
    loading_progress_bar.stop()
    loading_progress_bar.pack_forget()
    if skipped_files:
        msg = "Some files were skipped:\n" + "\n".join(skipped_files)
        log_message(msg)
        messagebox.showinfo("Files skipped", msg)

outer_frame = ctk.CTkFrame(app)
outer_frame.pack(fill="both", expand=True, padx=20, pady=10)
outer_frame.drop_target_register(DND_FILES)
outer_frame.dnd_bind('<<Drop>>', handle_drop)

table_frame = ctk.CTkScrollableFrame(outer_frame)
table_frame.pack(fill="both", expand=True)

spaltenbreiten = [40, 140, 60, 60, 70, 100, 70, 40, 60, 60, 60, 60, 60]
for i, breite in enumerate(spaltenbreiten):
    table_frame.grid_columnconfigure(i, minsize=breite)

for i, header in enumerate(headers):
    lbl = ctk.CTkLabel(table_frame, text=header, font=("Courier", 14))
    lbl.grid(row=0, column=i, padx=10, pady=5)

controls_frame = ctk.CTkFrame(app)
controls_frame.pack(fill="x", padx=20, pady=(10, 0))

row1 = ctk.CTkFrame(controls_frame)
row1.pack(fill="x", pady=5)
ctk.CTkButton(row1, text="📂 Input folder", command=load_files).pack(side="left", padx=5)
ctk.CTkLabel(row1, text="📁 Output folder:").pack(side="left", padx=5)
ctk.CTkEntry(row1, textvariable=output_folder_var, width=300).pack(side="left", padx=5)

def change_output_folder():
    folder = filedialog.askdirectory()
    if folder:
        output_folder_var.set(folder)

ctk.CTkButton(row1, text="Change", command=change_output_folder).pack(side="left", padx=5)
ctk.CTkLabel(row1, text="Format:").pack(side="left", padx=5)
ctk.CTkOptionMenu(row1, values=["wav", "mp3", "aiff"], variable=output_format_var, width=80).pack(side="left", padx=5)
ctk.CTkLabel(row1, text="Mode:").pack(side="left", padx=5)
ctk.CTkOptionMenu(row1, values=["stereo", "mono"], variable=stereo_mono_var, width=80).pack(side="left", padx=5)

row2 = ctk.CTkFrame(controls_frame)
row2.pack(fill="x", pady=5)
ctk.CTkButton(row2, text="Start", command=convert_files).pack(side="left", padx=5)
ctk.CTkButton(row2, text="Open output folder", command=open_output_folder).pack(side="left", padx=5)
ctk.CTkButton(row2, text="Select all", command=select_all).pack(side="left", padx=5)
ctk.CTkButton(row2, text="Deselect all", command=deselect_all).pack(side="left", padx=5)
ctk.CTkButton(row2, text="Delete selected", command=delete_selected).pack(side="left", padx=5)

progress_var = ctk.DoubleVar()
progress_bar = ctk.CTkProgressBar(app, variable=progress_var)
progress_bar.pack(fill="x", padx=20, pady=10)

loading_progress_bar = ctk.CTkProgressBar(app, mode="indeterminate")

ascii_art = r"""
  __                    __  .__                    .__       .__     
_/  |______  ___  ___ _/  |_|  |__   ____   _______|__| ____ |  |__  
\   __\__  \ \  \/  / \   __\  |  \_/ __ \  \_  __ \  |/ ___\|  |  \ 
 |  |  / __ \_>    <   |  | |   Y  \  ___/   |  | \/  \  \___|   Y  \
 |__| (____  /__/\_ \  |__| |___|  /\___  >  |__|  |__|\___  >___|  /
           \/      \/            \/     \/                 \/     \/  
"""
ctk.CTkLabel(app, text=ascii_art, font=ctk.CTkFont("Courier", size=12), text_color="lime").pack(pady=(0, 5))

log_text = tk.Text(app, height=7, state="disabled", bg="#232323", fg="lime", font=("Courier", 10))
log_text.pack(fill="x", padx=20, pady=(0, 10))

app.mainloop()
