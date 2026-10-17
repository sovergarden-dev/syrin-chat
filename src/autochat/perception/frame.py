from __future__ import annotations

from dataclasses import dataclass
from ..ui.geometry import Rect


@dataclass(frozen=True)
class Frame:
    width: int
    height: int
    channels: int
    data: bytes

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if self.channels not in (1, 3, 4):
            raise ValueError("channels must be 1, 3, or 4")
        expected_len = self.width * self.height * self.channels
        if len(self.data) != expected_len:
            raise ValueError(f"data length {len(self.data)} does not match {expected_len}")

    def crop(self, rect: Rect) -> Frame:
        # Clamp crop area to frame bounds
        crop_x = max(0, min(rect.x, self.width - 1))
        crop_y = max(0, min(rect.y, self.height - 1))
        crop_w = max(1, min(rect.width, self.width - crop_x))
        crop_h = max(1, min(rect.height, self.height - crop_y))

        stride = self.width * self.channels
        row_bytes = crop_w * self.channels
        out = bytearray(crop_w * crop_h * self.channels)

        out_idx = 0
        for y in range(crop_y, crop_y + crop_h):
            start = y * stride + crop_x * self.channels
            end = start + row_bytes
            out[out_idx : out_idx + row_bytes] = self.data[start:end]
            out_idx += row_bytes

        return Frame(width=crop_w, height=crop_h, channels=self.channels, data=bytes(out))
