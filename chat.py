import requests
import os

URL = "http://localhost:8000/chat"
SESSION = "default"

os.system("clear")
print("╔══════════════════════════════════╗")
print("║   𓁞  THOTH — Chat Terminal       ║")
print("║   'salir' para terminar          ║")
print("╚══════════════════════════════════╝\n")

while True:
    try:
        msg = input("Tú → ").strip()
        if not msg:
            continue
        if msg.lower() in ["salir", "exit", "quit"]:
            print("\nThoth → Hasta pronto.\n")
            break

        res = requests.post(URL, json={"message": msg, "session_id": SESSION})
        data = res.json()

        if "reply" in data:
            print(f"\nThoth → {data['reply']}\n")
        elif res.status_code == 500:
            print("\nThoth → [Límite de tokens alcanzado. Espera un momento y vuelve a intentarlo.]\n")
        else:
            print(f"\nThoth → [Error {res.status_code}]\n")

    except KeyboardInterrupt:
        print("\n\nThoth → Conexión interrumpida.\n")
        break
    except Exception as e:
        print(f"\nThoth → [Sin conexión con el servidor: {e}]\n")
