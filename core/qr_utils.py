from pathlib import Path
import qrcode
from config.settings import QRCODE_DIR
import hashlib
import time
import secrets

QRCODE_DIR.mkdir(exist_ok=True)

def make_qr_token() -> str:
    """
    Create a unique token for QR payload using random bits + timestamp.
    """
    random_part = secrets.token_hex(8)
    base = f"{random_part}|{time.time_ns()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def generate_qr_image(token: str, filename: str = None) -> str:
    if filename is None:
        filename = f"user_{token[:12]}.png"
    path = Path(QRCODE_DIR) / filename
    img = qrcode.make(token)
    img.save(path.as_posix())
    return path.as_posix()
