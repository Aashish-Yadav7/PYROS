"""
voice.py
Gives Pyros ears (speech-to-text via Whisper) and a voice (text-to-speech,
swappable between edge-tts and Chatterbox).

SPEECH-TO-TEXT: Whisper "small" model - good accuracy, runs fine on CPU,
no GPU needed. First run downloads the model (~244MB), then it's cached
locally and loads fast every time after.

TEXT-TO-SPEECH: swappable engine, set in .env as TTS_ENGINE:
- "edge_tts" (default) - free, cloud-based, natural voice, zero GPU needed.
  Works on any machine right now.
- "chatterbox" - much higher quality, voice cloning, emotion control, but
  needs a real GPU (several GB VRAM). Only usable once you have one.
  If chatterbox isn't installed/available, automatically falls back to
  edge_tts so nothing breaks.
"""

import os
import asyncio
import tempfile

import config

# ---------- SPEECH-TO-TEXT (Whisper) ----------

_whisper_model = None  # lazy-loaded once, reused after


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print("[voice] Loading Whisper 'small' model (first run downloads it, ~244MB)...")
        _whisper_model = whisper.load_model("small")
        print("[voice] Whisper model loaded.")
    return _whisper_model


def transcribe_audio(audio_path: str) -> str:
    """
    Convert a recorded audio file (wav/mp3/etc.) into text using Whisper.
    Returns the transcribed text, or an empty string if it fails.
    """
    try:
        model = _get_whisper_model()
        result = model.transcribe(audio_path)
        return result.get("text", "").strip()
    except Exception as e:
        print(f"[voice] Transcription failed: {e}")
        return ""


def record_from_microphone(duration_seconds: int = 5) -> str:
    """
    Records audio from the default microphone for a fixed duration,
    saves it to a temp wav file, and returns the file path.
    """
    import pyaudio
    import wave

    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000  # Whisper expects 16kHz

    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print(f"[voice] Recording for {duration_seconds}s...")
    frames = []
    for _ in range(int(RATE / CHUNK * duration_seconds)):
        frames.append(stream.read(CHUNK, exception_on_overflow=False))
    print("[voice] Recording done.")

    stream.stop_stream()
    stream.close()
    pa.terminate()

    temp_path = os.path.join(tempfile.gettempdir(), "pyros_recording.wav")
    with wave.open(temp_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pa.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

    return temp_path


def listen(duration_seconds: int = 5) -> str:
    """Record from mic and transcribe in one step. Returns the spoken text."""
    audio_path = record_from_microphone(duration_seconds)
    return transcribe_audio(audio_path)


# ---------- TEXT-TO-SPEECH (swappable engine) ----------

DEFAULT_EDGE_VOICE = "en-US-AriaNeural"  # natural-sounding, good default


def _speak_edge_tts(text: str) -> None:
    """Speak text using edge-tts (cloud, free, no GPU needed)."""
    import edge_tts
    import pygame

    async def _generate_and_play():
        temp_path = os.path.join(tempfile.gettempdir(), "pyros_speech.mp3")
        communicate = edge_tts.Communicate(text, DEFAULT_EDGE_VOICE)
        await communicate.save(temp_path)

        pygame.mixer.init()
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        pygame.mixer.quit()

    asyncio.run(_generate_and_play())


_chatterbox_model = None


def _get_chatterbox_model():
    global _chatterbox_model
    if _chatterbox_model is None:
        from chatterbox.tts import ChatterboxTTS
        print("[voice] Loading Chatterbox-Turbo model (needs GPU)...")
        _chatterbox_model = ChatterboxTTS.from_pretrained(device="cuda")
    return _chatterbox_model


def _speak_chatterbox(text: str) -> None:
    """
    Speak text using Chatterbox-Turbo (much higher quality, needs a real GPU).
    Falls back to edge_tts automatically if Chatterbox isn't installed or
    fails to load (e.g. no GPU available yet).

    TO ACTIVATE once you have a GPU laptop:
    1. pip install chatterbox-tts
    2. Set TTS_ENGINE=chatterbox in .env
    3. This function will then be used automatically instead of edge_tts.
    """
    try:
        import pygame

        model = _get_chatterbox_model()
        wav = model.generate(text)
        temp_path = os.path.join(tempfile.gettempdir(), "pyros_speech_chatterbox.wav")
        model.save_audio(wav, temp_path)

        pygame.mixer.init()
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pass
        pygame.mixer.quit()

    except Exception as e:
        print(f"[voice] Chatterbox unavailable ({e}), falling back to edge_tts.")
        _speak_edge_tts(text)


def speak(text: str) -> None:
    """
    Speak the given text out loud, using whichever engine is set as
    TTS_ENGINE in .env ("edge_tts" or "chatterbox"). Defaults to edge_tts
    if not set, since that works on any machine with no GPU required.
    """
    engine = getattr(config, "TTS_ENGINE", "edge_tts")
    if engine == "chatterbox":
        _speak_chatterbox(text)
    else:
        _speak_edge_tts(text)


# --- Quick manual test ---
if __name__ == "__main__":
    print("Testing voice.py")
    print("Current TTS engine:", getattr(config, "TTS_ENGINE", "edge_tts"))

    test_text = "Hey Boss, this is a test of my voice."
    print(f"Speaking: {test_text!r}")
    speak(test_text)

    print("\nNow testing microphone input - say something in the next 5 seconds...")
    heard = listen(duration_seconds=5)
    print(f"Whisper heard: {heard!r}")