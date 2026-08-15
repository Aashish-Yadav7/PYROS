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
import pygame

# Mixer is initialized ONCE, not per-call - this is what makes stopping
# mid-sentence actually reliable instead of fragile.
_mixer_ready = False
try:
    pygame.mixer.init()
    _mixer_ready = True
except Exception as e:
    print(f"[voice] Audio device init failed ({e}) - voice output disabled until fixed.")

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

    try:
        pa = pyaudio.PyAudio()
        stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"[voice] Could not open microphone: {e}")
        print("[voice] Check: is a microphone connected? Does Windows have mic "
              "permissions enabled for this app? Settings > Privacy > Microphone.")
        return ""

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
    if not audio_path:
        return ""
    return transcribe_audio(audio_path)


# ---------- TEXT-TO-SPEECH (swappable engine) ----------

DEFAULT_EDGE_VOICE = "en-US-AriaNeural"  # natural-sounding, good default


def stop_speaking() -> None:
    """
    Immediately stop whatever Pyros is currently saying. Safe to call
    even if nothing is playing. This is what makes her interruptible.
    """
    if not _mixer_ready:
        return
    try:
        pygame.mixer.music.stop()
    except Exception as e:
        print(f"[voice] stop_speaking error (harmless if nothing was playing): {e}")


def is_speaking() -> bool:
    """True if Pyros is currently in the middle of saying something."""
    if not _mixer_ready:
        return False
    try:
        return pygame.mixer.music.get_busy()
    except Exception:
        return False


def _speak_edge_tts(text: str) -> None:
    """Speak text using edge-tts (cloud, free, no GPU needed)."""
    if not _mixer_ready:
        print("[voice] Can't speak - no audio device available.")
        return

    import edge_tts

    async def _generate_and_play():
        temp_path = os.path.join(tempfile.gettempdir(), "pyros_speech.mp3")
        # rate="+8%" tightens the awkward pauses edge-tts adds at commas/
        # periods by default, making delivery feel less choppy/robotic.
        communicate = edge_tts.Communicate(text, DEFAULT_EDGE_VOICE, rate="+8%")
        await communicate.save(temp_path)

        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

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
        model = _get_chatterbox_model()
        wav = model.generate(text)
        temp_path = os.path.join(tempfile.gettempdir(), "pyros_speech_chatterbox.wav")
        model.save_audio(wav, temp_path)

        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)

    except Exception as e:
        print(f"[voice] Chatterbox unavailable ({e}), falling back to edge_tts.")
        _speak_edge_tts(text)


_vibevoice_model = None
_vibevoice_processor = None


def _get_vibevoice_model():
    """
    Loads VibeVoice-Streaming-0.5B (real-time, single-speaker model).
    Needs the repo cloned and installed first - see _speak_vibevoice below.
    """
    global _vibevoice_model, _vibevoice_processor
    if _vibevoice_model is None:
        from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
        from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
        print("[voice] Loading VibeVoice-Streaming-0.5B (needs GPU)...")
        model_path = "microsoft/VibeVoice-Realtime-0.5B"
        _vibevoice_processor = VibeVoiceProcessor.from_pretrained(model_path)
        _vibevoice_model = VibeVoiceForConditionalGenerationInference.from_pretrained(
            model_path, torch_dtype="auto", device_map="cuda"
        )
    return _vibevoice_model, _vibevoice_processor


def _speak_vibevoice(text: str, speaker_name: str = "Samuel") -> None:
    """
    Speak text using VibeVoice 1.5B - either a REMOTE Colab server (see
    colab_voice_server.py, since your current laptop has no GPU) or a LOCAL
    install once you have a GPU laptop. Falls back to edge_tts automatically
    if neither is available.

    TO USE VIA COLAB (works on your current laptop):
    1. Run colab_voice_server.py in Google Colab (free T4 GPU)
    2. Copy the printed URL into .env as: VIBEVOICE_API_URL=<url>
    3. Set TTS_ENGINE=vibevoice in .env
    This function automatically detects and uses the remote server.

    TO USE LOCALLY (once you have a GPU laptop):
    1. git clone https://github.com/Aashish-Yadav7/VibeVoice7.git
    2. cd VibeVoice7 && pip install -e .
    3. Don't set VIBEVOICE_API_URL - it'll load the model locally instead.
    """
    api_url = getattr(config, "VIBEVOICE_API_URL", None)

    if api_url:
        _speak_vibevoice_remote(text, api_url, speaker_name)
    else:
        _speak_vibevoice_local(text, speaker_name)


def _speak_vibevoice_remote(text: str, api_url: str, speaker_name: str) -> None:
    """Calls a Colab-hosted VibeVoice server over HTTP, authenticated."""
    try:
        import requests

        api_secret = getattr(config, "VIBEVOICE_API_SECRET", "")
        response = requests.post(
            f"{api_url.rstrip('/')}/speak",
            json={"text": text, "speaker": speaker_name},
            headers={"X-API-Secret": api_secret},
            timeout=30,
        )
        response.raise_for_status()

        temp_path = os.path.join(tempfile.gettempdir(), "pyros_speech_vibevoice_remote.wav")
        with open(temp_path, "wb") as f:
            f.write(response.content)

        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)

    except Exception as e:
        print(f"[voice] Colab VibeVoice server unreachable ({e}) - is the "
              f"Colab notebook still running? Falling back to edge_tts.")
        _speak_edge_tts(text)


def _speak_vibevoice_local(text: str, speaker_name: str) -> None:
    """Loads and runs VibeVoice directly on this machine (needs a real GPU)."""
    try:
        import torch
        import soundfile as sf

        model, processor = _get_vibevoice_model()
        inputs = processor(text=[text], voice_samples=[speaker_name], return_tensors="pt")
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=None, cfg_scale=1.5)

        temp_path = os.path.join(tempfile.gettempdir(), "pyros_speech_vibevoice.wav")
        sf.write(temp_path, output.speech_outputs[0].cpu().numpy(), 24000)

        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)

    except Exception as e:
        print(f"[voice] Local VibeVoice unavailable ({e}), falling back to edge_tts.")
        _speak_edge_tts(text)


def speak(text: str) -> None:
    """
    Speak the given text out loud, using whichever engine is set as
    TTS_ENGINE in .env ("edge_tts", "chatterbox", or "vibevoice").
    Defaults to edge_tts if not set, since that works on any machine
    with no GPU required.
    """
    stop_speaking()
    engine = getattr(config, "TTS_ENGINE", "edge_tts")
    if engine == "chatterbox":
        _speak_chatterbox(text)
    elif engine == "vibevoice":
        _speak_vibevoice(text)
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