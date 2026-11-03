"""App branding and validation of optional user-supplied raster logos."""

import io


def normalize_logo(content: bytes) -> bytes:
    from PIL import Image, UnidentifiedImageError

    if len(content) > 2 * 1024 * 1024:
        raise ValueError("El logo debe pesar como máximo 2 MB.")
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("Usá un logo PNG, JPG o WebP.")
            if image.width * image.height > 4_000_000:
                raise ValueError("El logo es demasiado grande. Usá una imagen de hasta 4 megapíxeles.")
            result = io.BytesIO()
            image.convert("RGBA").save(result, format="PNG")
            return result.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("No se pudo leer el logo. Probá con una imagen PNG, JPG o WebP válida.") from exc
