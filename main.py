import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6.QtGui import QFont, QPalette, QColor


DARK_BG       = "#1a1a2e"
CARD_BG       = "#16213e"
ACCENT        = "#e94560"
ACCENT_HOVER  = "#c73652"
SECONDARY     = "#0f3460"
SECONDARY_HOVER = "#1a4f8a"
TEXT_PRIMARY  = "#eaeaea"
TEXT_MUTED    = "#7a7a9a"
SPIN_BG       = "#0f3460"
SPIN_BORDER   = "#e94560"


APP_STYLE = f"""
    QWidget {{
        background-color: {DARK_BG};
        color: {TEXT_PRIMARY};
        font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    }}
    QSpinBox {{
        background-color: {SPIN_BG};
        color: {TEXT_PRIMARY};
        border: 2px solid {SPIN_BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 15px;
        font-weight: bold;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        width: 20px;
        background-color: {SECONDARY};
        border-radius: 4px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {SECONDARY_HOVER};
    }}
    QMessageBox {{
        background-color: {CARD_BG};
        color: {TEXT_PRIMARY};
    }}
"""


class ShutdownTimer(QWidget):
    def __init__(self):
        super().__init__()
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.remaining_seconds = 0
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Shutdown Timer")
        self.setFixedSize(420, 480)
        self.setStyleSheet(APP_STYLE)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # ── Header ──────────────────────────────────────────────
        header = QLabel("SHUTDOWN TIMER")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(13)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
        font.setBold(True)
        header.setFont(font)
        header.setStyleSheet(f"color: {ACCENT}; margin-bottom: 4px;")
        main_layout.addWidget(header)

        subtitle = QLabel("Schedule a system shutdown")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; margin-bottom: 24px;")
        main_layout.addWidget(subtitle)

        # ── Countdown display card ───────────────────────────────
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {CARD_BG}; border-radius: 16px; "
            f"border: 1px solid {SECONDARY}; padding: 10px; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(4)

        self.countdown_label = QLabel("00:00:00")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_label.setMinimumHeight(80)
        countdown_font = QFont("Monospace")
        countdown_font.setPointSize(36)
        countdown_font.setBold(True)
        self.countdown_label.setFont(countdown_font)
        self.countdown_label.setStyleSheet(f"color: {TEXT_PRIMARY}; letter-spacing: 2px;")
        card_layout.addWidget(self.countdown_label)

        self.status_label = QLabel("Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        card_layout.addWidget(self.status_label)

        main_layout.addWidget(card)
        main_layout.addSpacing(18)

        # ── Spinboxes ────────────────────────────────────────────
        spin_layout = QHBoxLayout()
        spin_layout.setSpacing(14)

        hours_col = QVBoxLayout()
        hours_col.setSpacing(4)
        hours_lbl = QLabel("HOURS")
        hours_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hours_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 23)
        self.hours_spin.setFixedHeight(48)
        self.hours_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hours_col.addWidget(hours_lbl)
        hours_col.addWidget(self.hours_spin)

        minutes_col = QVBoxLayout()
        minutes_col.setSpacing(4)
        minutes_lbl = QLabel("MINUTES")
        minutes_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        minutes_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(30)
        self.minutes_spin.setFixedHeight(48)
        self.minutes_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        minutes_col.addWidget(minutes_lbl)
        minutes_col.addWidget(self.minutes_spin)

        spin_layout.addLayout(hours_col)
        spin_layout.addLayout(minutes_col)
        main_layout.addLayout(spin_layout)
        main_layout.addSpacing(18)

        # ── Buttons ──────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.set_btn = QPushButton("Set Shutdown")
        self.set_btn.setFixedHeight(48)
        self.set_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: white; border-radius: 10px;"
            f" font-size: 13px; font-weight: bold; border: none; }}"
            f"QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}"
            f"QPushButton:disabled {{ background-color: #3a3a5a; color: {TEXT_MUTED}; }}"
        )
        self.set_btn.clicked.connect(self.set_shutdown)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(48)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: {SECONDARY}; color: white; border-radius: 10px;"
            f" font-size: 13px; font-weight: bold; border: none; }}"
            f"QPushButton:hover {{ background-color: {SECONDARY_HOVER}; }}"
            f"QPushButton:disabled {{ background-color: #2a2a4a; color: {TEXT_MUTED}; }}"
        )
        self.cancel_btn.clicked.connect(self.cancel_shutdown)

        btn_layout.addWidget(self.set_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)
        main_layout.addSpacing(14)

        # ── Footer ───────────────────────────────────────────────
        footer = QLabel("Made with \u2764 by uriel")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        main_layout.addWidget(footer)

        self.setLayout(main_layout)

    def set_shutdown(self):
        hours = self.hours_spin.value()
        minutes = self.minutes_spin.value()
        total_minutes = hours * 60 + minutes

        if total_minutes == 0:
            QMessageBox.warning(self, "Invalid Time", "Please set at least 1 minute.")
            return

        try:
            subprocess.run(["sudo", "shutdown", f"+{total_minutes}"], check=True)
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Error", "Failed to schedule shutdown.\nMake sure you have sudo privileges.")
            return

        self.remaining_seconds = total_minutes * 60
        self.countdown_timer.start(1000)
        self._refresh_countdown_display()

        self.set_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.hours_spin.setEnabled(False)
        self.minutes_spin.setEnabled(False)

        time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        self.status_label.setText(f"Shutting down in {time_str}")
        self.status_label.setStyleSheet(f"color: {ACCENT}; font-size: 12px;")

    def cancel_shutdown(self):
        try:
            subprocess.run(["sudo", "shutdown", "-c"], check=True)
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Error", "Failed to cancel shutdown.")
            return

        self.countdown_timer.stop()
        self.remaining_seconds = 0
        self.countdown_label.setText("00:00:00")
        self.countdown_label.setStyleSheet(f"color: {TEXT_PRIMARY}; letter-spacing: 4px;")

        self.set_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.hours_spin.setEnabled(True)
        self.minutes_spin.setEnabled(True)
        self.status_label.setText("Shutdown cancelled")
        self.status_label.setStyleSheet("color: #4caf50; font-size: 12px;")

    def _refresh_countdown_display(self):
        t = QTime(0, 0).addSecs(self.remaining_seconds)
        self.countdown_label.setText(t.toString("HH:mm:ss"))
        if self.remaining_seconds <= 60:
            self.countdown_label.setStyleSheet(f"color: {ACCENT}; letter-spacing: 2px;")
        else:
            self.countdown_label.setStyleSheet(f"color: {TEXT_PRIMARY}; letter-spacing: 2px;")

    def update_countdown(self):
        if self.remaining_seconds <= 0:
            self.countdown_timer.stop()
            return
        self.remaining_seconds -= 1
        self._refresh_countdown_display()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Force dark palette base so native widgets inherit dark colors
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1a1a2e"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#eaeaea"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0f3460"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#16213e"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#eaeaea"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#16213e"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#eaeaea"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#e94560"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = ShutdownTimer()
    window.show()
    sys.exit(app.exec())
