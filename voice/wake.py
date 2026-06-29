import os
import subprocess
import json
import tempfile
import struct
import math

WAKE_WORDS = ["thoth", "hey", "ok thoth", "despierta", "thot"]

_model = None

def _get_model():
    global _model
    if _model is None:
        from vosk import Model
        model_path = os.path.join(os.path.dirname(__file__), "vosk-model-small-es-0.42")
        if os.path.exists(model_path):
            _model = Model(model_path)
    return _model


def _rms(data):
    count = len(data) // 2
    if count == 0:
        return 0
    shorts = struct.unpack(f"{count}h", data[:count * 2])
    sum_squares = sum(s * s for s in shorts)
    return int(math.sqrt(sum_squares / count))


def detect_wake(duration=2, threshold=500):
    path = os.path.join(tempfile.gettempdir(), "thoth_wake.wav")
    subprocess.run(
        ["arecord", "-d", str(duration), "-f", "S16_LE", "-r", "16000", "-c", "1", path],
        capture_output=True,
        timeout=duration + 3,
    )
    if not os.path.exists(path):
        return False
    with open(path, "rb") as f:
        data = f.read()
    header_size = 44
    audio = data[header_size:]
    rms = _rms(audio)
    if rms < threshold:
        return False
    model = _get_model()
    if model is None:
        return True
    from vosk import KaldiRecognizer
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(False)
    rec.AcceptWaveform(audio)
    result = json.loads(rec.FinalResult())
    text = result.get("text", "").lower().strip()
    if not text:
        return rms > threshold * 2
    for w in WAKE_WORDS:
        if w in text:
            return True
    return False


def wait_for_wake(duration=2, threshold=500):
    print("  [Modo reposo. Habla para activar...]", end=" ", flush=True)
    while True:
        if detect_wake(duration=duration, threshold=threshold):
            print("¡Despierto!\n")
            return
