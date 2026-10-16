from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Dict, Optional
from .geometry import Rect
from .win32 import Win32Bridge


@dataclass(frozen=True)
class OverlayConfig:
    border_width: int = 2
    border_color: str = "#00E5FF"
    background_alpha: float = 0.05
    exclude_from_capture: bool = True
    no_activate: bool = True


class OverlayState:
    def __init__(self, initial_roi: Rect) -> None:
        if not isinstance(initial_roi, Rect):
            raise ValueError("initial_roi must be Rect")
        self._current_roi = initial_roi
        self._is_locked = False
        self._presets: Dict[str, Rect] = {}
        self._lock = RLock()

    @property
    def current_roi(self) -> Rect:
        with self._lock:
            return self._current_roi

    @property
    def is_locked(self) -> bool:
        with self._lock:
            return self._is_locked

    def update_roi(self, new_roi: Rect) -> None:
        if not isinstance(new_roi, Rect):
            raise ValueError("new_roi must be Rect")
        with self._lock:
            if not self._is_locked:
                self._current_roi = new_roi

    def toggle_lock(self) -> bool:
        with self._lock:
            self._is_locked = not self._is_locked
            return self._is_locked

    def save_preset(self, name: str, roi: Rect) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("preset name must be non-empty string")
        if not isinstance(roi, Rect):
            raise ValueError("roi must be Rect")
        with self._lock:
            self._presets[name.strip()] = roi

    def get_preset(self, name: str) -> Optional[Rect]:
        with self._lock:
            return self._presets.get(name.strip())

    def apply_preset(self, name: str) -> bool:
        with self._lock:
            preset = self._presets.get(name.strip())
            if preset is not None:
                self._current_roi = preset
                return True
            return False


def setup_overlay_window(hwnd: int, config: OverlayConfig, bridge: Optional[Win32Bridge] = None) -> bool:
    """Configures native Windows properties on a Qt window hwnd."""
    if bridge is None:
        bridge = Win32Bridge()
    if not bridge.is_available or hwnd <= 0:
        return False
    success = True
    if config.no_activate:
        success = bridge.apply_no_activate(hwnd) and success
    if config.exclude_from_capture:
        success = bridge.apply_exclude_from_capture(hwnd) and success
    return success


def is_qt_available() -> bool:
    try:
        import PySide6  # type: ignore[import-not-found]
        return True
    except ImportError:
        return False


class FloatingAssistantOverlay:
    """Factory and launcher for the PySide6 floating assistant widget."""

    def __init__(self, state: OverlayState, config: Optional[OverlayConfig] = None) -> None:
        self.state = state
        self.config = config or OverlayConfig()
        if not is_qt_available():
            raise ImportError(
                "PySide6 is required to display the floating overlay. "
                "Install it using: pip install 'auto-chat-agent[ui]'"
            )

    def create_widget(self):
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
            QTextEdit, QLabel, QFrame
        )

        class _Widget(QWidget):
            def __init__(widget_self, state: OverlayState, config: OverlayConfig):
                super().__init__()
                widget_self.state = state
                widget_self.config = config
                widget_self.setWindowFlags(
                    Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
                )
                widget_self.setAttribute(Qt.WA_TranslucentBackground, True)

                layout = QVBoxLayout(widget_self)
                layout.setContentsMargins(4, 4, 4, 4)

                # Header bar
                header = QHBoxLayout()
                widget_self.lbl_title = QLabel("Auto-Chat Staged Copilot")
                widget_self.lbl_title.setStyleSheet("color: #00E5FF; font-weight: bold;")
                widget_self.btn_lock = QPushButton("🔓 Unlock")
                widget_self.btn_lock.clicked.connect(widget_self._on_toggle_lock)
                header.addWidget(widget_self.lbl_title)
                header.addStretch()
                header.addWidget(widget_self.btn_lock)
                layout.addLayout(header)

                # Staged input area
                widget_self.txt_staged = QTextEdit()
                widget_self.txt_staged.setPlaceholderText("Nội dung AI đã soạn sẵn sàng ở đây...")
                widget_self.txt_staged.setStyleSheet(
                    "background: rgba(20, 24, 30, 0.85); color: #FFF; "
                    f"border: 1px solid {config.border_color}; border-radius: 4px;"
                )
                layout.addWidget(widget_self.txt_staged)

                # Bottom actions
                actions = QHBoxLayout()
                widget_self.btn_send = QPushButton("⚡ Gửi vào App")
                widget_self.btn_send.setStyleSheet(
                    "background: #00E5FF; color: #000; font-weight: bold; padding: 4px 12px; border-radius: 4px;"
                )
                actions.addStretch()
                actions.addWidget(widget_self.btn_send)
                layout.addLayout(actions)

                # Geometry sync
                roi = state.current_roi
                widget_self.setGeometry(roi.x, roi.y, roi.width, roi.height)

            def _on_toggle_lock(widget_self):
                locked = widget_self.state.toggle_lock()
                widget_self.btn_lock.setText("🔒 Locked" if locked else "🔓 Unlock")

            def showEvent(widget_self, event):
                super().showEvent(event)
                setup_overlay_window(int(widget_self.winId()), widget_self.config)

        return _Widget(self.state, self.config)

