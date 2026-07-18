import sys
import os
import math
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QPushButton, QMessageBox,
    QStackedWidget, QTimeEdit, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QTime, QRectF, QPointF
from PyQt6.QtGui import (
    QFont, QPalette, QColor, QIcon, QAction,
    QPainter, QPen, QConicalGradient, QFontMetrics
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = "/usr/share/sounds/freedesktop/stereo"
SOUND_TICK = os.path.join(SOUND_DIR, "bell.oga")
SOUND_ALARM = os.path.join(SOUND_DIR, "alarm-clock-elapsed.oga")

# ── "Ember" palette — a machine settling down for the night ─────────
BG        = "#14100b"   # warm near-black
SURFACE   = "#1e1710"   # cards, inputs
RAISED    = "#2a2014"   # hover surfaces
HAIRLINE  = "#382b1b"   # borders
EMBER     = "#ffa348"   # primary accent
EMBER_HI  = "#ffbd75"   # hover / bright
EMBER_LOW = "#c97a33"   # pressed
COAL      = "#ff5f30"   # last-minute heat
TEXT      = "#f3ead9"   # warm parchment
MUTED     = "#97896e"   # secondary text
FAINT     = "#5c5140"   # tertiary / idle
OK        = "#a9bb85"   # calm confirmation
BTN_TEXT  = "#201305"   # dark text on ember

SANS = "Lato"

APP_STYLE = f"""
    QWidget {{
        background-color: {BG};
        color: {TEXT};
        font-family: '{SANS}', 'DejaVu Sans', sans-serif;
    }}
    QSpinBox, QTimeEdit {{
        background-color: {SURFACE};
        color: {TEXT};
        border: 1px solid {HAIRLINE};
        border-radius: 9px;
        padding: 6px 8px;
        font-size: 20px;
        font-weight: 300;
    }}
    QSpinBox:focus, QTimeEdit:focus {{
        border: 1px solid {EMBER_LOW};
    }}
    QSpinBox:disabled, QTimeEdit:disabled {{
        color: {FAINT};
        border-color: {SURFACE};
    }}
    QSpinBox::up-button, QSpinBox::down-button,
    QTimeEdit::up-button, QTimeEdit::down-button {{
        width: 22px;
        background-color: transparent;
        border: none;
        border-radius: 5px;
        margin: 2px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {{
        background-color: {RAISED};
    }}
    QMessageBox {{
        background-color: {SURFACE};
        color: {TEXT};
    }}
    QMessageBox QPushButton {{
        background-color: {RAISED};
        color: {TEXT};
        border: 1px solid {HAIRLINE};
        border-radius: 7px;
        padding: 6px 18px;
    }}
    QMessageBox QPushButton:hover {{
        border-color: {EMBER_LOW};
    }}
    QMenu {{
        background-color: {SURFACE};
        color: {TEXT};
        border: 1px solid {HAIRLINE};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 22px;
        border-radius: 5px;
    }}
    QMenu::item:selected {{
        background-color: {RAISED};
        color: {EMBER_HI};
    }}
    QToolTip {{
        background-color: {RAISED};
        color: {TEXT};
        border: 1px solid {HAIRLINE};
    }}
"""


def _lerp_color(c1, c2, t):
    a, b = QColor(c1), QColor(c2)
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    )


