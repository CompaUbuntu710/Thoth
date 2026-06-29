import os
import subprocess
import struct
import wave
import tempfile

VOICE_DIR = os.path.join(os.path.dirname(__file__), "piper_voices")

try:
    import piper
    import numpy as np
    HAS_PIPER = True
except ImportError:
    HAS_PIPER = False

try:
    import pyttsx3
    HAS_ESPEAK = True
except ImportError:
    HAS_ESPEAK = False

_piper_voice = None
_piper_config = None
_espeak_engine = None


def _get_piper():
    global _piper_voice
    if _piper_voice is None and HAS_PIPER:
        onnx_paths = [f for f in os.listdir(VOICE_DIR) if f.endswith(".onnx")] if os.path.isdir(VOICE_DIR) else []
        if onnx_paths:
            model_path = os.path.join(VOICE_DIR, onnx_paths[0])
            config_path = model_path + ".json"
            _piper_voice = piper.PiperVoice.load(model_path, config_path=config_path)
    return _piper_voice


def _get_espeak():
    global _espeak_engine
    if _espeak_engine is None and HAS_ESPEAK:
        _espeak_engine = pyttsx3.init()
        voices = _espeak_engine.getProperty("voices")
        for v in voices:
            if v.languages and any(l.startswith("es") for l in v.languages):
                _espeak_engine.setProperty("voice", v.id)
                break
        _espeak_engine.setProperty("rate", 160)
        _espeak_engine.setProperty("volume", 0.9)
    return _espeak_engine


def speak(text):
    voice = _get_piper()
    if voice:
        try:
            chunks = list(voice.synthesize(text))
            if not chunks:
                raise ValueError("No audio generated")
            audio = np.concatenate([c.audio_float_array for c in chunks])
            audio_int16 = (audio * 32767).astype(np.int16)
            sr = chunks[0].sample_rate
            wav_path = os.path.join(tempfile.gettempdir(), "thoth_tts.wav")
            with wave.open(wav_path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes(audio_int16.tobytes())
            subprocess.run(["aplay", wav_path], capture_output=True)
            return
        except Exception:
            pass
    engine = _get_espeak()
    if engine:
        engine.say(text)
        engine.runAndWait()


def say_thoth(reply):
    speak(reply)
