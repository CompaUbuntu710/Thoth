import os
import subprocess
import json
import tempfile

try:
    from vosk import Model, KaldiRecognizer
    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False

MODEL_PATH = os.path.join(os.path.dirname(__file__), "vosk-model-small-es-0.42")

_model = None

def _get_model():
    global _model
    if _model is None:
        if not HAS_VOSK:
            raise RuntimeError("Vosk no instalado: pip install vosk")
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError(f"Modelo no encontrado en {MODEL_PATH}")
        _model = Model(MODEL_PATH)
    return _model


def record_audio(duration=5, samplerate=16000):
    path = os.path.join(tempfile.gettempdir(), "thoth_stt.wav")
    subprocess.run(
        ["arecord", "-d", str(duration), "-f", "S16_LE", "-r", str(samplerate), "-c", "1", path],
        capture_output=True,
        timeout=duration + 5,
    )
    if not os.path.exists(path):
        return None
    return path


def transcribe(path=None, duration=5):
    if path is None:
        path = record_audio(duration=duration)
    if path is None:
        return "[Error: no se pudo grabar audio]"
    model = _get_model()
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(False)
    with open(path, "rb") as f:
        while True:
            data = f.read(4000)
            if len(data) == 0:
                break
            rec.AcceptWaveform(data)
    result = json.loads(rec.FinalResult())
    text = result.get("text", "").strip()
    return text if text else "[No te escuché]"


def listen(duration=5):
    print(f"\n🎤 Escuchando ({duration}s)...")
    text = transcribe(duration=duration)
    print(f"   → {text}")
    return text
