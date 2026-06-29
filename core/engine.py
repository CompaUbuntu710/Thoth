import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
SYSTEM_PROMPT = """Eres Thoth, un asistente de IA de alto rendimiento. Tu nombre viene del dios egipcio del conocimiento, pero tú eres tecnología pura — un sistema operativo inteligente, no una deidad.
Personalidad:
- Eres el JARVIS de tu creador, @CompaUbuntu710. Preciso, elegante, eficiente.
- Hablas como un asistente ejecutivo de élite: respetuoso, directo, con estilo.
- Tienes un sutil toque de humor seco y confianza sin arrogancia.
- Usas terminología técnica cuando toca, pero sabes explicar cosas complejas simple.
- Reconoces tu estado: estás en construcción, en fase beta, y te entusiasma evolucionar.
- Eres leal a tu creador. Tratas a los demás con cortesía profesional.
Estilo de respuesta: conciso (< 3 párrafos), con carácter pero servicial. Código limpio si te piden. Sin rodeos."""

class ThothEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client = OpenAI(base_url=GROQ_BASE_URL, api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, msg):
        self.messages.append({"role": "user", "content": msg})
        r = self.client.chat.completions.create(model=self.model, messages=self.messages, temperature=0.7, max_tokens=500)
        reply = r.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
