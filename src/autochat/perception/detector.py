from __future__ import annotations

import math
from typing import Optional
from .frame import Frame


class DirtyFrameDetector:
    def __init__(
        self,
        change_threshold: float = 0.05,
        pixel_delta_threshold: int = 25,
        sample_step: int = 1,
    ) -> None:
        if (
            not isinstance(change_threshold, (int, float))
            or isinstance(change_threshold, bool)
            or not math.isfinite(change_threshold)
            or not 0.0 <= change_threshold <= 1.0
        ):
            raise ValueError("change_threshold must be between 0.0 and 1.0")
        if (
            not isinstance(pixel_delta_threshold, int)
            or isinstance(pixel_delta_threshold, bool)
            or not 0 <= pixel_delta_threshold <= 255
        ):
            raise ValueError("pixel_delta_threshold must be integer 0..255")
        if not isinstance(sample_step, int) or sample_step <= 0:
            raise ValueError("sample_step must be positive integer")

        self.change_threshold = float(change_threshold)
        self.pixel_delta_threshold = int(pixel_delta_threshold)
        self.sample_step = int(sample_step)
        self._last_frame: Optional[Frame] = None

    def reset(self) -> None:
        self._last_frame = None

    def is_dirty(self, frame: Frame) -> bool:
        if not isinstance(frame, Frame):
            raise ValueError("frame must be Frame instance")

        if (
            self._last_frame is None
            or self._last_frame.width != frame.width
            or self._last_frame.height != frame.height
            or self._last_frame.channels != frame.channels
        ):
            self._last_frame = frame
            return True

        prev_data = self._last_frame.data
        curr_data = frame.data
        channels = frame.channels
        step = self.sample_step * channels

        changed_samples = 0
        total_samples = 0

        # Fast byte comparison loop
        delta_thresh = self.pixel_delta_threshold
        for idx in range(0, len(curr_data), step):
            total_samples += 1
            # Check maximum channel delta
            is_pixel_diff = False
            for c in range(min(channels, 3)):  # Skip alpha channel if RGBA
                if abs(curr_data[idx + c] - prev_data[idx + c]) >= delta_thresh:
                    is_pixel_diff = True
                    break
            if is_pixel_diff:
                changed_samples += 1

        if total_samples == 0:
            return False

        ratio = changed_samples / total_samples
        if ratio >= self.change_threshold:
            self._last_frame = frame
            return True

        return False
