import os
import subprocess
import tempfile

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def capture_camera():
    """Captura una foto desde la cámara. Retorna ruta o None."""
    path = os.path.join(tempfile.gettempdir(), "thoth_capture.jpg")
    try:
        subprocess.run(
            ["libcamera-still", "-o", path, "-n", "--width", "640", "--height", "480"],
            capture_output=True,
            timeout=10,
        )
        return path if os.path.exists(path) else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        try:
            subprocess.run(
                ["fswebcam", path, "--no-banner", "-r", "640x480"],
                capture_output=True,
                timeout=10,
            )
            return path if os.path.exists(path) else None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None


def describe_image(image_path):
    """Retorna metadatos básicos de una imagen."""
    if not HAS_PIL:
        return "[Visión no disponible: instala Pillow]"
    try:
        img = Image.open(image_path)
        return f"Imagen cargada: {img.size[0]}x{img.size[1]}px, {img.mode}"
    except Exception as e:
        return f"[Error al leer imagen: {e}]"
