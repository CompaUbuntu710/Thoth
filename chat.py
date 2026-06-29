import requests
import os
import sys

URL = "http://localhost:8000/chat"
SESSION = "default"

try:
    from voice import listen, speak
    VOICE_ENABLED = True
except ImportError:
    VOICE_ENABLED = False

TTS_ON = "--tts" in sys.argv

os.system("clear")
print("╔══════════════════════════════════╗")
print("║   𓁞  THOTH — Chat Terminal       ║")
print("║   Enter vacío → voz              ║")
print("║   :v            → voz            ║")
print("║   :tts          → toggle voz salida║")
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
            if msg.startswith("[No te escuché") or msg.startswith("[Error"):
                continue

        if not msg:
            continue

        if msg.lower() == ":tts":
            TTS_ON = not TTS_ON
            print(f"  TTS: {'ON' if TTS_ON else 'OFF'}\n")
            continue

        if msg.lower() in ["salir", "exit", "quit"]:
            print("\nThoth → Hasta pronto.\n")
            break

        res = requests.post(URL, json={"message": msg, "session_id": SESSION})
        data = res.json()

        if "reply" in data:
            reply = data["reply"]
            print(f"\nThoth → {reply}\n")
            if TTS_ON:
                speak(reply)
        elif res.status_code == 500:
            print("\nThoth → [Límite de tokens alcanzado. Espera un momento y vuelve a intentarlo.]\n")
        else:
            print(f"\nThoth → [Error {res.status_code}]\n")

    except KeyboardInterrupt:
        print("\n\nThoth → Conexión interrumpida.\n")
        break
    except Exception as e:
        print(f"\nThoth → [Sin conexión con el servidor: {e}]\n")
