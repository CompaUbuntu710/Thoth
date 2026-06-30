import os
import threading
from datetime import datetime, timezone

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")


class VectorStore:
    """Almacén vectorial para búsqueda semántica usando ChromaDB."""

    def __init__(self, path=None):
        self._lock = threading.Lock()
        self.path = path or CHROMA_DIR
        self._client = None
        self._collection = None

    @property
    def client(self):
        if self._client is None:
            os.makedirs(self.path, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self.path,
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="thoth_memory",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_fact(self, fact_id, fact_text, category="general", source_session=None):
        """Indexa (o actualiza) un hecho en ChromaDB."""
        if not HAS_CHROMA or not fact_text:
            return
        try:
            now = datetime.now(timezone.utc).isoformat()
            sid = str(fact_id) if fact_id else fact_text
            with self._lock:
                try:
                    self.collection.add(
                        ids=[sid],
                        documents=[fact_text],
                        metadatas=[{
                            "category": category,
                            "source_session": source_session or "",
                            "created_at": now,
                            "type": "fact",
                        }],
                    )
                except Exception:
                    self.collection.update(
                        ids=[sid],
                        documents=[fact_text],
                        metadatas=[{
                            "category": category,
                            "source_session": source_session or "",
                            "created_at": now,
                            "type": "fact",
                        }],
                    )
        except Exception:
            pass

    def search(self, query, n_results=5, category=None):
        """Búsqueda semántica por embedding similarity."""
        if not HAS_CHROMA or not query:
            return []
        try:
            where = {"type": "fact"}
            if category:
                where["category"] = category
            with self._lock:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where,
                )
            items = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    items.append({
                        "fact": doc,
                        "category": meta.get("category", "general"),
                        "score": results["distances"][0][i] if results["distances"] else 0,
                        "source_session": meta.get("source_session", ""),
                    })
            return items
        except Exception:
            return []

    def count(self):
        """Número de documentos en el índice."""
        if not HAS_CHROMA:
            return 0
        try:
            return self.collection.count()
        except Exception:
            return 0

    def close(self):
        self._client = None
        self._collection = None