class EmberRing(QWidget):
    """Countdown dial drawn as a power symbol: a ring with a gap at the
    top and a tick through it. The ring drains clockwise as time runs
    out and shifts from ember amber to coal red in the final stretch."""

    GAP_DEG = 30        # total gap at twelve o'clock
    STROKE = 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fraction = 0.0        # 0 = idle/empty, 1 = full
        self.remaining_seconds = 0
        self.running = False
        self.setMinimumSize(260, 260)

    def set_state(self, running, fraction, remaining_seconds):
        self.running = running
        self.fraction = max(0.0, min(1.0, fraction))
        self.remaining_seconds = remaining_seconds
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        cx, cy = self.width() / 2, self.height() / 2
        margin = self.STROKE * 2.4
        r = side / 2 - margin
        rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)

        span_full = 360 - self.GAP_DEG
        start = 90 - self.GAP_DEG / 2          # right edge of the gap

        hot = self.running and self.remaining_seconds <= 60
        heat = 0.0
        if self.running:
            heat = 1.0 - min(1.0, self.remaining_seconds / 300)  # warm up over last 5 min
        arc_color = _lerp_color(EMBER, COAL, heat)

        # Track
        pen = QPen(QColor(RAISED), self.STROKE, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, int(start * 16), int(-span_full * 16))

        # Remaining arc
        if self.running and self.fraction > 0:
            span = span_full * self.fraction

            glow = QColor(arc_color)
            glow.setAlpha(60 if not hot else 95)
            p.setPen(QPen(glow, self.STROKE * 2.6, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, int(start * 16), int(-span * 16))

            grad = QConicalGradient(QPointF(cx, cy), start)
            grad.setColorAt(0.0, _lerp_color(EMBER_HI, COAL, heat))
            grad.setColorAt(min(0.999, span / 360), arc_color)
            p.setPen(QPen(grad, self.STROKE, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, int(start * 16), int(-span * 16))

            # Spark at the draining head
            head_deg = math.radians(start - span)
            hx = cx + r * math.cos(head_deg)
            hy = cy - r * math.sin(head_deg)
            halo = QColor("#ffd9a0")
            halo.setAlpha(70)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo)
            p.drawEllipse(QPointF(hx, hy), self.STROKE * 1.5, self.STROKE * 1.5)
            p.setBrush(QColor("#fff3dd"))
            p.drawEllipse(QPointF(hx, hy), self.STROKE * 0.62, self.STROKE * 0.62)

        # Power tick through the gap
        tick_color = QColor(arc_color) if self.running else QColor(FAINT)
        p.setPen(QPen(tick_color, self.STROKE, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(cx, cy - r - self.STROKE * 1.1),
                   QPointF(cx, cy - r + self.STROKE * 1.4))

        # Time, painted in fixed slots so digits never jitter
        t = QTime(0, 0).addSecs(self.remaining_seconds)
        text = t.toString("HH:mm:ss")
        digit_font = QFont(SANS)
        digit_font.setPointSizeF(side * 0.115)
        digit_font.setWeight(QFont.Weight.Light)
        p.setFont(digit_font)
        fm = QFontMetrics(digit_font)
        slot = fm.horizontalAdvance("8") * 1.08
        colon_slot = slot * 0.52
        total_w = sum(colon_slot if ch == ":" else slot for ch in text)
        x = cx - total_w / 2
        baseline = cy + fm.capHeight() / 2
        p.setPen(QColor(TEXT) if self.running else QColor(FAINT))
        for ch in text:
            w = colon_slot if ch == ":" else slot
            p.drawText(QRectF(x, baseline - fm.ascent(), w, fm.height()),
                       Qt.AlignmentFlag.AlignCenter, ch)
            x += w

        # Small caption under the digits
        cap_font = QFont(SANS)
        cap_font.setPointSizeF(max(7.0, side * 0.026))
        cap_font.setWeight(QFont.Weight.DemiBold)
        cap_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
        p.setFont(cap_font)
        p.setPen(QColor(arc_color) if hot else QColor(MUTED if self.running else FAINT))
        caption = "remaining" if self.running else "ready"
        cap_rect = QRectF(cx - r, baseline + side * 0.03, 2 * r, side * 0.08)
        p.drawText(cap_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   caption.upper())
        p.end()


class ShutdownTimer(QWidget):
    def __init__(self):
        super().__init__()
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.remaining_seconds = 0
        self.total_seconds = 0
        self.notified = set()
        self.action = "shutdown"  # shutdown | reboot | suspend | hibernate
        self.sound_enabled = True
        self.running = False
        self.init_ui()
        self.init_tray()

    # ── UI ───────────────────────────────────────────────────────────
    def init_ui(self):
        self.setWindowTitle("Shutdown Timer")
        self.setFixedSize(400, 668)
        self.setStyleSheet(APP_STYLE)

        root = QVBoxLayout()
        root.setSpacing(0)
        root.setContentsMargins(28, 22, 28, 18)

        # Wordmark
        wordmark = QLabel("shutdown <span style='color:#ffa348;'>timer</span>")
        wordmark.setTextFormat(Qt.TextFormat.RichText)
        wm_font = QFont(SANS)
        wm_font.setPointSize(12)
        wm_font.setWeight(QFont.Weight.DemiBold)
        wm_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        wordmark.setFont(wm_font)
        wordmark.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(wordmark)

        # Dial
        self.ring = EmberRing()
        root.addWidget(self.ring)

        self.status_label = QLabel("Pick a time, bank the ember.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        root.addWidget(self.status_label)
        root.addSpacing(18)

        # Mode tabs — underline style
        tab_row = QHBoxLayout()
        tab_row.setSpacing(22)
        tab_row.addStretch(1)
        self.mode_duration_btn = self._make_tab("Duration")
        self.mode_duration_btn.clicked.connect(lambda: self._set_mode(0))
        self.mode_exact_btn = self._make_tab("Exact time")
        self.mode_exact_btn.clicked.connect(lambda: self._set_mode(1))
        tab_row.addWidget(self.mode_duration_btn)
        tab_row.addWidget(self.mode_exact_btn)
        tab_row.addStretch(1)
        root.addLayout(tab_row)
        root.addSpacing(12)

        # Input stack
        self.input_stack = QStackedWidget()
        self.input_stack.setFixedHeight(74)

        duration_page = QWidget()
        spin_layout = QHBoxLayout(duration_page)
        spin_layout.setContentsMargins(0, 0, 0, 0)
        spin_layout.setSpacing(14)
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 23)
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(30)
        for spin, caption in ((self.hours_spin, "HOURS"), (self.minutes_spin, "MINUTES")):
            col = QVBoxLayout()
            col.setSpacing(5)
            lbl = QLabel(caption)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color: {FAINT}; font-size: 9px; font-weight: 600; letter-spacing: 2px;")
            spin.setFixedHeight(46)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl)
            col.addWidget(spin)
            spin_layout.addLayout(col)

        exact_page = QWidget()
        exact_layout = QVBoxLayout(exact_page)
        exact_layout.setContentsMargins(0, 0, 0, 0)
        exact_layout.setSpacing(5)
        exact_lbl = QLabel("POWER OFF AT")
        exact_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exact_lbl.setStyleSheet(
            f"color: {FAINT}; font-size: 9px; font-weight: 600; letter-spacing: 2px;")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("hh:mm AP")
        self.time_edit.setTime(QTime.currentTime().addSecs(3600))
        self.time_edit.setFixedHeight(46)
        self.time_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        exact_layout.addWidget(exact_lbl)
        exact_layout.addWidget(self.time_edit)

        self.input_stack.addWidget(duration_page)
        self.input_stack.addWidget(exact_page)
        root.addWidget(self.input_stack)
        root.addSpacing(10)

        # Preset chips
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(8)
        chip_style = (
            f"QPushButton {{ background-color: transparent; color: {MUTED};"
            f" border: 1px solid {HAIRLINE}; border-radius: 13px;"
            f" font-size: 11px; padding: 4px 0px; }}"
            f"QPushButton:hover {{ border-color: {EMBER_LOW}; color: {EMBER_HI}; }}"
            f"QPushButton:disabled {{ color: {FAINT}; border-color: {SURFACE}; }}"
        )
        self.preset_btns = []
        for label, h, m in [("15m", 0, 15), ("30m", 0, 30), ("1h", 1, 0),
                            ("2h", 2, 0), ("3h", 3, 0)]:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(chip_style)
            btn.clicked.connect(lambda _, hh=h, mm=m: self._apply_preset(hh, mm))
            presets_layout.addWidget(btn)
            self.preset_btns.append(btn)
        root.addLayout(presets_layout)
        root.addSpacing(20)

        # Action pills
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(7)
        self.action_btns = {}
        for key, label in [("shutdown", "Shutdown"), ("reboot", "Reboot"),
                           ("suspend", "Suspend"), ("hibernate", "Hibernate")]:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._set_action(k))
            actions_layout.addWidget(btn)
            self.action_btns[key] = btn
        self._restyle_actions()
        root.addLayout(actions_layout)
        root.addSpacing(18)

        # Primary button — becomes Cancel while armed
        self.main_btn = QPushButton("Start timer")
        self.main_btn.setFixedHeight(48)
        self.main_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_btn.clicked.connect(self._main_clicked)
        self._style_main_btn(armed=False)
        root.addWidget(self.main_btn)
        root.addSpacing(12)

        # Footer
        footer_layout = QHBoxLayout()
        footer = QLabel("made with ❤ by uriel")
        footer.setStyleSheet(f"color: {FAINT}; font-size: 11px;")
        self.sound_btn = QPushButton("SOUND ON")
        self.sound_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sound_btn.setToolTip("Click to mute")
        self.sound_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {MUTED};"
            f" font-size: 9px; font-weight: 600; letter-spacing: 2px; padding: 4px 6px; }}"
            f"QPushButton:hover {{ color: {EMBER_HI}; }}"
        )
        self.sound_btn.clicked.connect(self._toggle_sound)
        footer_layout.addWidget(footer, stretch=1)
        footer_layout.addWidget(self.sound_btn)
        root.addLayout(footer_layout)

        self.setLayout(root)
        self._set_mode(0)

    def _make_tab(self, label):
        btn = QPushButton(label)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(28)
        return btn

    def _tab_style(self, active):
        if active:
            return (f"QPushButton {{ background: transparent; border: none;"
                    f" border-bottom: 2px solid {EMBER}; color: {TEXT};"
                    f" font-size: 12px; font-weight: 600; padding: 0 2px 6px 2px; }}")
        return (f"QPushButton {{ background: transparent; border: none;"
                f" border-bottom: 2px solid transparent; color: {MUTED};"
                f" font-size: 12px; padding: 0 2px 6px 2px; }}"
                f"QPushButton:hover {{ color: {TEXT}; }}"
                f"QPushButton:disabled {{ color: {FAINT}; }}")

    def _pill_style(self, active):
        if active:
            return (f"QPushButton {{ background-color: {RAISED}; color: {EMBER_HI};"
                    f" border: 1px solid {EMBER_LOW}; border-radius: 16px;"
                    f" font-size: 11px; font-weight: 600; }}")
        return (f"QPushButton {{ background-color: transparent; color: {MUTED};"
                f" border: 1px solid transparent; border-radius: 16px; font-size: 11px; }}"
                f"QPushButton:hover {{ color: {TEXT}; border-color: {HAIRLINE}; }}"
                f"QPushButton:disabled {{ color: {FAINT}; }}")

    def _style_main_btn(self, armed):
        if armed:
            self.main_btn.setText("Cancel " + self.action)
            self.main_btn.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {COAL};"
                f" border: 1px solid {COAL}; border-radius: 12px;"
                f" font-size: 13px; font-weight: 600; letter-spacing: 1px; }}"
                f"QPushButton:hover {{ background-color: #2a160e; }}"
            )
        else:
            self.main_btn.setText("Start timer")
            self.main_btn.setStyleSheet(
                f"QPushButton {{ background-color: {EMBER}; color: {BTN_TEXT};"
                f" border: none; border-radius: 12px;"
                f" font-size: 13px; font-weight: 700; letter-spacing: 1px; }}"
                f"QPushButton:hover {{ background-color: {EMBER_HI}; }}"
                f"QPushButton:pressed {{ background-color: {EMBER_LOW}; }}"
            )

    def _restyle_actions(self):
        for k, btn in self.action_btns.items():
            btn.setStyleSheet(self._pill_style(k == self.action))

    # ── Tray ─────────────────────────────────────────────────────────
    def init_tray(self):
        icon_path = os.path.join(APP_DIR, "icon.png")
        icon = QIcon(icon_path)
        if icon.isNull():
            icon = QIcon.fromTheme("system-run")

        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Shutdown Timer")

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

    # ── State changes ────────────────────────────────────────────────
    def _set_action(self, key):
        self.action = key
        self._restyle_actions()

    def _apply_preset(self, hours, minutes):
        self._set_mode(0)
        self.hours_spin.setValue(hours)
        self.minutes_spin.setValue(minutes)

    def _set_mode(self, index):
        self.input_stack.setCurrentIndex(index)
        self.mode_duration_btn.setStyleSheet(self._tab_style(index == 0))
        self.mode_exact_btn.setStyleSheet(self._tab_style(index == 1))

    def _set_inputs_enabled(self, enabled):
        for w in (self.mode_duration_btn, self.mode_exact_btn,
                  self.hours_spin, self.minutes_spin, self.time_edit,
                  *self.preset_btns, *self.action_btns.values()):
            w.setEnabled(enabled)

    def _main_clicked(self):
        if self.running:
            self.cancel_shutdown()
        else:
            self.set_shutdown()

    def set_shutdown(self):
        mode = self.input_stack.currentIndex()

        if mode == 0:
            hours = self.hours_spin.value()
            minutes = self.minutes_spin.value()
            total_minutes = hours * 60 + minutes
            if total_minutes == 0:
                QMessageBox.warning(self, "Invalid Time", "Please set at least 1 minute.")
                return
        else:
            target = self.time_edit.time()
            now = QTime.currentTime()
            total_minutes = now.secsTo(target) // 60
            if total_minutes <= 0:
                # Target is tomorrow
                total_minutes += 24 * 60
            if total_minutes <= 0:
                QMessageBox.warning(self, "Invalid Time", "Please choose a future time.")
                return

        verbs = {"shutdown": "Shutting down", "reboot": "Rebooting",
                 "suspend": "Suspending", "hibernate": "Hibernating"}
        verb = verbs[self.action]
        if mode == 0:
            status_str = f"{verb} in {hours}h {minutes}m" if hours else f"{verb} in {minutes}m"
        else:
            status_str = f"{verb} at {target.toString('hh:mm AP')}"

        if self.action in ("shutdown", "reboot"):
            cmd = ["sudo", "shutdown"] + (["-r"] if self.action == "reboot" else []) + [f"+{total_minutes}"]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to schedule {self.action}.\nMake sure you have sudo privileges.")
                return
        # suspend/hibernate: executed by Python timer when countdown reaches 0

        self.running = True
        self.total_seconds = total_minutes * 60
        self.remaining_seconds = self.total_seconds
        self.notified.clear()
        self.countdown_timer.start(1000)
        self._refresh_countdown_display()

        self._set_inputs_enabled(False)
        self._style_main_btn(armed=True)
        self.status_label.setText(status_str)
        self.status_label.setStyleSheet(f"color: {EMBER}; font-size: 12px;")

    def cancel_shutdown(self):
        if self.action in ("shutdown", "reboot"):
            try:
                subprocess.run(["sudo", "shutdown", "-c"], check=True)
            except subprocess.CalledProcessError:
                QMessageBox.critical(self, "Error", f"Failed to cancel {self.action}.")
                return

        self.countdown_timer.stop()
        self.running = False
        self.remaining_seconds = 0
        self.total_seconds = 0
        self.notified.clear()
        self.ring.set_state(False, 0.0, 0)
        self.tray.setToolTip("Shutdown Timer — Idle")

        self._set_inputs_enabled(True)
        self._style_main_btn(armed=False)
        labels = {"shutdown": "Shutdown", "reboot": "Reboot",
                  "suspend": "Suspend", "hibernate": "Hibernate"}
        self.status_label.setText(f"{labels[self.action]} cancelled — ember banked.")
        self.status_label.setStyleSheet(f"color: {OK}; font-size: 12px;")

    def _refresh_countdown_display(self):
        t = QTime(0, 0).addSecs(self.remaining_seconds)
        time_str = t.toString("HH:mm:ss")
        fraction = (self.remaining_seconds / self.total_seconds) if self.total_seconds else 0
        self.ring.set_state(self.running, fraction, self.remaining_seconds)
        self.tray.setToolTip(f"Shutdown Timer — {time_str} remaining")

    def _notify(self, minutes):
        verbs = {"shutdown": "Shutting down", "reboot": "Rebooting",
                 "suspend": "Suspending", "hibernate": "Hibernating"}
        verb = verbs[self.action]
        bodies = {10: "Save your work!", 5: "Save your work now!", 1: "Last chance to save!"}
        title = f"{verb} in {minutes} minute{'s' if minutes > 1 else ''}"
        body = bodies[minutes]
        icon = os.path.join(APP_DIR, "icon.png")
        subprocess.Popen(
            ["notify-send", "-i", icon, "-u", "critical", title, body],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        if self.sound_enabled:
            self.sound_btn.setText("SOUND ON")
            self.sound_btn.setToolTip("Click to mute")
        else:
            self.sound_btn.setText("SOUND OFF")
            self.sound_btn.setToolTip("Click to unmute")

    def _play(self, path):
        if not self.sound_enabled:
            return
        subprocess.Popen(
            ["paplay", path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def update_countdown(self):
        if self.remaining_seconds <= 0:
            self.countdown_timer.stop()
            self._play(SOUND_ALARM)
            if self.action in ("suspend", "hibernate"):
                subprocess.Popen(
                    ["systemctl", self.action],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            return
        self.remaining_seconds -= 1
        self._refresh_countdown_display()

        # Tick every second in the last 10 seconds
        if self.remaining_seconds <= 10:
            self._play(SOUND_TICK)

        minutes_left = self.remaining_seconds // 60
        seconds_left = self.remaining_seconds % 60
        for threshold in (10, 5, 1):
            if minutes_left == threshold and seconds_left == 0 and threshold not in self.notified:
                self.notified.add(threshold)
                self._notify(threshold)
                break


if __name__ == "__main__":
    # Fix for tray icon on Wayland (GNOME/KDE)
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    app.setApplicationName("Shutdown Timer")
    app.setOrganizationName("uriel")
    app.setDesktopFileName("shutdown-timer")
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    # Warm dark palette so native widgets inherit the theme
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(RAISED))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(EMBER))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(BTN_TEXT))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(RAISED))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    app.setPalette(palette)

    window = ShutdownTimer()
    window.show()
    sys.exit(app.exec())
