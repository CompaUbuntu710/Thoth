import os
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

TWITTER_BEARER = os.getenv("TWITTER_BEARER_TOKEN", "")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")


def handle_social(platform, action, query="", text="", limit=5):
    try:
        if platform == "twitter":
            return _twitter(action, query=query, text=text, limit=limit)
        elif platform == "status":
            return _status()
        else:
            return f"[Error: plataforma '{platform}' no soportada. Usa: twitter]"
    except Exception as e:
        return f"[Error en social: {e}]"


def _twitter(action, query="", text="", limit=5):
    if action == "search":
        return _twitter_search(query, limit)
    elif action == "post":
        return _twitter_post(text)
    elif action == "trends":
        return _twitter_trends()
    else:
        return "[Error: acción twitter inválida. Usa: search, post, trends]"


def _twitter_search(query, limit=5):
    if not TWITTER_BEARER:
        return "[Error: TWITTER_BEARER_TOKEN no configurado en .env]"
    url = f"https://api.twitter.com/2/tweets/search/recent?query={urllib.parse.quote(query)}&max_results={limit}&tweet.fields=created_at,public_metrics"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TWITTER_BEARER}"})
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read())
        tweets = data.get("data", [])
        if not tweets:
            return f"[Sin resultados para '{query}']"
        lines = []
        for t in tweets:
            metrics = t.get("public_metrics", {})
            likes = metrics.get("like_count", 0)
            lines.append(f"  🐦 {t['created_at'][:19]}: {t['text'][:200]} ❤️{likes}")
        return f"Tweets sobre '{query}':\n" + "\n\n".join(lines[:limit])
    except urllib.error.HTTPError as e:
        err = json.loads(e.read()) if e.code == 429 else {"detail": str(e)}
        if e.code == 429:
            return "[Error: límite de API Twitter alcanzado. Espera 15 min.]"
        return f"[Error Twitter API {e.code}: {err.get('detail', err.get('title', str(e)))}]"
    except Exception as e:
        return f"[Error buscando en Twitter: {e}]"


def _twitter_post(text):
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        return "[Error: credenciales OAuth incompletas. Configura TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]"
    import hmac
    import hashlib
    import base64
    import time

    # OAuth 1.0a helper
    def _oauth_header(method, url, params=None):
        oauth = {
            "oauth_consumer_key": TWITTER_API_KEY,
            "oauth_nonce": hashlib.sha1(os.urandom(32)).hexdigest()[:32],
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": TWITTER_ACCESS_TOKEN,
            "oauth_version": "1.0",
        }
        if params:
            oauth.update(params)
        keys = sorted(oauth.keys())
        sig_params = "&".join(f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(oauth[k]), safe='')}" for k in keys)
        sig_base = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(sig_params, safe='')}"
        sig_key = f"{TWITTER_API_SECRET}&{TWITTER_ACCESS_SECRET}"
        signature = base64.b64encode(hmac.new(sig_key.encode(), sig_base.encode(), hashlib.sha1).digest()).decode()
        oauth["oauth_signature"] = signature
        return "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(str(oauth[k]), safe="")}"' for k in sorted(oauth.keys()))

    url = "https://api.twitter.com/2/tweets"
    body = json.dumps({"text": text[:280]}).encode()
    auth = _oauth_header("POST", url)
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": auth,
        "Content-Type": "application/json",
    })
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read())
        tweet_id = data.get("data", {}).get("id", "")
        return f"[Tweet publicado: {text[:80]}... ID: {tweet_id}]"
    except urllib.error.HTTPError as e:
        err = json.loads(e.read()) if e.code else {"detail": str(e)}
        return f"[Error publicando tweet {e.code}: {err}]"
    except Exception as e:
        return f"[Error publicando: {e}]"


def _twitter_trends():
    if not TWITTER_BEARER:
        return "[Error: TWITTER_BEARER_TOKEN no configurado]"
    trends_url = "https://api.twitter.com/2/trends/by/woeid/23424977"
    req = urllib.request.Request(trends_url, headers={"Authorization": f"Bearer {TWITTER_BEARER}"})
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read())
        lines = [f"  #{t['name']}" for t in data.get("data", {}).get("trends", [])[:10]]
        return "Tendencias en Twitter:\n" + "\n".join(lines)
    except Exception:
        return "[Tendencias no disponibles (puede requerir Elevated access)]"


def _status():
    tw = bool(TWITTER_BEARER)
    tw_write = all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET])
    parts = []
    if tw:
        parts.append(f"Twitter search: ✓")
    if tw_write:
        parts.append(f"Twitter post: ✓")
    return "Social: " + (" | ".join(parts) if parts else "Sin configurar")

