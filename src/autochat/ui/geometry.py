from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if type(self.x) is not int or type(self.y) is not int:
            raise ValueError("coordinates must be integers")
        if type(self.width) is not int or type(self.height) is not int:
            raise ValueError("dimensions must be integers")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive integers")

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def contains(self, other: Rect) -> bool:
        return (
            self.x <= other.x
            and self.y <= other.y
            and self.right >= other.right
            and self.bottom >= other.bottom
        )

    def clamp_to(self, container: Rect) -> Rect:
        new_width = min(self.width, container.width)
        new_height = min(self.height, container.height)
        new_x = max(container.x, min(self.x, container.right - new_width))
        new_y = max(container.y, min(self.y, container.bottom - new_height))
        return Rect(new_x, new_y, new_width, new_height)


@dataclass(frozen=True)
class NormalizedRect:
    dx: float
    dy: float
    width: float
    height: float

    def __post_init__(self) -> None:
        for val, name in (
            (self.dx, "dx"),
            (self.dy, "dy"),
            (self.width, "width"),
            (self.height, "height"),
        ):
            if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val):
                raise ValueError(f"{name} must be a finite float")
            if val < 0.0:
                raise ValueError(f"{name} must be non-negative")

    @classmethod
    def from_absolute(cls, child: Rect, parent: Rect) -> NormalizedRect:
        return cls(
            dx=(child.x - parent.x) / parent.width,
            dy=(child.y - parent.y) / parent.height,
            width=child.width / parent.width,
            height=child.height / parent.height,
        )

    def to_absolute(self, parent: Rect) -> Rect:
        return Rect(
            x=int(round(parent.x + self.dx * parent.width)),
            y=int(round(parent.y + self.dy * parent.height)),
            width=int(round(self.width * parent.width)),
            height=int(round(self.height * parent.height)),
        )


@dataclass(frozen=True)
class DpiScale:
    scale_factor: float = 1.0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.scale_factor, (int, float))
            or isinstance(self.scale_factor, bool)
            or not math.isfinite(self.scale_factor)
            or self.scale_factor <= 0.0
        ):
            raise ValueError("scale_factor must be positive finite float")

    def logical_to_physical(self, rect: Rect) -> Rect:
        return Rect(
            x=int(round(rect.x * self.scale_factor)),
            y=int(round(rect.y * self.scale_factor)),
            width=int(round(rect.width * self.scale_factor)),
            height=int(round(rect.height * self.scale_factor)),
        )

    def physical_to_logical(self, rect: Rect) -> Rect:
        return Rect(
            x=int(round(rect.x / self.scale_factor)),
            y=int(round(rect.y / self.scale_factor)),
            width=int(round(rect.width / self.scale_factor)),
            height=int(round(rect.height / self.scale_factor)),
        )


@dataclass(frozen=True)
class WindowAnchor:
    hwnd: int
    normalized_roi: NormalizedRect

    @classmethod
    def create(cls, hwnd: int, parent_rect: Rect, roi_rect: Rect) -> WindowAnchor:
        norm = NormalizedRect.from_absolute(roi_rect, parent_rect)
        return cls(hwnd=hwnd, normalized_roi=norm)

    def compute_roi(self, current_parent_rect: Rect) -> Rect:
        raw = self.normalized_roi.to_absolute(current_parent_rect)
        return raw.clamp_to(current_parent_rect)
