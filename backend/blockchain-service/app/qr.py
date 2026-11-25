import base64
import io

import qrcode

from app.config import Settings


def build_verification_url(settings: Settings, credential_id: str) -> str:
    return f"{settings.frontend_verify_base_url.rstrip('/')}/{credential_id}"


def generate_qr_png_base64(url: str) -> str:
    """Generate a QR code PNG for the given verification URL, returned as a
    base64 data string. The QR code encodes only the verification URL/ID —
    never any certificate content or personal data.
    """
    img = qrcode.make(url)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")
