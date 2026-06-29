import json
import csv
import io
import os

try:
    import fitz
    HAS_PDF = True
except ImportError:
    HAS_PDF = False


def read_pdf(path):
    if not HAS_PDF:
        return "[PDF reader no disponible: instala PyMuPDF]"
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append(f"[Página {i+1}]\n{text}")
    doc.close()
    return "\n\n".join(pages)


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return json.dumps(data, indent=2, ensure_ascii=False)


def read_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)
    if not rows:
        return ""
    header = " | ".join(rows[0])
    lines = [" | ".join(r) for r in rows[1:]]
    return f"{header}\n" + "\n".join(lines)


def read_md(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_file(path):
    ext = os.path.splitext(path)[1].lower()
    readers = {
        ".pdf": read_pdf,
        ".json": read_json,
        ".csv": read_csv,
        ".md": read_md,
        ".txt": read_md,
    }
    reader = readers.get(ext)
    if reader is None:
        return f"[Formato no soportado: {ext}]"
    return reader(path)
