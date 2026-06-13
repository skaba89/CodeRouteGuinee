import io

import qrcode
import qrcode.image.svg


def generate_qr_svg(payload: str) -> str:
    image_factory = qrcode.image.svg.SvgImage
    qr_image = qrcode.make(payload, image_factory=image_factory)
    buffer = io.BytesIO()
    qr_image.save(buffer)
    return buffer.getvalue().decode("utf-8")
