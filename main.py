import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QPushButton, QMessageBox, QFrame,
    QStackedWidget, QTimeEdit, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon, QAction

APP_DIR = os.path.dirname(os.path.abspath(__file__))


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
    QTimeEdit {{
        background-color: {SPIN_BG};
        color: {TEXT_PRIMARY};
        border: 2px solid {SPIN_BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 22px;
        font-weight: bold;
    }}
    QTimeEdit::up-button, QTimeEdit::down-button {{
        width: 20px;
        background-color: {SECONDARY};
        border-radius: 4px;
    }}
    QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {{
        background-color: {SECONDARY_HOVER};
    }}
"""


class ShutdownTimer(QWidget):
    def __init__(self):
        super().__init__()
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.remaining_seconds = 0
        self.notified = set()
        self.init_ui()
        self.init_tray()

    def init_ui(self):
        self.setWindowTitle("Shutdown Timer")
        self.setFixedSize(420, 530)
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
        main_layout.addSpacing(14)

        # ── Mode toggle ──────────────────────────────────────────
        toggle_layout = QHBoxLayout()
        toggle_layout.setSpacing(0)

        toggle_frame = QFrame()
        toggle_frame.setStyleSheet(
            f"QFrame {{ background-color: {SECONDARY}; border-radius: 10px; }}"
        )
        toggle_frame.setFixedHeight(38)
        tf_layout = QHBoxLayout(toggle_frame)
        tf_layout.setContentsMargins(4, 4, 4, 4)
        tf_layout.setSpacing(4)

        def _toggle_style(active):
            if active:
                return (f"QPushButton {{ background-color: {ACCENT}; color: white;"
                        f" border-radius: 7px; font-size: 12px; font-weight: bold; border: none; }}")
            return (f"QPushButton {{ background-color: transparent; color: {TEXT_MUTED};"
                    f" border-radius: 7px; font-size: 12px; border: none; }}"
                    f"QPushButton:hover {{ color: {TEXT_PRIMARY}; }}")

        self.mode_duration_btn = QPushButton("Duration")
        self.mode_duration_btn.setFixedHeight(30)
        self.mode_duration_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_duration_btn.setStyleSheet(_toggle_style(True))
        self.mode_duration_btn.clicked.connect(lambda: self._set_mode(0))

        self.mode_exact_btn = QPushButton("Exact Time")
        self.mode_exact_btn.setFixedHeight(30)
        self.mode_exact_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_exact_btn.setStyleSheet(_toggle_style(False))
        self.mode_exact_btn.clicked.connect(lambda: self._set_mode(1))

        self._toggle_style_fn = _toggle_style
        tf_layout.addWidget(self.mode_duration_btn)
        tf_layout.addWidget(self.mode_exact_btn)
        toggle_layout.addWidget(toggle_frame)
        main_layout.addLayout(toggle_layout)
        main_layout.addSpacing(14)

        # ── Stacked input panels ─────────────────────────────────
        self.input_stack = QStackedWidget()
        self.input_stack.setFixedHeight(78)

        # Page 0 — Duration
        duration_page = QWidget()
        spin_layout = QHBoxLayout(duration_page)
        spin_layout.setContentsMargins(0, 0, 0, 0)
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

        # Page 1 — Exact time
        exact_page = QWidget()
        exact_layout = QVBoxLayout(exact_page)
        exact_layout.setContentsMargins(0, 0, 0, 0)
        exact_layout.setSpacing(4)
        exact_lbl = QLabel("SHUT DOWN AT")
        exact_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exact_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("hh:mm AP")
        self.time_edit.setTime(QTime.currentTime().addSecs(3600))
        self.time_edit.setFixedHeight(48)
        self.time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exact_layout.addWidget(exact_lbl)
        exact_layout.addWidget(self.time_edit)

        self.input_stack.addWidget(duration_page)
        self.input_stack.addWidget(exact_page)
        main_layout.addWidget(self.input_stack)
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

    def init_tray(self):
        icon = QIcon(os.path.join(APP_DIR, "icon.png"))
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Shutdown Timer — Idle")

        menu = QMenu()
        self.tray_toggle_action = QAction("Hide", self)
        self.tray_toggle_action.triggered.connect(self.toggle_window)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        menu.addAction(self.tray_toggle_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def toggle_window(self):
        if self.isVisible():
            self.hide()
            self.tray_toggle_action.setText("Show")
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.tray_toggle_action.setText("Hide")

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_toggle_action.setText("Show")
        self.tray.showMessage(
            "Shutdown Timer",
            "Running in the background. Double-click the tray icon to restore.",
            QSystemTrayIcon.MessageIcon.Information,
            2500
        )

    def _set_mode(self, index):
        self.input_stack.setCurrentIndex(index)
        self.mode_duration_btn.setStyleSheet(self._toggle_style_fn(index == 0))
        self.mode_exact_btn.setStyleSheet(self._toggle_style_fn(index == 1))

    def set_shutdown(self):
        mode = self.input_stack.currentIndex()

        if mode == 0:
            # Duration mode
            hours = self.hours_spin.value()
            minutes = self.minutes_spin.value()
            total_minutes = hours * 60 + minutes
            if total_minutes == 0:
                QMessageBox.warning(self, "Invalid Time", "Please set at least 1 minute.")
                return
            status_str = f"Shutting down in {hours}h {minutes}m" if hours else f"Shutting down in {minutes}m"
        else:
            # Exact time mode
            target = self.time_edit.time()
            now = QTime.currentTime()
            total_minutes = now.secsTo(target) // 60
            if total_minutes <= 0:
                # Target is tomorrow
                total_minutes += 24 * 60
            if total_minutes <= 0:
                QMessageBox.warning(self, "Invalid Time", "Please choose a future time.")
                return
            status_str = f"Shutting down at {target.toString('hh:mm AP')}"

        try:
            subprocess.run(["sudo", "shutdown", f"+{total_minutes}"], check=True)
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Error", "Failed to schedule shutdown.\nMake sure you have sudo privileges.")
            return

        self.remaining_seconds = total_minutes * 60
        self.notified.clear()
        self.countdown_timer.start(1000)
        self._refresh_countdown_display()

        self.set_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.mode_duration_btn.setEnabled(False)
        self.mode_exact_btn.setEnabled(False)
        self.hours_spin.setEnabled(False)
        self.minutes_spin.setEnabled(False)
        self.time_edit.setEnabled(False)

        self.status_label.setText(status_str)
        self.status_label.setStyleSheet(f"color: {ACCENT}; font-size: 12px;")

    def cancel_shutdown(self):
        try:
            subprocess.run(["sudo", "shutdown", "-c"], check=True)
        except subprocess.CalledProcessError:
            QMessageBox.critical(self, "Error", "Failed to cancel shutdown.")
            return

        self.countdown_timer.stop()
        self.remaining_seconds = 0
        self.notified.clear()
        self.countdown_label.setText("00:00:00")
        self.countdown_label.setStyleSheet(f"color: {TEXT_PRIMARY}; letter-spacing: 4px;")

        self.set_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.mode_duration_btn.setEnabled(True)
        self.mode_exact_btn.setEnabled(True)
        self.hours_spin.setEnabled(True)
        self.minutes_spin.setEnabled(True)
        self.time_edit.setEnabled(True)
        self.status_label.setText("Shutdown cancelled")
        self.status_label.setStyleSheet("color: #4caf50; font-size: 12px;")

    def _refresh_countdown_display(self):
        t = QTime(0, 0).addSecs(self.remaining_seconds)
        time_str = t.toString("HH:mm:ss")
        self.countdown_label.setText(time_str)
        self.tray.setToolTip(f"Shutdown Timer — {time_str} remaining")
        if self.remaining_seconds <= 60:
            self.countdown_label.setStyleSheet(f"color: {ACCENT}; letter-spacing: 2px;")
        else:
            self.countdown_label.setStyleSheet(f"color: {TEXT_PRIMARY}; letter-spacing: 2px;")

    def _notify(self, minutes):
        messages = {
            10: ("Shutting down in 10 minutes", "Save your work!"),
            5:  ("Shutting down in 5 minutes",  "Save your work now!"),
            1:  ("Shutting down in 1 minute",   "Last chance to save!"),
        }
        title, body = messages[minutes]
        icon = os.path.join(APP_DIR, "icon.png")
        subprocess.Popen(
            ["notify-send", "-i", icon, "-u", "critical", title, body],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def update_countdown(self):
        if self.remaining_seconds <= 0:
            self.countdown_timer.stop()
            return
        self.remaining_seconds -= 1
        self._refresh_countdown_display()

        minutes_left = self.remaining_seconds // 60
        seconds_left = self.remaining_seconds % 60
        for threshold in (10, 5, 1):
            if minutes_left == threshold and seconds_left == 0 and threshold not in self.notified:
                self.notified.add(threshold)
                self._notify(threshold)
                break


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

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
