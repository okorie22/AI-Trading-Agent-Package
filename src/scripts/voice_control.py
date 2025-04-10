import whisper
import sounddevice as sd
import numpy as np
import queue
import os

# Load the model
model = whisper.load_model("small")

# Queue to store audio data
q = queue.Queue()

def callback(indata, frames, time, status):
    """Callback function to store recorded audio in the queue"""
    if status:
        print(status)
    q.put(indata.copy())

def record_audio(duration=5, samplerate=16000):
    """Records audio and returns numpy array"""
    with sd.InputStream(callback=callback, samplerate=samplerate, channels=1):
        print("Listening...")
        audio_data = []
        for _ in range(int(duration * samplerate / 1024)): 
            audio_data.append(q.get())
        print("Recording complete")
    return np.concatenate(audio_data, axis=0)

def transcribe_audio():
    """Records and transcribes voice input"""
    audio = record_audio()
    np.save("temp_audio.npy", audio)
    os.system("ffmpeg -f f32le -ar 16000 -ac 1 -i temp_audio.npy temp_audio.wav -y")
    result = model.transcribe("temp_audio.wav")
    return result["text"]

# Capture voice input and print transcription
command = transcribe_audio()
print(f"You said: {command}")
