"""Open-Source Dynamic UPI QR Generation Service (NPCI Specification Compliant).

Generates standard UPI payment URIs (upi://pay?...) and renders high-contrast,
error-resilient QR code images using Python 'qrcode' and Pillow.
"""

import base64
import io
import re
import urllib.parse

import qrcode
from app.core.exceptions import ValidationException
from qrcode.constants import ERROR_CORRECT_M

# NPCI standard VPA regex: username@bankhandle (e.g. gadispot@icici)
VPA_REGEX = re.compile(r"^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$")

DEFAULT_PAYEE_VPA = "gadispot.payments@icici"
DEFAULT_PAYEE_NAME = "Gadispot Parking"


def validate_vpa(vpa: str) -> bool:
    """Validate that a Virtual Payment Address adheres to NPCI VPA format rules."""
    if not vpa or len(vpa) > 256:
        return False
    return bool(VPA_REGEX.match(vpa.strip()))


def build_upi_payment_uri(
    amount_rupees: float,
    transaction_ref: str,
    payee_vpa: str | None = None,
    payee_name: str | None = None,
    note: str | None = None,
) -> str:
    """Construct an NPCI-compliant dynamic UPI deep-link URI.

    Format:
    upi://pay?pa={vpa}&pn={name}&am={amount:.2f}&cu=INR&tr={ref}&tn={note}
    """
    vpa = payee_vpa or DEFAULT_PAYEE_VPA
    name = payee_name or DEFAULT_PAYEE_NAME
    transaction_note = (note or f"Parking Fee {transaction_ref[:10]}").strip()[:50]

    if not validate_vpa(vpa):
        raise ValidationException(
            detail=f"Invalid Virtual Payment Address (VPA): '{vpa}'. Must match username@bank.",
            code="INVALID_VPA",
        )

    if amount_rupees <= 0.0 or amount_rupees > 100000.0:
        raise ValidationException(
            detail=f"Invalid UPI payment amount: ₹{amount_rupees:.2f}. Must be between ₹0.01 and ₹100,000.00.",
            code="INVALID_AMOUNT",
        )

    # Clean transaction ref (alphanumeric up to 35 chars per NPCI standard)
    clean_ref = re.sub(r"[^a-zA-Z0-9\-_]", "", transaction_ref)[:35]

    params = {
        "pa": vpa,
        "pn": name,
        "am": f"{amount_rupees:.2f}",
        "cu": "INR",
        "tr": clean_ref,
        "tn": transaction_note,
    }

    query_str = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"upi://pay?{query_str}"


def generate_upi_qr_code_image(
    upi_uri: str,
    box_size: int = 10,
    border: int = 2,
) -> io.BytesIO:
    """Render a dynamic UPI payment QR code as a PNG byte buffer using Pillow."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_M,  # 15% error recovery for damaged/creased screens
        box_size=box_size,
        border=border,
    )
    qr.add_data(upi_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0A0A0A", back_color="#FFFFFF")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generate_upi_qr_base64(
    upi_uri: str,
    box_size: int = 10,
    border: int = 2,
) -> str:
    """Render a dynamic UPI QR code as a Base64-encoded PNG Data URL."""
    buffer = generate_upi_qr_code_image(upi_uri, box_size=box_size, border=border)
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"
