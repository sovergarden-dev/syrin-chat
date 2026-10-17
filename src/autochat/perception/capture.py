from __future__ import annotations

import ctypes
from ctypes import Structure, c_long, c_short, c_uint, byref
from typing import Optional, Protocol, runtime_checkable
from ..ui.geometry import Rect
from .frame import Frame


@runtime_checkable
class ScreenRegionCapture(Protocol):
    def capture_region(self, rect: Rect) -> Optional[Frame]: ...


class MockCaptureBackend:
    def __init__(self, default_frame: Optional[Frame] = None) -> None:
        self._default_frame = default_frame

    def set_frame(self, frame: Optional[Frame]) -> None:
        self._default_frame = frame

    def capture_region(self, rect: Rect) -> Optional[Frame]:
        if self._default_frame is None:
            return None
        if self._default_frame.width == rect.width and self._default_frame.height == rect.height:
            return self._default_frame
        # Crop or return clamped frame
        return self._default_frame.crop(Rect(0, 0, rect.width, rect.height))


# Win32 GDI structures for screen capture
class BITMAPINFOHEADER(Structure):
    _fields_ = [
        ("biSize", c_uint),
        ("biWidth", c_long),
        ("biHeight", c_long),
        ("biPlanes", c_short),
        ("biBitCount", c_short),
        ("biCompression", c_uint),
        ("biSizeImage", c_uint),
        ("biXPelsPerMeter", c_long),
        ("biYPelsPerMeter", c_long),
        ("biClrUsed", c_uint),
        ("biClrImportant", c_uint),
    ]


SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0


class GdiCaptureBackend:
    """Zero-dependency Windows screen region capture using GDI BitBlt."""

    def __init__(self) -> None:
        try:
            self._user32 = ctypes.windll.user32
            self._gdi32 = ctypes.windll.gdi32
        except (AttributeError, OSError):
            self._user32 = None
            self._gdi32 = None

    @property
    def is_available(self) -> bool:
        return self._user32 is not None and self._gdi32 is not None

    def capture_region(self, rect: Rect) -> Optional[Frame]:
        if not self.is_available:
            return None
        if rect.width <= 0 or rect.height <= 0:
            return None

        width = rect.width
        height = rect.height

        hwnd = self._user32.GetDesktopWindow()
        hdc_screen = self._user32.GetDC(hwnd)
        if not hdc_screen:
            return None

        hdc_mem = None
        hbm = None
        hbm_old = None

        try:
            hdc_mem = self._gdi32.CreateCompatibleDC(hdc_screen)
            if not hdc_mem:
                return None
            hbm = self._gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
            if not hbm:
                return None
            hbm_old = self._gdi32.SelectObject(hdc_mem, hbm)

            # BitBlt from screen to memory DC
            self._gdi32.BitBlt(
                hdc_mem, 0, 0, width, height, hdc_screen, rect.x, rect.y, SRCCOPY
            )

            # Setup bitmap header
            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # Top-down bitmap
            bmi.biPlanes = 1
            bmi.biBitCount = 32  # BGRA 4 channels
            bmi.biCompression = BI_RGB

            buffer_size = width * height * 4
            buffer = ctypes.create_string_buffer(buffer_size)

            res = self._gdi32.GetDIBits(
                hdc_mem,
                hbm,
                0,
                height,
                buffer,
                byref(bmi),
                DIB_RGB_COLORS,
            )

            if res == 0:
                return None

            # Convert BGRA to RGBA bytes
            raw_bytes = bytearray(buffer.raw)
            for i in range(0, len(raw_bytes), 4):
                b = raw_bytes[i]
                r = raw_bytes[i + 2]
                raw_bytes[i] = r
                raw_bytes[i + 2] = b

            return Frame(width=width, height=height, channels=4, data=bytes(raw_bytes))
        except Exception:
            return None
        finally:
            if hdc_mem and hbm_old:
                self._gdi32.SelectObject(hdc_mem, hbm_old)
            if hbm:
                self._gdi32.DeleteObject(hbm)
            if hdc_mem:
                self._gdi32.DeleteDC(hdc_mem)
            if hdc_screen:
                self._user32.ReleaseDC(hwnd, hdc_screen)
