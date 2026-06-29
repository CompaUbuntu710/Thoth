try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        if not HAS_TTS:
            raise RuntimeError("pyttsx3 no instalado: pip install pyttsx3")
        _engine = pyttsx3.init()
        voices = _engine.getProperty("voices")
        for v in voices:
            if v.languages and any(l.startswith("es") for l in v.languages):
                _engine.setProperty("voice", v.id)
                break
        _engine.setProperty("rate", 160)
        _engine.setProperty("volume", 0.9)
    return _engine


def speak(text):
    engine = _get_engine()
    engine.say(text)
    engine.runAndWait()


def say_thoth(reply):
    speak(reply)
