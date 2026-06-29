import os
import sys

SESSION = "default"

try:
    from voice import listen, speak
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False

TTS_ON = "--tts" in sys.argv
USE_SERVER = "--server" in sys.argv

if USE_SERVER:
    import requests
    URL = "http://localhost:8000"

    def send(msg):
        r = requests.post(f"{URL}/chat", json={"message": msg, "session_id": SESSION})
        return r.json().get("reply", f"[Error {r.status_code}]")

    def do_remember(fact):
        requests.post(f"{URL}/remember", json={"message": fact, "session_id": SESSION})
        return f"Recordado: {fact}"

    def do_forget(fact):
        requests.post(f"{URL}/forget", json={"fact": fact, "session_id": SESSION})
        return f"Olvidado: {fact}"

    def do_recall():
        r = requests.get(f"{URL}/memories")
        return r.json().get("facts", [])
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from core.engine import ThothEngine
    from memory.store import MemoryStore
    _store = MemoryStore()
    _engine = ThothEngine(store=_store)

    def send(msg):
        return _engine.chat(msg, SESSION)

    def do_remember(fact):
        _engine.remember(fact)
        return f"Recordado: {fact}"

    def do_forget(fact):
        _engine.forget(fact)
        return f"Olvidado: {fact}"

    def do_recall():
        return _engine.recall()

os.system("clear")
print("╔══════════════════════════════════╗")
print("║   𓁞  THOTH — Chat Terminal       ║")
print("║   Enter vacío → voz              ║")
print("║   :tts          → toggle voz     ║")
print("║   :recuerda X   → guardar hecho  ║")
print("║   :olvida X     → borrar hecho   ║")
print("║   :recuerdos    → listar hechos  ║")
print("║   'salir'       → terminar       ║")
print("╚══════════════════════════════════╝\n")

while True:
    try:
        if VOICE_ENABLED:
            msg = input("Tú (Enter=voz) → ").strip()
        else:
            msg = input("Tú → ").strip()

        if not msg and VOICE_ENABLED:
            msg = listen(duration=5)
            if not msg or msg.startswith("[No te escuché") or msg.startswith("[Error"):
                continue

        if not msg:
            continue

        if msg.lower() == ":tts":
            TTS_ON = not TTS_ON
            print(f"  TTS: {'ON' if TTS_ON else 'OFF'}\n")
            continue

        if msg.lower().startswith(":recuerda "):
            print(f"  {do_remember(msg[10:])}\n")
            continue

        if msg.lower().startswith(":olvida "):
            print(f"  {do_forget(msg[8:])}\n")
            continue

        if msg.lower() == ":recuerdos":
            facts = do_recall()
            if facts:
                print("  Thoth recuerda:")
                for f in facts:
                    print(f"    [{f['category']}] {f['fact']}")
            else:
                print("  No recuerdo nada aún")
            print()
            continue

        if msg.lower() in ["salir", "exit", "quit"]:
            print("\nThoth → Hasta pronto.\n")
            break

        reply = send(msg)
        print(f"\nThoth → {reply}\n")
        if TTS_ON:
            speak(reply)

    except KeyboardInterrupt:
        print("\n\nThoth → Conexión interrumpida.\n")
        break
    except Exception as e:
        print(f"\nThoth → [Error: {e}]\n")
