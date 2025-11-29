import threading
import json
import time
import tkinter as tk
from tkinter import scrolledtext
from vosk import Model, KaldiRecognizer
import pyaudio

# -----------------------
# GLOBALS
# -----------------------
listening = False
audio_thread = None
recognizer = None
stream = None
mic = None
last_partial = ""
last_update_time = 0

# -----------------------
# PRELOAD MODEL (important!)
# -----------------------
print("Loading Vosk model... this can take a moment.")
model = Model("path") #CHANGE TO WHERE THE PATH OF vosk-small-model-en-us-0.15 IS 
recognizer = KaldiRecognizer(model, 16000)
print("Model loaded.")

# -----------------------
# TKINTER GUI SETUP
# -----------------------
root = tk.Tk()
root.title("Live Speech Recognition")

# wrap=tk.NONE = faster
text_box = scrolledtext.ScrolledText(root, wrap=tk.NONE, font=("Arial", 14), width=60, height=20)
text_box.pack(padx=10, pady=10)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

start_btn = tk.Button(btn_frame, text="Start Listening", font=("Arial", 12), width=15)
stop_btn = tk.Button(btn_frame, text="Stop Listening", font=("Arial", 12), width=15)


# -----------------------
# UI FUNCTIONS
# -----------------------
def update_partial(new_text):
    """Update only when text changes."""
    global last_partial

    if not new_text:
        return

    if new_text == last_partial:
        return  # Prevent unnecessary UI work

    # Remove old partial
    if last_partial:
        text_box.delete("end-1c linestart", "end-1c")

    # Insert the new partial
    text_box.insert(tk.END, new_text)
    text_box.see(tk.END)

    last_partial = new_text


def throttled_update_partial(new_text):
    """Limit updates to every 60ms to reduce GUI overhead."""
    global last_update_time
    now = time.time()

    if now - last_update_time < 0.06:  # 60 milliseconds
        return

    last_update_time = now
    update_partial(new_text)


def add_final_text(final_text):
    """Insert final recognized text and remove partial."""
    global last_partial

    if last_partial:
        text_box.delete("end-1c linestart", "end-1c")
        last_partial = ""

    text_box.insert(tk.END, final_text + "\n")
    text_box.see(tk.END)


# -----------------------
# LISTENING THREAD
# -----------------------
def listening_loop():
    global listening, stream, mic, recognizer

    mic = pyaudio.PyAudio()

    # Smaller buffer = quicker updates
    buffer_size = 1600

    stream = mic.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=buffer_size
    )
    stream.start_stream()

    while listening:
        data = stream.read(buffer_size, exception_on_overflow=False)

        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")
            root.after(0, add_final_text, text)
        else:
            partial = json.loads(recognizer.PartialResult())
            text = partial.get("partial", "")
            root.after(0, throttled_update_partial, text)

    # clean up
    stream.stop_stream()
    stream.close()
    mic.terminate()


# -----------------------
# START / STOP BUTTONS
# -----------------------
def start_listening():
    global listening, audio_thread

    if listening:
        return

    listening = True
    audio_thread = threading.Thread(target=listening_loop, daemon=True)
    audio_thread.start()


def stop_listening():
    global listening
    listening = False


start_btn.config(command=start_listening)
stop_btn.config(command=stop_listening)

start_btn.grid(row=0, column=0, padx=10)
stop_btn.grid(row=0, column=1, padx=10)


# -----------------------
# RUN TKINTER
# -----------------------
root.mainloop()
