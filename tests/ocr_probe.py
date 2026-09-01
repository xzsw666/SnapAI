"""
SnapAI Phase 5 -- OCR Step 1: Windows Native OCR Probe.

Temporary test script to verify whether Windows.Media.Ocr is usable
in the current development environment.

Usage:
    .venv\Scripts\python.exe ocr_probe.py

This script does NOT modify any SnapAI source files.
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def report(step: str, status: str, detail: str = "") -> None:
    """Print a formatted test result line."""
    tag = f"[{status}]"
    if status == "PASS":
        logger.info("===> %s %s", tag, f"{step}  -- {detail}" if detail else step)
    elif status == "FAIL":
        logger.info("!!! %s %s", tag, f"{step}  -- {detail}" if detail else step)
    else:
        logger.info("--- %s %s", tag, f"{step}  -- {detail}" if detail else step)


def test_python_version() -> None:
    """A. Python version"""
    v = sys.version_info
    report("Python version", "PASS", f"{v.major}.{v.minor}.{v.micro}")


def test_imports() -> None:
    """B. All required winrt imports"""
    all_pass = True
    for pkg, label in [
        ("winrt", "winrt"),
        ("winrt.windows.media.ocr", "winrt.windows.media.ocr"),
        ("winrt.windows.graphics.imaging", "winrt.windows.graphics.imaging"),
        ("winrt.windows.storage.streams", "winrt.windows.storage.streams"),
        ("winrt.windows.globalization", "winrt.windows.globalization"),
        ("winrt.windows.foundation", "winrt.windows.foundation"),
    ]:
        try:
            __import__(pkg)
            report(f"{label} import", "PASS")
        except ImportError as e:
            report(f"{label} import", "FAIL", str(e))
            all_pass = False
    if not all_pass:
        report("Import check", "FAIL", "missing required packages")
        sys.exit(1)


def test_ocr_engine() -> None:
    """C. OcrEngine creation and language info"""
    import winrt.windows.media.ocr as ocr

    engine = ocr.OcrEngine.try_create_from_user_profile_languages()
    report("OcrEngine creation", "PASS")
    report("Max image dimension", "INFO", str(ocr.OcrEngine.max_image_dimension))

    lang = engine.recognizer_language
    report("OCR language", "PASS", f"{lang.display_name} ({lang.language_tag})")


def _create_test_image() -> bytes:
    """Create a test PNG image with English and Chinese text via PySide6."""
    from PySide6.QtCore import Qt, QBuffer, QByteArray
    from PySide6.QtGui import QImage, QPainter, QColor, QFont
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication(sys.argv)

    width, height = 600, 200
    img = QImage(width, height, QImage.Format.Format_RGB32)
    img.fill(Qt.GlobalColor.white)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setPen(QColor(0, 0, 0))

    font_en = QFont("Segoe UI", 28)
    painter.setFont(font_en)
    painter.drawText(30, 70, "Hello World")

    font_cn = QFont("Microsoft YaHei", 28)
    painter.setFont(font_cn)
    painter.drawText(30, 140, "\u4f60\u597d\uff0c\u4e16\u754c")

    painter.end()

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    buf.close()

    return bytes(ba.data())


async def _run_ocr_pipeline(png_bytes: bytes) -> str:
    """Convert PNG to SoftwareBitmap and run OCR."""
    import winrt.windows.media.ocr as ocr
    import winrt.windows.graphics.imaging as imaging
    import winrt.windows.storage.streams as streams

    stream = streams.InMemoryRandomAccessStream()
    writer = streams.DataWriter(stream)
    writer.write_bytes(png_bytes)
    await writer.store_async()
    writer.detach_stream()
    stream.seek(0)

    decoder = await imaging.BitmapDecoder.create_async(stream)
    sb = await decoder.get_software_bitmap_async()
    logger.info("SoftwareBitmap: %dx%d", sb.pixel_width, sb.pixel_height)

    engine = ocr.OcrEngine.try_create_from_user_profile_languages()
    result = await engine.recognize_async(sb)
    return result.text


def main() -> None:
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("SnapAI Phase 5 -- Windows OCR Probe")
    logger.info("=" * 60)

    test_python_version()
    test_imports()
    test_ocr_engine()

    report("Creating test image", "INFO", "via PySide6 QPainter")
    try:
        png_bytes = _create_test_image()
        report("Test image created", "PASS", f"PNG size={len(png_bytes)} bytes")
    except Exception as e:
        report("Test image creation", "FAIL", str(e))
        import traceback
        traceback.print_exc()
        return

    report("Running OCR pipeline", "INFO", "SoftwareBitmap + RecognizeAsync")
    try:
        text = asyncio.run(_run_ocr_pipeline(png_bytes))
    except Exception as e:
        report("OCR pipeline", "FAIL", str(e))
        import traceback
        traceback.print_exc()
        return

    report("OCR pipeline", "PASS", "executed successfully")
    print()
    print("=" * 60)
    print("OCR RESULT:")
    print(text)
    print("=" * 60)

    has_hello = "Hello" in text or "hello" in text
    has_world = "World" in text or "world" in text
    has_chinese = any("\u4e00" <= c <= "\u9fff" for c in text)

    if has_hello and has_world:
        report("English text", "PASS", "'Hello World' recognized")
    else:
        report("English text", "FAIL", f"'Hello World' not found in OCR output")

    if has_chinese:
        report("Chinese text", "PASS", "Chinese text recognized")
    else:
        report("Chinese text", "FAIL", "Chinese text not found in OCR output")

    if has_hello and has_world and has_chinese:
        report("Overall result", "PASS", "Windows OCR full pipeline verified")
        print()
        print("=" * 60)
        print("PASS -- Windows OCR full pipeline verified")
        print("=" * 60)
    else:
        report("Overall result", "FAIL", "OCR partial failure")

    logger.info("=" * 60)
    logger.info("Probe complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
