"""OCR module for SnapAI — Windows native OCR.

Converts mss.ScreenShot to text using Windows.Media.Ocr.
No file I/O, no clipboard access, no QImage dependency.

Public interface:
    recognize(screenshot: mss.ScreenShot) -> str
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

_engine = None


def _get_engine():
    """Lazy-initialize and return the global OCR engine."""
    global _engine
    if _engine is not None:
        return _engine

    import winrt.windows.media.ocr as ocr

    _engine = ocr.OcrEngine.try_create_from_user_profile_languages()
    if _engine is None:
        raise RuntimeError(
            "Failed to create Windows OCR engine. "
            "Ensure Windows OCR language pack is installed."
        )
    lang = _engine.recognizer_language
    logger.info(
        "OCR engine initialized: %s (%s)", lang.display_name, lang.language_tag
    )
    return _engine


def _rgb_to_bmp_data(rgb_bytes: bytes, width: int, height: int) -> bytes:
    """Convert RGB888 bytes to a BMP file in memory.

    BMP format: BGR pixels, bottom-up rows, 4-byte row padding.
    This avoids any dependency on QImage or PIL.
    """
    row_size = width * 3
    padding = (4 - row_size % 4) % 4
    stride = row_size + padding
    pixel_data_size = stride * height
    file_size = 14 + 40 + pixel_data_size

    data = bytearray(file_size)

    # BMP file header (14 bytes)
    data[0:2] = b'BM'
    data[2:6] = file_size.to_bytes(4, 'little')
    data[10:14] = (54).to_bytes(4, 'little')  # offset to pixel data

    # DIB header (BITMAPINFOHEADER, 40 bytes)
    data[14:18] = (40).to_bytes(4, 'little')   # header size
    data[18:22] = width.to_bytes(4, 'little')
    data[22:26] = height.to_bytes(4, 'little')  # positive = bottom-up
    data[26:28] = (1).to_bytes(2, 'little')     # planes
    data[28:30] = (24).to_bytes(2, 'little')    # bits per pixel

    # Pixel data — BGR, bottom-up
    pixel_offset = 54
    for y in range(height):
        src_start = y * width * 3
        dst_start = pixel_offset + (height - 1 - y) * stride
        for x in range(width):
            src = src_start + x * 3
            dst = dst_start + x * 3
            # RGB -> BGR swap
            data[dst] = rgb_bytes[src + 2]      # B
            data[dst + 1] = rgb_bytes[src + 1]  # G
            data[dst + 2] = rgb_bytes[src]      # R
        # Padding bytes are already zero (from bytearray init)

    return bytes(data)


async def _run_ocr(screenshot):
    """Convert screenshot to SoftwareBitmap and run OCR asynchronously."""
    import winrt.windows.media.ocr as ocr
    import winrt.windows.graphics.imaging as imaging
    import winrt.windows.storage.streams as streams

    # Step 1: Convert RGB888 -> BMP in memory
    bmp_data = _rgb_to_bmp_data(screenshot.rgb, screenshot.width, screenshot.height)

    # Step 2: Write BMP into memory stream
    stream = streams.InMemoryRandomAccessStream()
    writer = streams.DataWriter(stream)
    writer.write_bytes(bmp_data)
    await writer.store_async()
    writer.detach_stream()
    stream.seek(0)

    # Step 3: Decode BMP -> SoftwareBitmap
    decoder = await imaging.BitmapDecoder.create_async(stream)
    software_bitmap = await decoder.get_software_bitmap_async()

    # Step 4: Run OCR
    engine = _get_engine()
    result = await engine.recognize_async(software_bitmap)
    return result.text


def recognize(screenshot) -> str:
    """Recognize text from a screenshot using Windows native OCR.

    Args:
        screenshot: An mss.ScreenShot object (from screenshot.py).

    Returns:
        Recognized text as a string. Returns "" if nothing was recognized.

    Raises:
        ValueError: If screenshot is None or has invalid dimensions.
        RuntimeError: If OCR engine initialization or execution fails.
    """
    if screenshot is None:
        raise ValueError("screenshot must not be None")
    if screenshot.width <= 0 or screenshot.height <= 0:
        raise ValueError(
            f"Invalid screenshot dimensions: {screenshot.width}x{screenshot.height}"
        )

    logger.info("OCR started: image=%dx%d", screenshot.width, screenshot.height)

    try:
        text = asyncio.run(_run_ocr(screenshot))
    except Exception as exc:
        raise RuntimeError(f"OCR failed: {exc}") from exc

    text = text.strip()

    if text:
        logger.info("OCR completed: text_length=%d", len(text))
        logger.info("OCR result:\n%s", text)
    else:
        logger.info("OCR result: <empty>")

    return text
