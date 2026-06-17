import sys
import os
import threading
import uuid
import time

# ── SESSION_ID unico por proceso ────────────────────────────────────────────
# Cada instancia del ejecutable/script genera su propio UUID al iniciarse.
# NO se comparte entre instancias concurrentes del mismo exe.
# Esto es CRITICO para la concurrencia: cada ventana = usuario diferente.
SESSION_ID = str(uuid.uuid4())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.cliente_lib import (
    check, login, register,
    select_seat, deselect_seat, reserve, reserve_multiple,
    confirm, cancel, release_session,
    global_state, get_log, get_ttl, DEFAULT_HOST, DEFAULT_PORT, set_server_address
)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QLineEdit,
    QTextEdit, QFrame, QScrollArea, QSizePolicy, QSpacerItem,
    QMessageBox, QTabWidget, QGroupBox, QStatusBar, QSplitter, QStackedWidget,
    QLayout, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QObject, QProcess
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap

# ── Paleta ─────────────────────────────────────────────────────────────────
BG_DEEP    = "#09090b"
BG_CARD    = "#18181b"
BG_PANEL   = "#27272a"
BG_HOVER   = "#3f3f46"
ACCENT     = "#2563eb"
ACCENT2    = "#3b82f6"
GREEN      = "#10b981"
YELLOW     = "#f59e0b"
RED        = "#ef4444"
TEXT_PRI   = "#f8fafc"
TEXT_SEC   = "#cbd5e1"
TEXT_MUTED = "#64748b"
BORDER     = "#3f3f46"

SEAT_AVAILABLE = "#334155"
SEAT_RESERVED  = "#3b82f6"  # Reservado por otros (Blue)
SEAT_SOLD      = "#e11d48"  # Vendido
SEAT_SELECTED  = "#f59e0b"  # Mi selección / Mi reserva (Orange)

ZONE_COLORS = {
    0: "#ec4899",
    1: "#a855f7",
    2: "#8b5cf6",
    3: "#06b6d4",
    4: "#14b8a6",
}
ZONE_NAMES  = {
    0: "VIP",
    1: "Preferencial Norte",
    2: "Preferencial Sur",
    3: "General Oeste",
    4: "General Este",
}
ZONE_PRICES = {
    0: 85_000,    # VIP            ₡85 000
    1: 55_000,    # Preferencial Norte
    2: 55_000,    # Preferencial Sur
    3: 30_000,    # General Oeste
    4: 30_000,    # General Este
}

# ── Usuarios predefinidos para login local ──────────────────────────────────
LOGIN_USERS = {
    "keylor":   "1234",
    "allan":    "1234",
    "admin":    "admin",
    "usuario1": "pass1",
}


STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DEEP};
    color: {TEXT_PRI};
    font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {BG_CARD};
    border-radius: 8px;
}}
QTabBar::tab {{
    background: {BG_PANEL};
    color: {TEXT_SEC};
    padding: 10px 24px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    font-size: 15px;
    font-weight: 500;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {BG_CARD};
    color: {TEXT_PRI};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover {{
    background: {BG_HOVER};
    color: {TEXT_PRI};
}}
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #2563eb);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 22px;
    font-size: 15px;
    font-weight: 700;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #60a5fa, stop:1 #3b82f6);
}}
QPushButton:pressed {{
    background: #1d4ed8;
}}
QPushButton:disabled {{
    background: #27272a;
    color: #64748b;
}}
QPushButton#secondary {{
    background: #27272a;
    border: 1px solid #3f3f46;
    color: #cbd5e1;
}}
QPushButton#secondary:hover {{
    background: #3f3f46;
    border-color: #3b82f6;
    color: #ffffff;
}}
QPushButton#danger {{
    background-color: #ef4444;
}}
QPushButton#danger:hover {{
    background-color: #f87171;
}}
QPushButton#success {{
    background-color: #10b981;
}}
QPushButton#success:hover {{
    background-color: #34d399;
}}
QComboBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    color: {TEXT_PRI};
    font-size: 15px;
    min-width: 160px;
}}
QComboBox:hover {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox QAbstractItemView {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    color: {TEXT_PRI};
    selection-background-color: {ACCENT};
}}
QLineEdit {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    color: {TEXT_PRI};
    font-size: 15px;
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QTextEdit {{
    background-color: {BG_DEEP};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: #a0aec0;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 14px;
    padding: 8px;
}}
QScrollBar:vertical {{
    background: {BG_DEEP};
    width: 12px;
    border-radius: 6px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 6px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar:horizontal {{
    background: {BG_DEEP};
    height: 12px;
    border-radius: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 6px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-top: 20px;
    padding-top: 16px;
    font-size: 15px;
    font-weight: 600;
    color: {TEXT_SEC};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {ACCENT2};
}}
QStatusBar {{
    background: {BG_CARD};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
    font-size: 14px;
}}
QSplitter::handle {{ background: {BORDER}; width: 1px; }}
QLabel#heading {{
    font-size: 34px;
    font-weight: 700;
    color: {TEXT_PRI};
}}
QLabel#subheading {{
    font-size: 15px;
    color: {TEXT_SEC};
}}
QLabel#stat_value {{
    font-size: 34px;
    font-weight: 700;
}}
QLabel#stat_label {{
    font-size: 13px;
    color: {TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QPushButton#success {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669);
    color: white; border: none; border-radius: 8px; font-weight: 800; font-size: 14px;
}}
QPushButton#success:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #34d399, stop:1 #10b981); }}
QPushButton#success:pressed {{ background: #047857; }}

QPushButton#danger {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ef4444, stop:1 #dc2626);
    color: white; border: none; border-radius: 8px; font-weight: 800; font-size: 14px;
}}
QPushButton#danger:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f87171, stop:1 #ef4444); }}
QPushButton#danger:pressed {{ background: #b91c1c; }}
"""


# Conjunto global para evitar que el recolector de basura de Python destruya
# hilos QThread que todavía están ejecutándose en C++.
_active_workers: set = set()


class NetworkWorker(QThread):
    result = pyqtSignal(dict)
    error  = pyqtSignal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn   = fn
        self.args = args
        # Registrar en el set global ANTES de start() para proteger el objeto
        _active_workers.add(self)
        self.finished.connect(self._safe_cleanup)

    def _safe_cleanup(self):
        """Se ejecuta en el hilo principal vía señal. Elimina la referencia
        global y programa la destrucción segura del objeto Qt."""
        _active_workers.discard(self)
        self.deleteLater()

    def run(self):
        try:
            resp = self.fn(*self.args)
            self.result.emit(resp)
        except ConnectionRefusedError:
            self.error.emit("No se pudo conectar al servidor. \u00bfEst\u00e1 corriendo en el puerto 9090?")
        except Exception as e:
            self.error.emit(str(e))


class PurchaseController(QObject):
    reserve_result = pyqtSignal(dict)
    tx_result = pyqtSignal(dict, str)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def reserve_selection(self, selected):
        if not selected:
            return

        if len(selected) == 1:
            z, r, c = selected[0]
            worker = NetworkWorker(reserve, z, r, c, SESSION_ID)
        else:
            seats = [[z, r, c] for z, r, c in selected]
            worker = NetworkWorker(reserve_multiple, seats, SESSION_ID)

        worker.result.connect(self.reserve_result.emit)
        worker.error.connect(self.error.emit)
        worker.start()

    def confirm_purchase(self, tx_id):
        self._run_tx(confirm, tx_id, SESSION_ID, "Compra confirmada")

    def cancel_reservation(self, tx_id):
        self._run_tx(cancel, tx_id, SESSION_ID, "Reserva cancelada")

    def _run_tx(self, fn, tx_id, session_id, success_msg):
        worker = NetworkWorker(fn, tx_id, session_id)
        worker.result.connect(lambda resp: self.tx_result.emit(resp, success_msg))
        worker.error.connect(self.error.emit)
        worker.start()


# ── Botón de asiento ────────────────────────────────────────────────────────
class SeatButton(QPushButton):
    error_clicked = pyqtSignal(str)
    
    def __init__(self, row, col, state="D", parent=None):
        super().__init__(parent)
        self.seat_row   = row
        self.seat_col   = col
        self.seat_state = state
        self.selected   = False  # True = pre-seleccionado por ESTE usuario
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    def set_state(self, state):
        self.seat_state = state
        self.selected   = False
        self._apply_style()

    def sync_state(self, new_state):
        if self.seat_state == new_state and not self.selected:
            return
        self.seat_state = new_state
        if new_state not in ("D", "S"):
            self.selected = False
        self._apply_style()

    def _apply_style(self):
        hover_css = f"QPushButton:hover {{ border: 2px solid #38bdf8; background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, stop:0 #38bdf8, stop:1 {SEAT_SELECTED}); }}"

        if self.selected:
            color = SEAT_SELECTED
            bg = f"qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, stop:0 {color}, stop:1 #b45309)"
            border_color = '#ffffff'
            border_w = '2px'
            text_color = '#ffffff'
        elif self.seat_state in ("S", "R"):
            color = SEAT_RESERVED
            bg = f"qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, stop:0 {color}, stop:1 #1e3a8a)"
            border_color = '#09090b'
            border_w = '1px'
            text_color = '#ffffff'
            hover_css = ""
        elif self.seat_state == "V":
            color = SEAT_SOLD
            bg = f"qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, stop:0 {color}, stop:1 #be123c)"
            border_color = '#09090b'
            border_w = '1px'
            text_color = '#ffffff'
            hover_css = ""
        else:
            color = SEAT_AVAILABLE
            bg = f"qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, stop:0 #334155, stop:1 {color})"
            border_color = '#1e293b'
            border_w = '1px'
            text_color = '#f8fafc'

        shadow = "box-shadow: 0px 0px 8px rgba(0, 0, 0, 0.5);" if self.seat_state != "D" else ""

        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: {border_w} solid {border_color};
                border-radius: 6px;
                color: {text_color};
                font-weight: 800;
                font-size: 11px;
                padding: 0;
                margin: 1px;
                {shadow}
            }}
            {hover_css}
        """)
        
        if self.selected:
            label = "[X]"
        elif self.seat_state in ("S", "R"):
            label = "Res"
        elif self.seat_state == "V":
            label = "Vend"
        else:
            label = f"{self.seat_row}-{self.seat_col}"
        self.setText(label)

    def toggle_select(self):
        if self.seat_state == "V":
            self.error_clicked.emit("Este asiento ya fue vendido.")
            self._shake()
            return
        elif self.seat_state in ("S", "R") and not self.selected:
            self.error_clicked.emit("Este asiento ya está reservado por alguien más.")
            self._shake()
            return

        self.selected = not self.selected
        self._apply_style()

    def _shake(self):
        orig = self.pos()
        for i, dx in enumerate([4, -4, 2, -2, 0]):
            QTimer.singleShot(i * 30, lambda d=dx, o=orig: self.move(o.x() + d, o.y()))


class StadiumSelectorWidget(QFrame):
    zone_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_zone = 0
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(340)
        self.setStyleSheet(f"""
            .QFrame {{
                background: {BG_PANEL};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)

        self.subtitle = QLabel("Toca una zona para seleccionarla")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setStyleSheet(f"color: {TEXT_SEC}; font-size: 14px; letter-spacing: 0.2px;")
        layout.addWidget(self.subtitle)

        arena = QFrame()
        arena.setStyleSheet("border: none; background: transparent;")
        arena_layout = QGridLayout(arena)
        arena_layout.setContentsMargins(10, 8, 10, 8)
        arena_layout.setSpacing(10)
        arena_layout.setRowMinimumHeight(1, 80)
        arena_layout.setRowMinimumHeight(2, 0)
        arena_layout.setRowMinimumHeight(3, 80)
        arena_layout.setRowStretch(0, 0)
        arena_layout.setRowStretch(1, 3)
        arena_layout.setRowStretch(2, 3)
        arena_layout.setRowStretch(3, 3)

        stage_label = QLabel("ESCENARIO PRINCIPAL")
        stage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stage_label.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: 800; font-size: 16px; letter-spacing: 4px; background: {BG_DEEP}; border-radius: 12px; padding: 12px;")
        arena_layout.addWidget(stage_label, 0, 1, 1, 2)

        self.zone_buttons = {}
        zone_specs = [
            (0, "VIP\nFrente", 1, 1, 1, 2),
            (1, "Pref Norte\nLateral", 1, 0, 2, 1),
            (2, "Pref Sur\nLateral", 1, 3, 2, 1),
            (3, "Gen Oeste\nPerimetral", 3, 0, 1, 2),
            (4, "Gen Este\nPerimetral", 3, 2, 1, 2),
        ]

        for zone_id, label, row, col, rowspan, colspan in zone_specs:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.setMinimumHeight(80)
            btn.clicked.connect(lambda _, z=zone_id: self._select_zone(z))
            self.zone_buttons[zone_id] = btn
            
            color = ZONE_COLORS[zone_id]
            color_stop = '#' + ''.join([f"{max(0, int(c, 16) - 5):02x}" for c in (color[1:3], color[3:5], color[5:7])])
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color}, stop:1 {color_stop});
                    border: 1px solid rgba(255,255,255,0.1);
                    color: #ffffff;
                    border-radius: 14px;
                    font-size: 15px;
                    font-weight: 800;
                    padding: 10px;
                    box-shadow: inset 0px 2px 5px rgba(255,255,255,0.2);
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color_stop}, stop:1 {color});
                }}
                QPushButton:checked {{
                    border: 3px solid #ffffff;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color}, stop:1 {color});
                }}
            """)
            arena_layout.addWidget(btn, row, col, rowspan, colspan)

        layout.addWidget(arena, 1)
        self.set_selected_zone(0)

    def set_selected_zone(self, zone_id):
        self.selected_zone = zone_id
        self._sync_styles()
        self.update()

    def _select_zone(self, zone_id):
        self.set_selected_zone(zone_id)
        self.zone_selected.emit(zone_id)

    def _sync_styles(self):
        for zone_id, btn in self.zone_buttons.items():
            active = zone_id == self.selected_zone
            btn.setChecked(active)



# ── Panel de mapa de asientos ───────────────────────────────────────────────
class SeatMapPanel(QWidget):
    selection_changed = pyqtSignal(object)
    seat_select_error = pyqtSignal(str)   # emitida cuando falla la selección
    seat_auto_reserved = pyqtSignal(str, object)  # (tx_id, key) reserva automática OK
    seat_cancel_request = pyqtSignal(str, object) # NUEVO: (tx_id, key) solicitud de cancelación rápida
    _internal_seat_reserved = pyqtSignal(dict, object, object)
    _internal_seat_error = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._internal_seat_reserved.connect(self._on_seat_auto_reserved)
        self._internal_seat_error.connect(self._on_seat_select_error)
        
        self.zone_id      = 0
        self.seat_buttons = {}
        self.local_cart   = set()  # (zone_id, r, c) pre-seleccionados en ESTE cliente
        self.owned_seats  = {}     # (zone_id, r, c) -> tx_id reservados formalmente
        
        # Timer para actualización dinámica (Polling)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(50)
        self.poll_timer.timeout.connect(self._poll_zone)
        
        self._poll_running = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Mapa de asientos")
        title.setStyleSheet(f"font-size: 15px; color: {TEXT_PRI}; font-weight: 600;")
        self.zone_label = QLabel("Zona VIP")
        self.zone_label.setStyleSheet(f"""
            background: {ZONE_COLORS[0]}33;
            border: 1px solid {ZONE_COLORS[0]}aa;
            border-radius: 10px;
            color: {TEXT_PRI};
            padding: 3px 10px;
            font-size: 13px;
            font-weight: 700;
        """)
        header.addWidget(title)
        header.addWidget(self.zone_label)
        
        header.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Policy.Expanding))
        layout.addLayout(header)

        legend = QHBoxLayout()
        legend_items = [
            (SEAT_AVAILABLE, "Disponible"),
            (SEAT_SELECTED,  "Mi selección/Reserva"),
            (SEAT_RESERVED,  "Reservado por otro"),
            (SEAT_SOLD,      "Vendido"),
        ]
        for color, label in legend_items:
            swatch = QLabel("  ")
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(f"background: {color}; border: 1px solid {BORDER}; border-radius: 6px;")
            text = QLabel(label)
            text.setStyleSheet(f"color: {TEXT_SEC}; font-size: 14px; margin-right: 14px;")
            legend.addWidget(swatch)
            legend.addWidget(text)
        legend.addStretch()
        layout.addLayout(legend)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.scroll = scroll

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setHorizontalSpacing(8)
        self.grid_layout.setVerticalSpacing(8)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        self.grid_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll, 1)

        self.lbl_selected = QLabel("Ningún asiento seleccionado")
        self.lbl_selected.setStyleSheet(f"color: {TEXT_SEC}; font-size: 14px;")
        layout.addWidget(self.lbl_selected)

    def set_zone(self, zone_id, auto_load=True):
        self.zone_id = zone_id
        self.selected = []
        zone_color = ZONE_COLORS.get(zone_id, ACCENT)
        self.zone_label.setText(f"Zona {ZONE_NAMES.get(zone_id, zone_id)}")
        self.zone_label.setStyleSheet(f"""
            background: {zone_color}33;
            border: 1px solid {zone_color}aa;
            border-radius: 10px;
            color: {TEXT_PRI};
            padding: 3px 10px;
            font-size: 13px;
            font-weight: 700;
        """)
        self._update_selection_label()
        
        self.poll_timer.stop()
        if auto_load:
            self.load_zone(full_rebuild=True)
            self.poll_timer.start(100)

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _poll_zone(self):
        if self._poll_running:
            return
        self.load_zone(full_rebuild=False)

    def load_zone(self, full_rebuild=True):
        self._poll_running = True
        worker = NetworkWorker(check, self.zone_id, SESSION_ID)
        worker.result.connect(lambda resp, fb=full_rebuild: self._on_loaded(resp, fb))
        worker.error.connect(self._on_load_error)
        worker.start()

    def _on_loaded(self, resp, is_full_rebuild=True):
        self._poll_running = False
        if not resp["ok"]:
            return
        matrix = resp["state"]

        # Sincronizar owned_seats desde servidor SOLO en rebuild completo (cambio de zona)
        # En polls periódicos (cada 300ms), jamás limpiar para no destruir reservas recién hechas
        if is_full_rebuild and "my_reservations" in resp:
            self.owned_seats.clear()
            for tx, seats in resp["my_reservations"].items():
                for item in seats:
                    z, r, c = item[0], item[1], item[2]
                    self.owned_seats[(z, r, c)] = tx

        # Sincronizar holds (asientos SELECTED míos) — sobreviven a reinicios y re-login
        # Se agregan a owned_seats con tx="HOLD" y a local_cart para que aparezcan naranja (míos)
        if is_full_rebuild and "my_holds" in resp:
            for item in resp["my_holds"]:
                z, r, c = item[0], item[1], item[2]
                key = (z, r, c)
                if key not in self.owned_seats:
                    self.owned_seats[key] = "HOLD"
                if key not in self.local_cart:
                    self.local_cart.add(key)
        
        if not is_full_rebuild:
            if matrix:
                self.update_matrix(matrix)
            return
            
        self._clear_grid()
        self.seat_buttons.clear()

        if not matrix:
            self._update_selection_label()
            return

        cols = len(matrix[0])
        for c in range(cols):
            clbl = QLabel(f"C{c}")
            clbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
            clbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            self.grid_layout.addWidget(clbl, 0, c + 1)

        for r, row in enumerate(matrix):
            lbl = QLabel(f"F{r}")
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.grid_layout.addWidget(lbl, r + 1, 0)
            for c, state in enumerate(row):
                btn = SeatButton(r, c, state)
                key = (self.zone_id, r, c)
                if key in self.local_cart or key in self.owned_seats:
                    btn.selected = True
                    btn._apply_style()
                btn.clicked.connect(lambda _, b=btn: self._toggle_seat(b))
                btn.error_clicked.connect(self.seat_select_error.emit)
                self.seat_buttons[(r, c)] = btn
                self.grid_layout.addWidget(btn, r + 1, c + 1)

        # Ensure the matrix is shown from the top-left corner after every reload.
        self.scroll.horizontalScrollBar().setValue(0)
        self.scroll.verticalScrollBar().setValue(0)

        self._update_selection_label()


    def _on_load_error(self, msg):
        self._poll_running = False

    def _on_error(self, msg):
        pass

    def _toggle_seat(self, btn):
        r, c = btn.seat_row, btn.seat_col
        key  = (self.zone_id, r, c)

        # Si ya lo tenemos reservado formalmente, permitimos cancelar (deseleccionar)
        if key in self.owned_seats:
            tx_id = self.owned_seats[key]
            if tx_id == "HOLD":
                # Era un hold recuperado de sesión anterior — lo deseleccionamos
                self.owned_seats.pop(key, None)
                self.local_cart.discard(key)
                btn.selected = False
                btn._apply_style()
                self._update_selection_label()
                self.selection_changed.emit((self.local_cart, self.owned_seats))
                worker = NetworkWorker(deselect_seat, self.zone_id, r, c, SESSION_ID)
                worker.error.connect(lambda e: self.seat_select_error.emit(e))
                worker.start()
            else:
                self.seat_cancel_request.emit(tx_id, key)
            return

        if key in self.local_cart:
            # --- DESELECCIONAR: notificar al servidor ---
            self.local_cart.discard(key)
            btn.selected = False
            btn._apply_style()
            worker = NetworkWorker(deselect_seat, self.zone_id, r, c, SESSION_ID)
            worker.error.connect(lambda e: self.seat_select_error.emit(e))
            worker.start()
            self._update_selection_label()
            self.selection_changed.emit((self.local_cart, self.owned_seats))
        else:
            if btn.seat_state == "S":
                self.seat_select_error.emit(
                    f"El asiento F{r}C{c} ya está siendo seleccionado por otro usuario. "
                    f"Por favor elige otro asiento."
                )
                return
            elif btn.seat_state == "R":
                self.seat_select_error.emit(f"El asiento F{r}C{c} está reservado por otro usuario.")
                return
            elif btn.seat_state == "V":
                self.seat_select_error.emit(f"El asiento F{r}C{c} ya fue vendido.")
                return
            elif btn.seat_state != "D":
                return

            # ── RESERVA INMEDIATA: select + reserve en un solo paso ──────────
            # Marcar optimistamente como seleccionado
            self.local_cart.add(key)
            btn.selected = True
            btn._apply_style()
            self._update_selection_label()
            self.selection_changed.emit((self.local_cart, self.owned_seats))

            # Primero hacer select en el servidor, luego reserve automáticamente
            worker = NetworkWorker(select_seat, self.zone_id, r, c, SESSION_ID)
            worker.result.connect(lambda resp, b=btn, k=key, zid=self.zone_id, ro=r, co=c:
                self._on_select_then_reserve(resp, b, k, zid, ro, co))
            worker.error.connect(lambda e, b=btn, k=key: self._on_select_network_error(e, b, k))
            worker.start()

    def _on_select_then_reserve(self, resp, btn, key, zone_id, row, col):
        """Callback: si el select fue OK, lanza reserve inmediatamente."""
        if not resp["ok"]:
            # Selección rechazada — revertir
            self.local_cart.discard(key)
            btn.selected = False
            btn._apply_style()
            self._update_selection_label()
            self.selection_changed.emit((self.local_cart, self.owned_seats))
            self.seat_select_error.emit(resp.get("error", "No se pudo seleccionar el asiento"))
            return
        # Select OK → reservar inmediatamente
        worker = NetworkWorker(reserve, zone_id, row, col, SESSION_ID)
        worker.result.connect(lambda r, b=btn, k=key: self._on_auto_reserve_result(r, b, k))
        worker.error.connect(lambda e, b=btn, k=key: self._on_select_network_error(e, b, k))
        worker.start()

    def _on_auto_reserve_result(self, resp, btn, key):
        """Procesa el resultado de la reserva automática tras el clic."""
        if resp["ok"]:
            tx_id = resp["tx_id"]
            self.local_cart.discard(key)
            self.owned_seats[key] = tx_id
            btn.selected = True  # mantener naranja — el asiento es nuestro
            btn.seat_state = "R"
            btn._apply_style()
            self._update_selection_label()
            self.selection_changed.emit((self.local_cart, self.owned_seats))
            self.seat_auto_reserved.emit(tx_id, key)
        else:
            # La reserva falló — revertir
            self.local_cart.discard(key)
            btn.selected = False
            btn._apply_style()
            self._update_selection_label()
            self.selection_changed.emit((self.local_cart, self.owned_seats))
            self.seat_select_error.emit(resp.get("error", "No se pudo reservar el asiento"))

    def _on_select_result(self, resp, btn, key):
        if not resp["ok"]:
            self.local_cart.discard(key)
            btn.selected = False
            btn._apply_style()
            self._update_selection_label()
            self.selection_changed.emit((self.local_cart, self.owned_seats))
            self.seat_select_error.emit(resp.get("error", "No se pudo seleccionar el asiento"))

    def _on_select_network_error(self, e, btn, key):
        self.local_cart.discard(key)
        btn.selected = False
        btn._apply_style()
        self._update_selection_label()
        self.selection_changed.emit((self.local_cart, self.owned_seats))
        self.seat_select_error.emit(str(e))

    def _on_seat_auto_reserved(self, resp, key, btn):
        pass  # Not used

    def _on_seat_select_error(self, msg, btn):
        """Cuando falla la selección, revierte el botón a su estado anterior."""
        key = (self.zone_id, btn.seat_row, btn.seat_col)
        self.local_cart.discard(key)
        btn.selected = False
        btn._apply_style()
        self.selection_changed.emit((self.local_cart, self.owned_seats))

    def _cancel_seat_async(self, tx_id):
        pass  # Handled by ReserveTab now

    def reset(self):
        """Detiene timers y limpia estado local para el logout sin reiniciar el proceso."""
        self.poll_timer.stop()
        self._poll_running = False
        self.owned_seats.clear()
        self.local_cart.clear()
        self.seat_buttons.clear()
        self._clear_grid()
        self._update_selection_label()

    def _update_selection_label(self):
        if not self.local_cart and not self.owned_seats:
            self.lbl_selected.setText("Ningún asiento seleccionado")
        else:
            txt = []
            if self.local_cart:
                txt.append(f"{len(self.local_cart)} seleccionados")
            if self.owned_seats:
                txt.append(f"{len(self.owned_seats)} reservados")
            self.lbl_selected.setText(" | ".join(txt))

    def update_matrix(self, matrix):
        for r, row in enumerate(matrix):
            for c, state in enumerate(row):
                btn = self.seat_buttons.get((r, c))
                if btn:
                    key = (self.zone_id, r, c)
                    if key in self.owned_seats:
                        # Reservado formalmente por nosotros: mostrar naranja "R"
                        if not btn.selected:
                            btn.selected = True
                            btn.seat_state = "R"
                            btn._apply_style()
                    elif key in self.local_cart:
                        # En carrito local (pendiente de reserva): mantener verde
                        if not btn.selected:
                            btn.selected = True
                            btn._apply_style()
                    else:
                        # Asiento de otro: mostrar estado real del servidor
                        btn.selected = False
                        btn.sync_state(state)
                            
        self._update_selection_label()
        self.selection_changed.emit((self.local_cart, self.owned_seats))

    def get_selection(self):
        return self.zone_id, list(self.owned_seats.items())


# ── Tarjeta de estadística ──────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, label, value="—", color=TEXT_PRI, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setMinimumWidth(100)
        self.setMinimumHeight(105)
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 12px;
                padding: 4px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setObjectName("stat_value")
        self.value_lbl.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {color};")
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_lbl = QLabel(label.upper())
        self.label_lbl.setObjectName("stat_label")
        self.label_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_lbl.setWordWrap(False)

        layout.addWidget(self.value_lbl)
        layout.addWidget(self.label_lbl)

    def update_value(self, value, color=None):
        self.value_lbl.setText(str(value))
        if color:
            self.value_lbl.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {color};")


# ── Tab: Mapa de asientos + reserva ────────────────────────────────────────
class ReserveTab(QWidget):
    log_signal       = pyqtSignal(str)
    summary_updated  = pyqtSignal(str, str)   # (texto, color_hex)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_zone = 0
        self.countdown_seconds = 0
        self._prev_cart_size = 0   # para detectar cuando el usuario agrega un asiento
        self.purchase = PurchaseController(self)
        self.purchase.reserve_result.connect(self._on_reserve_result)
        self.purchase.tx_result.connect(self._on_tx_result)
        self.purchase.error.connect(self._on_error)
        
        # Timer local que decrementa el countdown cada segundo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_countdown)
        self.timer.start(1000)

        # Al iniciar, consultar al servidor si la sesión tiene un TTL activo
        # (caso: el usuario reabre la app antes de que expirar)
        self._sync_ttl_from_server()
        
        self._build_ui()

    def _sync_ttl_from_server(self):
        """Consulta al servidor el TTL de sesión actual y sincroniza el countdown.
        Se llama al iniciar la app (para reanudar un countdown pendiente)."""
        worker = NetworkWorker(get_ttl, SESSION_ID)
        worker.result.connect(self._on_ttl_synced)
        worker.error.connect(lambda _: None)  # Silencioso si el servidor no está
        worker.start()
        self._ttl_sync_worker = worker

    def _on_ttl_synced(self, resp):
        """Recibe el TTL del servidor y actualiza el countdown si hay tiempo restante."""
        import math
        if resp.get("ok"):
            remaining = math.ceil(float(resp.get("remaining", 0)))
            if remaining > 0 and self.countdown_seconds == 0:
                self.countdown_seconds = remaining
                self._log(f"Sesión retomada — {remaining}s restantes")

    def _update_countdown(self):
        if self.countdown_seconds > 0:
            self.countdown_seconds -= 1
            mins = self.countdown_seconds // 60
            secs = self.countdown_seconds % 60
            self.lbl_countdown.setText(f"{mins:02d}:{secs:02d}")
            if self.countdown_seconds <= 10:
                self.lbl_countdown.setStyleSheet(f"color: {RED}; font-size: 24px; font-weight: 800; text-align: center;")
            else:
                self.lbl_countdown.setStyleSheet(f"color: {ACCENT2}; font-size: 24px; font-weight: 800; text-align: center;")
            # Refrescar el strip del header con TTL actualizado
            owned = self.seat_map.owned_seats
            if owned:
                total_p = sum(ZONE_PRICES.get(z, 0) for (z, r, c) in owned)
                n_s = len(owned)
                n_z = len(set(z for (z, r, c) in owned))
                color = RED if self.countdown_seconds <= 10 else TEXT_SEC
                parts = [f"₡ {total_p:,.0f}", f"{n_s} asiento{'s' if n_s != 1 else ''}"]
                if n_z > 1:
                    parts.append(f"{n_z} zonas")
                parts.append(f"⏱ {self.countdown_seconds}s")
                self.summary_updated.emit("  ·  ".join(parts), color)
            
            if self.countdown_seconds == 0:
                self.lbl_countdown.setText("Tiempo expirado")
                for key in list(self.seat_map.owned_seats.keys()):
                    z, r, c = key
                    if z == self.seat_map.zone_id:
                        btn = self.seat_map.seat_buttons.get((r, c))
                        if btn:
                            btn.selected = False
                            btn.sync_state("D")
                            btn._apply_style()
                self.seat_map.owned_seats.clear()
                self.tx_input.clear()
                self.seat_map.selection_changed.emit((self.seat_map.local_cart, self.seat_map.owned_seats))
        else:
            if "expirado" not in self.lbl_countdown.text():
                self.lbl_countdown.setText("")

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        self.flow_stack = QStackedWidget()
        main.addWidget(self.flow_stack, 1)

        self._build_zone_step_page()
        self._build_purchase_step_page()
        self.flow_stack.setCurrentIndex(0)

    def _build_zone_step_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        title = QLabel("Paso 1: Seleccione la zona")
        title.setObjectName("heading")
        sub = QLabel("Elige una zona del estadio para cargar su matriz de asientos")
        sub.setObjectName("subheading")
        layout.addWidget(title)
        layout.addWidget(sub)

        stadium_card = QFrame()
        stadium_card.setStyleSheet(f"""
            .QFrame {{
                background: {BG_PANEL};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
        """)
        stadium_layout = QVBoxLayout(stadium_card)
        stadium_layout.setContentsMargins(12, 12, 12, 12)
        stadium_layout.setSpacing(10)

        self.stadium_selector = StadiumSelectorWidget()
        self.stadium_selector.zone_selected.connect(self._on_zone_selected)
        stadium_layout.addWidget(self.stadium_selector)

        self.zone_hint = QLabel("Toca una zona para abrir su matriz")
        self.zone_hint.setStyleSheet(f"color: {TEXT_SEC}; font-size: 14px;")
        self.zone_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stadium_layout.addWidget(self.zone_hint)

        layout.addWidget(stadium_card, 1)

        self.flow_stack.addWidget(page)

    def _build_purchase_step_page(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(12)

        header = QHBoxLayout()
        self.btn_back_to_zones = QPushButton("Volver a zonas")
        self.btn_back_to_zones.setObjectName("secondary")
        self.btn_back_to_zones.setFixedWidth(150)
        self.btn_back_to_zones.clicked.connect(self._back_to_zone_selection)

        self.lbl_step_zone = QLabel("Paso 2: Matriz de Zona VIP")
        self.lbl_step_zone.setObjectName("subheading")
        self.lbl_step_zone.setStyleSheet(f"font-size: 14px; color: {TEXT_PRI};")

        header.addWidget(self.btn_back_to_zones)
        header.addWidget(self.lbl_step_zone)
        header.addStretch()
        page_layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: seat map
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.seat_map = SeatMapPanel()
        self.seat_map.set_zone(self.selected_zone, auto_load=False)
        self.seat_map.selection_changed.connect(self._on_selection_changed)
        # Mostrar errores de selección en la bitácora local
        self.seat_map.seat_select_error.connect(self._on_seat_error)
        left_layout.addWidget(self.seat_map, 1)
        # Conectar reserva automática y cancelación rápida
        self.seat_map.seat_auto_reserved.connect(self._on_seat_auto_reserved)
        self.seat_map.seat_cancel_request.connect(self._on_seat_cancel_request)

        splitter.addWidget(left)

        # Right: action panel inside a ScrollArea to prevent squashing
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setMinimumWidth(380)
        right_scroll.setMaximumWidth(450)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(0, 0, 16, 0) # Añadir un poco de margen derecho para el scrollbar
        right_layout.setSpacing(12)

        grp_reserve = QFrame()
        grp_reserve.setStyleSheet(f".QFrame {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}")
        grp_layout  = QVBoxLayout(grp_reserve)
        grp_layout.setSpacing(10)
        grp_layout.setContentsMargins(16, 14, 16, 14)

        # Header row
        hdr_row = QHBoxLayout()
        res_title = QLabel("\U0001f9fe  Desglose de compra")
        res_title.setStyleSheet(f"color: {ACCENT2}; font-size: 14px; font-weight: 800; border: none;")
        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_countdown.setStyleSheet("border: none;")
        hdr_row.addWidget(res_title)
        hdr_row.addStretch()
        hdr_row.addWidget(self.lbl_countdown)
        grp_layout.addLayout(hdr_row)

        reserve_note = QLabel("Haz clic en asientos disponibles para reservarlos. Tienes 60s para confirmar.")
        reserve_note.setWordWrap(True)
        reserve_note.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; border: none;")
        grp_layout.addWidget(reserve_note)

        # Breakdown scroll area
        breakdown_scroll = QScrollArea()
        breakdown_scroll.setWidgetResizable(True)
        breakdown_scroll.setFrameShape(QFrame.Shape.NoFrame)
        breakdown_scroll.setMinimumHeight(120)
        breakdown_scroll.setMaximumHeight(250)
        breakdown_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        breakdown_scroll.setStyleSheet(f"background: transparent; border: none;")

        self._breakdown_widget = QWidget()
        self._breakdown_widget.setStyleSheet("background: transparent;")
        self._breakdown_layout = QVBoxLayout(self._breakdown_widget)
        self._breakdown_layout.setContentsMargins(0, 0, 0, 0)
        self._breakdown_layout.setSpacing(4)

        initial_lbl = QLabel("Sin asientos seleccionados")
        initial_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px; border: none; padding: 8px 0;")
        initial_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._breakdown_layout.addWidget(initial_lbl)
        breakdown_scroll.setWidget(self._breakdown_widget)
        grp_layout.addWidget(breakdown_scroll)

        # Total row
        total_sep = QFrame()
        total_sep.setFrameShape(QFrame.Shape.HLine)
        total_sep.setStyleSheet(f"border: none; border-top: 1px solid {BORDER}; margin: 2px 0;")
        grp_layout.addWidget(total_sep)

        total_row = QHBoxLayout()
        total_lbl = QLabel("TOTAL")
        total_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; font-weight: 800; border: none; letter-spacing: 1px;")
        self.lbl_total = QLabel("\u20a2 0")
        self.lbl_total.setStyleSheet(f"color: {GREEN}; font-size: 16px; font-weight: 800; border: none;")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        total_row.addWidget(total_lbl)
        total_row.addStretch()
        total_row.addWidget(self.lbl_total)
        grp_layout.addLayout(total_row)

        right_layout.addWidget(grp_reserve)

        grp_tx = QFrame()
        grp_tx.setStyleSheet(f".QFrame {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}")
        grp_tx_layout = QVBoxLayout(grp_tx)
        grp_tx_layout.setSpacing(12)
        grp_tx_layout.setContentsMargins(16, 16, 16, 16)

        tx_title = QLabel("Paso 4: Gestionar reserva")
        tx_title.setStyleSheet(f"color: {ACCENT2}; font-size: 15px; font-weight: 800; border: none;")
        grp_tx_layout.addWidget(tx_title)

        tx_note = QLabel("Usa el ID de transacción para confirmar la compra o cancelar la reserva.")
        tx_note.setWordWrap(True)
        tx_note.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; border: none;")
        tx_note.setMinimumHeight(45)
        tx_note.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        lbl_tx = QLabel("ID de transacción:")
        lbl_tx.setStyleSheet(f"color: {TEXT_SEC}; font-size: 14px; border: none;")
        self.tx_input = QLineEdit()
        self.tx_input.setPlaceholderText("Ej: A1B2C3D4")
        self.tx_input.setMinimumHeight(38)

        _btn_disabled_style = f"""
            QPushButton {{ background: #27272a; color: #52525b; border: 1px solid #3f3f46;
                           border-radius: 6px; font-size: 14px; font-weight: 800; }}
            QPushButton:hover {{ background: #27272a; color: #52525b; }}
        """
        self.btn_confirm = QPushButton("Confirmar compra")
        self.btn_confirm.setMinimumHeight(40)
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.setStyleSheet(_btn_disabled_style)
        self.btn_confirm.clicked.connect(self._do_confirm)

        self.btn_cancel = QPushButton("Cancelar reserva")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet(_btn_disabled_style)
        self.btn_cancel.clicked.connect(self._do_cancel)

        grp_tx_layout.addWidget(tx_note)
        grp_tx_layout.addWidget(lbl_tx)
        grp_tx_layout.addWidget(self.tx_input)
        grp_tx_layout.addSpacing(6)
        grp_tx_layout.addWidget(self.btn_confirm)
        grp_tx_layout.addSpacing(4)
        grp_tx_layout.addWidget(self.btn_cancel)
        right_layout.addWidget(grp_tx)
        right_layout.addStretch()

        right_scroll.setWidget(right_content)
        splitter.addWidget(right_scroll)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([850, 400])
        page_layout.addWidget(splitter, 1)

        self.flow_stack.addWidget(page)

    def _on_zone_selected(self, zone_id):
        self.selected_zone = zone_id
        self.zone_hint.setText(f"Zona seleccionada: {ZONE_NAMES.get(zone_id, zone_id)}")
        self.stadium_selector.set_selected_zone(zone_id)
        self._open_selected_zone(zone_id)

    def _open_selected_zone(self, zone_id=None):
        if zone_id is not None:
            self.selected_zone = zone_id
        self.seat_map.set_zone(self.selected_zone)
        self.lbl_step_zone.setText(f"Paso 2: Matriz de Zona {ZONE_NAMES.get(self.selected_zone, self.selected_zone)}")
        self.stadium_selector.set_selected_zone(self.selected_zone)
        self.flow_stack.setCurrentIndex(1)

    def _back_to_zone_selection(self):
        self.flow_stack.setCurrentIndex(0)
        self._refresh_selection_panel()

    def _on_seat_auto_reserved(self, tx_id, key):
        """Se llama cuando SeatMapPanel hace una reserva automática al clic."""
        # Sincronizar countdown con TTL real del servidor
        worker = NetworkWorker(get_ttl, SESSION_ID)
        worker.result.connect(self._apply_server_ttl)
        worker.error.connect(lambda _: None)
        worker.start()
        self._log(f"Reserva automática — TX: {tx_id}")
        self._log("Tienes 60 segundos para confirmar")
        self._refresh_selection_panel()

    def _on_selection_changed(self, selection):
        local_cart, owned_seats = selection
        cart_size = len(local_cart)

        self._refresh_selection_panel()

        if not local_cart and not owned_seats:
            self.countdown_seconds = 0
            self.lbl_countdown.setText("")
            self._prev_cart_size = 0
        else:

            if owned_seats:
                # Si hay reserva formal y el countdown llegó a 0, sincronizar
                if self.countdown_seconds == 0:
                    worker = NetworkWorker(get_ttl, SESSION_ID)
                    worker.result.connect(self._apply_server_ttl)
                    worker.error.connect(lambda _: None)
                    worker.start()

    def _refresh_selection_panel(self):
        """Construye el desglose visual de asientos por zona con precios en colones."""
        owned_seats = self.seat_map.owned_seats
        local_cart  = self.seat_map.local_cart

        # Limpiar el layout de desglose
        while self._breakdown_layout.count():
            item = self._breakdown_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_price = 0
        has_items = False

        by_zone = {}
        for (z, r, c), tx in owned_seats.items():
            by_zone.setdefault(z, []).append((r, c))

        for z_id in sorted(by_zone):
            seats_here = by_zone[z_id]
            price_unit = ZONE_PRICES.get(z_id, 0)
            subtotal   = price_unit * len(seats_here)
            total_price += subtotal
            zone_color  = ZONE_COLORS.get(z_id, ACCENT2)
            has_items = True

            zone_hdr = QFrame()
            zone_hdr.setStyleSheet(
                f"background: {zone_color}22; border-radius: 6px; border: 1px solid {zone_color}55;"
            )
            zone_hdr_lay = QHBoxLayout(zone_hdr)
            zone_hdr_lay.setContentsMargins(8, 5, 8, 5)
            lbl_zname = QLabel(f"  {ZONE_NAMES.get(z_id, z_id)}")
            lbl_zname.setStyleSheet(f"color: {zone_color}; font-size: 12px; font-weight: 800; border: none;")
            lbl_zprice = QLabel(f"₡ {price_unit:,.0f} c/u")
            lbl_zprice.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
            zone_hdr_lay.addWidget(lbl_zname)
            zone_hdr_lay.addStretch()
            zone_hdr_lay.addWidget(lbl_zprice)
            self._breakdown_layout.addWidget(zone_hdr)

            for r, c in sorted(seats_here):
                seat_row = QHBoxLayout()
                seat_row.setContentsMargins(6, 1, 6, 1)
                lbl_seat = QLabel(f"    Fila {r}  ·  Col {c}")
                lbl_seat.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; border: none;")
                lbl_seat_price = QLabel(f"₡ {price_unit:,.0f}")
                lbl_seat_price.setStyleSheet(f"color: {TEXT_PRI}; font-size: 12px; font-weight: 600; border: none;")
                lbl_seat_price.setAlignment(Qt.AlignmentFlag.AlignRight)
                seat_row.addWidget(lbl_seat)
                seat_row.addStretch()
                seat_row.addWidget(lbl_seat_price)
                seat_w = QWidget()
                seat_w.setStyleSheet("background: transparent;")
                seat_w.setLayout(seat_row)
                self._breakdown_layout.addWidget(seat_w)

            sub_row = QHBoxLayout()
            sub_row.setContentsMargins(6, 2, 6, 4)
            lbl_sub_l = QLabel(f"    {len(seats_here)} asiento(s)")
            lbl_sub_l.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
            lbl_sub_r = QLabel(f"₡ {subtotal:,.0f}")
            lbl_sub_r.setStyleSheet(f"color: {zone_color}; font-size: 12px; font-weight: 700; border: none;")
            lbl_sub_r.setAlignment(Qt.AlignmentFlag.AlignRight)
            sub_row.addWidget(lbl_sub_l)
            sub_row.addStretch()
            sub_row.addWidget(lbl_sub_r)
            sub_w = QWidget()
            sub_w.setStyleSheet("background: transparent;")
            sub_w.setLayout(sub_row)
            self._breakdown_layout.addWidget(sub_w)

        if local_cart:
            cart_lbl = QLabel(f"  + {len(local_cart)} en proceso...")
            cart_lbl.setStyleSheet(f"color: {YELLOW}; font-size: 12px; font-style: italic; border: none;")
            self._breakdown_layout.addWidget(cart_lbl)
            has_items = True

        if not has_items:
            empty = QLabel("Sin asientos seleccionados")
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px; border: none; padding: 8px 0;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._breakdown_layout.addWidget(empty)
            self.lbl_total.setText("₡ 0")
        else:
            self.lbl_total.setText(f"₡ {total_price:,.0f}")

        self._breakdown_layout.addStretch()

        if owned_seats:
            tx_ids = ", ".join(sorted(set(owned_seats.values())))
            self.tx_input.setText(tx_ids)
        else:
            self.tx_input.clear()

        # Señal al strip del header
        if owned_seats:
            n_seats = len(owned_seats)
            n_zones = len(set(z for (z, r, c) in owned_seats))
            parts = [f"₡ {total_price:,.0f}", f"{n_seats} asiento{'s' if n_seats != 1 else ''}"]
            if n_zones > 1:
                parts.append(f"{n_zones} zonas")
            if self.countdown_seconds > 0:
                parts.append(f"⏱ {self.countdown_seconds}s")
            self.summary_updated.emit("  ·  ".join(parts), TEXT_SEC)
        else:
            self.summary_updated.emit("", TEXT_MUTED)

        # Habilitar/deshabilitar botones de acción según si hay reservas
        has_reserved = bool(owned_seats)
        self.btn_confirm.setEnabled(has_reserved)
        self.btn_cancel.setEnabled(has_reserved)
        if has_reserved:
            self.btn_confirm.setStyleSheet(f"""
                QPushButton {{ background: {GREEN}; color: #000000; border: none; border-radius: 6px; font-size: 14px; font-weight: 800; }}
                QPushButton:hover {{ background: #34d399; }}
                QPushButton:pressed {{ background: #059669; }}
            """)
            self.btn_cancel.setStyleSheet(f"""
                QPushButton {{ background: {RED}; color: #ffffff; border: none; border-radius: 6px; font-size: 14px; font-weight: 800; }}
                QPushButton:hover {{ background: #f87171; }}
                QPushButton:pressed {{ background: #dc2626; }}
            """)
        else:
            disabled_style = f"""
                QPushButton {{ background: #27272a; color: #52525b; border: 1px solid #3f3f46;
                               border-radius: 6px; font-size: 14px; font-weight: 800; }}
                QPushButton:hover {{ background: #27272a; color: #52525b; }}
            """
            self.btn_confirm.setStyleSheet(disabled_style)
            self.btn_cancel.setStyleSheet(disabled_style)

    def _apply_server_ttl(self, resp):
        """Aplica el TTL recibido del servidor al countdown local.
        Siempre refleja el tiempo REAL que queda en el servidor."""
        import math
        if resp.get("ok"):
            remaining = math.ceil(float(resp.get("remaining", 60)))
            # Mínimo 1s para evitar flash de 'expirado' inmediato
            self.countdown_seconds = max(remaining, 1)

    def _on_reserve_result(self, resp):
        """Callback del PurchaseController (reserva múltiple manual, si se usa)."""
        if resp["ok"]:
            tx_id = resp["tx_id"]
            for key in list(self.seat_map.local_cart):
                self.seat_map.owned_seats[key] = tx_id
            self.seat_map.local_cart.clear()
            self.tx_input.setText(tx_id)
            worker = NetworkWorker(get_ttl, SESSION_ID)
            worker.result.connect(self._apply_server_ttl)
            worker.error.connect(lambda _: None)
            worker.start()
            self._log(f"Reserva exitosa — TX: {tx_id}")
            self._log("Tienes 60 segundos para confirmar")
            self.seat_map.selection_changed.emit((self.seat_map.local_cart, self.seat_map.owned_seats))
        else:
            self._log(f"Error: {resp.get('error', 'Desconocido')}")

    def _do_confirm(self):
        tx_text = self.tx_input.text().strip()
        txs_to_confirm = set()
        
        if tx_text:
            for tx in tx_text.split(","):
                tx = tx.strip()
                if tx:
                    txs_to_confirm.add(tx)
                    
        if self.seat_map.owned_seats:
            for tx in self.seat_map.owned_seats.values():
                txs_to_confirm.add(tx)

        if not txs_to_confirm:
            QMessageBox.warning(self, "Validación", "No tienes ningún asiento reservado ni has ingresado un ID de transacción para confirmar.")
            return

        for tx in txs_to_confirm:
            self.purchase.confirm_purchase(tx)
                
        # Actualizar UI para asientos visibles de la zona actual
        for key in list(self.seat_map.owned_seats.keys()):
            z, r, c = key
            if z == self.seat_map.zone_id:
                btn = self.seat_map.seat_buttons.get((r, c))
                if btn:
                    btn.selected = False
                    btn.sync_state("V")
                    btn._apply_style()

        self.seat_map.owned_seats.clear()
        self.tx_input.clear()
        self.countdown_seconds = 0
        self.seat_map.selection_changed.emit((self.seat_map.local_cart, self.seat_map.owned_seats))

    def _do_cancel(self):
        tx_text = self.tx_input.text().strip()
        txs_to_cancel = set()
        
        if tx_text:
            for tx in tx_text.split(","):
                tx = tx.strip()
                if tx:
                    txs_to_cancel.add(tx)
                    
        if self.seat_map.owned_seats:
            for tx in self.seat_map.owned_seats.values():
                txs_to_cancel.add(tx)

        if not txs_to_cancel:
            if self.seat_map.local_cart:
                for key in list(self.seat_map.local_cart):
                    z, r, c = key
                    if z == self.seat_map.zone_id:
                        btn = self.seat_map.seat_buttons.get((r, c))
                        if btn:
                            btn.selected = False
                            btn.sync_state("D")
                            btn._apply_style()
                self.seat_map.local_cart.clear()
                self.seat_map.selection_changed.emit((self.seat_map.local_cart, self.seat_map.owned_seats))
            else:
                QMessageBox.warning(self, "Validación", "No hay ningún asiento para cancelar. Selecciona uno primero o ingresa el ID.")
            return

        for tx in txs_to_cancel:
            self.purchase.cancel_reservation(tx)
                
        for key in list(self.seat_map.owned_seats.keys()):
            z, r, c = key
            if z == self.seat_map.zone_id:
                btn = self.seat_map.seat_buttons.get((r, c))
                if btn:
                    btn.selected = False
                    btn.sync_state("D")
                    btn._apply_style()

        self.seat_map.owned_seats.clear()
        self.tx_input.clear()
        self.countdown_seconds = 0
        self.seat_map.selection_changed.emit((self.seat_map.local_cart, self.seat_map.owned_seats))

    def _on_seat_cancel_request(self, tx_id, key):
        """Se activa al hacer clic sobre un asiento que ya estaba reservado — cancela SOLO ese asiento."""
        # Cancelar solo esa transacción específica en el servidor
        self.purchase.cancel_reservation(tx_id)
        # Quitar solo el asiento correspondiente del mapa
        z, r, c = key
        self.seat_map.owned_seats.pop(key, None)
        if z == self.seat_map.zone_id:
            btn = self.seat_map.seat_buttons.get((r, c))
            if btn:
                btn.selected = False
                btn.sync_state("D")
                btn._apply_style()
        self.seat_map._update_selection_label()
        self.seat_map.selection_changed.emit((self.seat_map.local_cart, self.seat_map.owned_seats))
        if not self.seat_map.owned_seats:
            self.countdown_seconds = 0
            self.lbl_countdown.setText("")
            self.tx_input.clear()
        else:
            self._refresh_selection_panel()

    def _on_tx_result(self, resp, success_msg):
        if resp["ok"]:
            self._log(f"Confirmado: {success_msg}")
            self.tx_input.clear()
        else:
            self._log(f"Error: {resp.get('error', 'Desconocido')}")

    def _on_error(self, msg):
        self._log(f"Error: {msg}")

    def _on_seat_error(self, msg):
        """Muestra errores de selección/conflicto de asiento en la bitácora."""
        self._log(f"Aviso: {msg}")

    def _log(self, msg):
        import time
        ts = time.strftime("%H:%M:%S")
        self.log_signal.emit(f"[{ts}] {msg}")

    def reset(self):
        """Detiene timers y limpia estado para logout sin reiniciar el proceso."""
        self.timer.stop()
        self.countdown_seconds = 0
        self.lbl_countdown.setText("")
        self.seat_map.reset()
        self.tx_input.clear()
        self._refresh_selection_panel()
        self.timer.start(1000)


# ── Tab: Estado global ──────────────────────────────────────────────────────
class StatusTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Estado Global del Sistema")
        title.setObjectName("heading")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Agregamos QScrollArea para evitar que las tarjetas se corten
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.cards_layout = QGridLayout(scroll_content)
        self.cards_layout.setHorizontalSpacing(12)
        self.cards_layout.setVerticalSpacing(12)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        self.stat_cards = {}
        
        from PyQt6.QtWidgets import QProgressBar
        
        self.progress_bars = {}
        for index, (zone_id, name) in enumerate(ZONE_NAMES.items()):
            grp = QGroupBox(f"Ocupación: {name}")
            grp.setMinimumWidth(260)
            grp.setStyleSheet(f"""
                QGroupBox {{
                    border: 1px solid {ZONE_COLORS[zone_id]}55;
                    border-radius: 10px;
                    margin-top: 14px;
                    padding-top: 10px;
                    color: {ZONE_COLORS[zone_id]};
                    font-weight: 700;
                    font-size: 14px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 14px;
                    padding: 0 6px;
                    color: {ZONE_COLORS[zone_id]};
                }}
            """)
            grp_layout = QVBoxLayout(grp)
            grp_layout.setSpacing(14)
            
            # Progress bar
            pb = QProgressBar()
            pb.setFixedHeight(12)
            pb.setTextVisible(False)
            pb.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    background-color: {BG_DEEP};
                    border-radius: 6px;
                }}
                QProgressBar::chunk {{
                    background-color: {ZONE_COLORS[zone_id]};
                    border-radius: 6px;
                }}
            """)
            self.progress_bars[zone_id] = pb
            grp_layout.addWidget(pb)
            
            # Stats row
            stats_layout = QHBoxLayout()
            cards = {}
            card_specs = [
                ("disponibles",    "Libres",      GREEN),
                ("seleccionados",   "En selección", SEAT_RESERVED),
                ("reservados",      "Reservados",   YELLOW),
                ("vendidos",        "Vendidos",     SEAT_SOLD),
                ("total",           "Total",        TEXT_SEC),
            ]
            for key, label, color in card_specs:
                card = StatCard(label, "—", color)
                cards[key] = card
                stats_layout.addWidget(card)
            
            grp_layout.addLayout(stats_layout)
            self.stat_cards[zone_id] = cards
            self.cards_layout.addWidget(grp, index // 2, index % 2)
            
        self.cards_layout.setRowStretch(self.cards_layout.rowCount(), 1)

        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.load)
        self.auto_timer.start(5000)
        self.load()

    def load(self):
        worker = NetworkWorker(global_state)
        worker.result.connect(self._on_loaded)
        worker.error.connect(lambda e: None)
        worker.start()
        self._workers.append(worker)

    def _on_loaded(self, resp):
        if not resp["ok"]:
            return
        for zone_id_str, info in resp["state"].items():
            zone_id = int(zone_id_str)
            cards   = self.stat_cards.get(zone_id, {})
            cards.get("disponibles",  StatCard("")).update_value(info["disponibles"],             GREEN)
            cards.get("seleccionados",StatCard("")).update_value(info.get("seleccionados", 0),    SEAT_RESERVED)
            cards.get("reservados",   StatCard("")).update_value(info["reservados"],              YELLOW)
            cards.get("vendidos",     StatCard("")).update_value(info["vendidos"],                RED)
            cards.get("total",        StatCard("")).update_value(info["total"],                   TEXT_SEC)

            total      = info["total"]
            vendidos   = info["vendidos"]
            reservados = info["reservados"]
            seleccionados = info.get("seleccionados", 0)

            pb = self.progress_bars.get(zone_id)
            if pb and total > 0:
                pb.setMaximum(total)
                pb.setValue(vendidos + reservados + seleccionados)


# ── Tab: Bitácora ────────────────────────────────────────────────────────────
class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Consola de Actividad Global")
        title.setObjectName("heading")
        title.setStyleSheet("font-size: 20px; color: #a1a1aa;")
        self.btn_clear = QPushButton("Limpiar consola")
        self.btn_clear.setObjectName("secondary")
        self.btn_clear.setMinimumWidth(150)
        self.btn_clear.clicked.connect(lambda: self.log_text.clear())
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.btn_clear)
        layout.addLayout(header)



        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 1)

        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.load)
        self.auto_timer.start(3000)
        self.load()

    def load(self):
        worker = NetworkWorker(get_log)
        worker.result.connect(self._on_loaded)
        worker.error.connect(lambda e: None)
        worker.start()
        self._workers.append(worker)

    def _on_loaded(self, resp):
        if not resp["ok"]:
            return
        entries = resp["log"]
        
        # Evitar parpadeos horribles del scroll si la bitacora no ha cambiado
        if len(entries) == getattr(self, "_last_log_count", 0):
            return
        self._last_log_count = len(entries)

        self.log_text.clear()
        for entry in entries:
            if "COMPRA CONFIRMADA" in entry:
                color = GREEN
            elif "CANCELACIÓN" in entry or "TTL RESERVA EXPIRADO" in entry:
                color = RED
            elif "TTL SELECCIÓN EXPIRADO" in entry or "DESELECCIÓN" in entry:
                color = TEXT_SEC
            elif "SELECCIÓN" in entry:
                color = SEAT_SELECTED
            elif "MÚLTIPLE" in entry or "MULTIPLE" in entry:
                color = ACCENT2
            elif "DESCONEXIÓN" in entry:
                color = YELLOW
            elif "RESERVA" in entry:
                color = ACCENT2
            else:
                color = TEXT_PRI
            self.log_text.append(
                f"<span style='color:{color}; font-family:monospace;'>{entry}</span>"
            )

    def append_entry(self, msg):
        self.log_text.append(
            f"<span style='color:{ACCENT2}; font-family:monospace;'>{msg}</span>"
        )

# ── Ventana principal ────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    """Ventana principal con pantalla de login integrada (QStackedWidget).
    - Página 0: Formulario de Login/Registro
    - Página 1: UI completa de reservas
    """

    def __init__(self):
        super().__init__()
        self.username = ""
        self.setWindowTitle("Sistema de Conciertos")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self._center_window()
        self._build_ui()

    def _center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

    # ── Página 0: pantalla de login/registro ────────────────────────────────────────
    def _build_name_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background: {BG_DEEP};")

        outer = QVBoxLayout(page)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setContentsMargins(20, 20, 20, 20)

        self.auth_card = QFrame()
        self.auth_card.setFixedWidth(420)
        self.auth_card.setStyleSheet(f"""
            .QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
        """)
        cl = QVBoxLayout(self.auth_card)
        cl.setContentsMargins(36, 32, 36, 32)
        cl.setSpacing(0)

        icon_lbl = QLabel("🎫")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 40px; background: transparent; border: none;")
        cl.addWidget(icon_lbl)
        cl.addSpacing(8)

        title = QLabel("Sistema de Reservas")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {TEXT_PRI}; "
            "background: transparent; letter-spacing: -0.3px; border: none;"
        )
        cl.addWidget(title)

        sub = QLabel("Conciertos — Entradas en línea")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        cl.addWidget(sub)
        cl.addSpacing(24)

        lbl_usr = QLabel("USUARIO")
        lbl_usr.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; "
            "background: transparent; border: none; letter-spacing: 1px;"
        )
        self.inp_login_usr = QLineEdit()
        self.inp_login_usr.setPlaceholderText("Ingresa tu usuario")
        self._style_auth_input(self.inp_login_usr)

        lbl_pwd = QLabel("CONTRASEÑA")
        lbl_pwd.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; "
            "background: transparent; border: none; letter-spacing: 1px;"
        )
        self.inp_login_pwd = QLineEdit()
        self.inp_login_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_login_pwd.setPlaceholderText("••••••••")
        self._style_auth_input(self.inp_login_pwd)

        cl.addWidget(lbl_usr)
        cl.addSpacing(4)
        cl.addWidget(self.inp_login_usr)
        cl.addSpacing(12)
        cl.addWidget(lbl_pwd)
        cl.addSpacing(4)
        cl.addWidget(self.inp_login_pwd)
        cl.addSpacing(18)

        # Botón Iniciar Sesión
        self.btn_login = QPushButton("Iniciar Sesión")
        self._style_auth_btn(self.btn_login)
        self.btn_login.clicked.connect(self._do_login)
        self.inp_login_pwd.returnPressed.connect(self._do_login)
        cl.addWidget(self.btn_login)
        cl.addSpacing(8)

        # Botón Registrarse (mismo formulario)
        self.btn_register = QPushButton("Crear Cuenta Nueva")
        self.btn_register.setMinimumHeight(44)
        self.btn_register.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_register.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {ACCENT2};
                border: 1.5px solid {ACCENT2};
                border-radius: 10px;
                font-size: 14px; font-weight: 700;
            }}
            QPushButton:hover {{ background: {ACCENT2}22; color: #93c5fd; border-color: #93c5fd; }}
            QPushButton:pressed {{ background: {ACCENT}33; }}
            QPushButton:disabled {{ border-color: {BORDER}; color: {TEXT_MUTED}; background: transparent; }}
        """)
        self.btn_register.clicked.connect(self._do_register)
        cl.addWidget(self.btn_register)
        cl.addSpacing(16)

        # Separador y configuración de red SIEMPRE VISIBLE (no colapsable)
        net_sep = QFrame()
        net_sep.setFrameShape(QFrame.Shape.HLine)
        net_sep.setStyleSheet(f"border: none; border-top: 1px solid {BORDER};")
        cl.addWidget(net_sep)
        cl.addSpacing(10)

        lbl_net = QLabel("⚙  Servidor")
        lbl_net.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        cl.addWidget(lbl_net)
        cl.addSpacing(6)

        net_row = QHBoxLayout()
        net_row.setSpacing(8)
        self.inp_net_ip = QLineEdit("127.0.0.1")
        self.inp_net_ip.setPlaceholderText("IP del servidor")
        self._style_auth_input(self.inp_net_ip)
        self.inp_net_port = QLineEdit("9090")
        self.inp_net_port.setPlaceholderText("Puerto")
        self.inp_net_port.setMaximumWidth(90)
        self._style_auth_input(self.inp_net_port)
        self.btn_net = QPushButton("Guardar")
        self.btn_net.setMinimumHeight(40)
        self.btn_net.setStyleSheet(f"""
            QPushButton {{ background: {BG_HOVER}; color: {TEXT_PRI}; border: 1px solid {BORDER};
                border-radius: 10px; font-weight: 700; font-size: 13px; }}
            QPushButton:hover {{ background: {ACCENT}; border-color: {ACCENT}; color: white; }}
        """)
        self.btn_net.clicked.connect(self._do_save_net)
        net_row.addWidget(self.inp_net_ip, 1)
        net_row.addWidget(self.inp_net_port)
        net_row.addWidget(self.btn_net)
        cl.addLayout(net_row)
        cl.addSpacing(12)

        self.lbl_auth_err = QLabel("")
        self.lbl_auth_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_auth_err.setStyleSheet(
            f"color: {RED}; font-size: 12px; background: transparent; min-height: 16px; border: none;"
        )
        self.lbl_auth_err.setWordWrap(True)
        self._auth_msg_color = RED
        cl.addWidget(self.lbl_auth_err)

        nota = QLabel(f"Sesión: {SESSION_ID[:8].upper()}")
        nota.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nota.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; background: transparent; border: none;"
        )
        cl.addWidget(nota)

        outer.addWidget(self.auth_card)
        return page

    def _toggle_register_panel(self):
        pass  # eliminado - ya no se usa

    def _toggle_net_panel(self):
        pass  # eliminado - ya no se usa

    def _style_auth_input(self, inp):
        inp.setMinimumHeight(42)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_PANEL}; border: 1.5px solid {BORDER}; border-radius: 10px;
                padding: 0 14px; color: {TEXT_PRI}; font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; background: {BG_DEEP}; }}
        """)

    def _style_auth_btn(self, btn):
        btn.setMinimumHeight(46)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #2563eb);
                color: #fff; border: none; border-radius: 10px; font-size: 15px; font-weight: 800;
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #60a5fa, stop:1 #3b82f6); }}
            QPushButton:pressed {{ background: #1d4ed8; }}
            QPushButton:disabled {{ background: #27272a; color: #64748b; }}
        """)

    def _do_login(self):
        usr = self.inp_login_usr.text().strip()
        pwd = self.inp_login_pwd.text().strip()
        if not usr or not pwd:
            self._show_auth_err("Completa todos los campos.")
            return
            
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Validando...")
        self.lbl_auth_err.setText("")
        
        worker = NetworkWorker(login, usr, pwd, SESSION_ID)
        worker.result.connect(lambda resp: self._on_auth_result(resp, "login"))
        worker.error.connect(lambda err: self._on_auth_network_error(err, "login"))
        worker.start()

    def _do_register(self):
        usr = self.inp_login_usr.text().strip()
        pwd = self.inp_login_pwd.text().strip()
        if not usr or not pwd:
            self._show_auth_err("Completa todos los campos.")
            return
        if len(usr) < 3:
            self._show_auth_err("El usuario debe tener al menos 3 caracteres.")
            return
        if len(pwd) < 4:
            self._show_auth_err("La contraseña debe tener al menos 4 caracteres.")
            return
            
        self.btn_register.setEnabled(False)
        self.btn_register.setText("Registrando...")
        self.lbl_auth_err.setText("")
        
        worker = NetworkWorker(register, usr, pwd, SESSION_ID)
        worker.result.connect(lambda resp: self._on_auth_result(resp, "register"))
        worker.error.connect(lambda err: self._on_auth_network_error(err, "register"))
        worker.start()

    def _do_save_net(self):
        ip = self.inp_net_ip.text().strip()
        port = self.inp_net_port.text().strip()
        if not ip or not port:
            self._show_auth_err("Debes indicar IP y Puerto.")
            return
        try:
            port_i = int(port)
            set_server_address(ip, port_i)
            self._show_auth_ok(f"✓ Configuración guardada ({ip}:{port_i})")
            # Actualizar status bar si ya está en la pantalla principal
            if hasattr(self, '_statusbar'):
                self._statusbar.showMessage(
                    f"Conectado a {ip}:{port_i}  •  TTL de selección: 60s  •  Sesión: {SESSION_ID[:8].upper()}"
                )
        except ValueError:
            self._show_auth_err("El puerto debe ser un número entero.")


    def _on_auth_result(self, resp, auth_type):
        if resp.get("ok"):
            self.username = resp.get("username", "Usuario")
            self.setWindowTitle(f"Sistema de Conciertos — {self.username}")
            self._user_lbl.setText(self.username)
            if auth_type == "login":
                self.btn_login.setText("Ingreso Exitoso!")
            else:
                self.btn_register.setText("Cuenta Creada!")
            QTimer.singleShot(300, lambda: self._enter_main_page())
        else:
            self._show_auth_err(f"Error: {resp.get('error', 'Error desconocido')}")
            if auth_type == "login":
                self.btn_login.setEnabled(True)
                self.btn_login.setText("Iniciar Sesión")
            else:
                self.btn_register.setEnabled(True)
                self.btn_register.setText("Crear Cuenta")

    def _on_auth_network_error(self, err_msg, auth_type):
        self._show_auth_err(f"Error de red: {err_msg}")
        if auth_type == "login":
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Iniciar Sesión")
        else:
            self.btn_register.setEnabled(True)
            self.btn_register.setText("Crear Cuenta")

    def _show_auth_err(self, msg):
        self.lbl_auth_err.setStyleSheet(
            f"color: {RED}; font-size: 12px; background: transparent; min-height: 16px; border: none;"
        )
        self.lbl_auth_err.setText(msg)

    def _show_auth_ok(self, msg):
        self.lbl_auth_err.setStyleSheet(
            f"color: {GREEN}; font-size: 12px; background: transparent; min-height: 16px; border: none;"
        )
        self.lbl_auth_err.setText(msg)


    # ── Página 1: UI principal ───────────────────────────────────────────────
    def _build_main_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background: {BG_DEEP};")
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        topbar = QWidget()
        topbar.setFixedHeight(56)
        topbar.setStyleSheet(f"background: {BG_CARD}; border-bottom: 1px solid {BORDER};")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("🎫  Sistema de Reservas")
        logo.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {TEXT_PRI}; letter-spacing: -0.5px;")

        self.status_dot = QLabel("● Conectado")
        self.status_dot.setStyleSheet(f"color: {GREEN}; font-size: 14px;")

        user_badge = QFrame()
        user_badge.setStyleSheet(f"""
            .QFrame {{
                background: {BG_PANEL};
                border: 1px solid {BORDER};
                border-radius: 20px;
                padding: 0px;
            }}
        """)
        user_badge_layout = QHBoxLayout(user_badge)
        user_badge_layout.setContentsMargins(10, 4, 14, 4)
        user_badge_layout.setSpacing(8)

        avatar = QLabel("👤")
        avatar.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        self._user_lbl = QLabel(self.username)
        self._user_lbl.setStyleSheet(f"color: {TEXT_PRI}; font-size: 14px; font-weight: 700; background: transparent; border: none;")
        session_lbl = QLabel(f"· {SESSION_ID[:6].upper()}")
        session_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; background: transparent; border: none;")
        user_badge_layout.addWidget(avatar)
        user_badge_layout.addWidget(self._user_lbl)
        user_badge_layout.addWidget(session_lbl)

        self.btn_logout = QPushButton("Cerrar Sesión")
        self.btn_logout.setObjectName("secondary")
        self.btn_logout.setStyleSheet(f"color: {RED}; font-size: 13px; font-weight: 700; padding: 4px 12px; height: 26px;")
        self.btn_logout.clicked.connect(self._do_logout)

        topbar_layout.addWidget(logo)
        topbar_layout.addStretch()
        topbar_layout.addWidget(user_badge)
        topbar_layout.addWidget(self.btn_logout)
        topbar_layout.addSpacing(16)
        topbar_layout.addWidget(self.status_dot)
        root.addWidget(topbar)

        self.lbl_cart_strip = QLabel("")
        self.lbl_cart_strip.setFixedHeight(22)
        self.lbl_cart_strip.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_cart_strip.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; background: transparent; "
            f"border: none; padding-right: 16px;"
        )
        root.addWidget(self.lbl_cart_strip)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        self.tab_reserve = ReserveTab()
        self.tab_status  = StatusTab()

        tabs.addTab(self.tab_reserve, "Reservas")
        tabs.addTab(self.tab_status,  "Estado Global")

        self.tab_log_full = LogTab()
        tabs.addTab(self.tab_log_full, "Bitácora Completa")

        self.tab_log = LogTab()
        self.tab_log.setMinimumHeight(180)
        self.tab_log.setMaximumHeight(260)

        self.tab_reserve.log_signal.connect(self.tab_log.append_entry)
        self.tab_reserve.log_signal.connect(self.tab_log_full.append_entry)
        self.tab_reserve.summary_updated.connect(self._on_summary_updated)
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(tabs)
        main_splitter.addWidget(self.tab_log)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)

        root.addWidget(main_splitter, 1)

        from client.cliente_lib import DEFAULT_HOST as _h, DEFAULT_PORT as _p
        self._statusbar = QStatusBar()
        self._statusbar.showMessage(f"Conectado a {_h}:{_p}  •  TTL de selección: 60s  •  Sesión: {SESSION_ID[:8].upper()}")
        self.setStatusBar(self._statusbar)

        # Ping timer
        self.ping_timer = QTimer()
        self.ping_timer.timeout.connect(self._ping)
        self.ping_timer.start(8000)

        return page

    def _build_ui(self):
        """Construye el QStackedWidget con las dos páginas."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_name_page())  # índice 0
        self._stack.addWidget(self._build_main_page())  # índice 1
        layout.addWidget(self._stack)

    def _ping(self):
        worker = NetworkWorker(global_state, SESSION_ID)
        worker.result.connect(lambda r: self.status_dot.setText(
            f"● Conectado" if r.get("ok") else f"● Error"
        ))
        worker.result.connect(lambda r: self.status_dot.setStyleSheet(
            f"color: {GREEN}; font-size: 14px;" if r.get("ok")
            else f"color: {RED}; font-size: 14px;"
        ))
        worker.error.connect(lambda _: (
            self.status_dot.setText("● Desconectado"),
            self.status_dot.setStyleSheet(f"color: {RED}; font-size: 14px;")
        ))
        worker.start()
        self._ping_worker = worker

    def _on_summary_updated(self, text, color):
        self.lbl_cart_strip.setText(text)
        self.lbl_cart_strip.setStyleSheet(
            f"color: {color}; font-size: 11px; background: transparent; "
            f"border: none; padding-right: 16px;"
        )

    def _do_logout(self):
        reply = QMessageBox.question(
            self, 'Cerrar Sesión',
            '¿Estás seguro de que deseas cerrar sesión?\nTus asientos seleccionados quedarán reservados para ti hasta que expire el TTL.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            worker = NetworkWorker(release_session, SESSION_ID)
            worker.result.connect(lambda _: self._go_to_login())
            worker.error.connect(lambda _: self._go_to_login())
            worker.start()

    def _go_to_login(self):
        """Vuelve a la pantalla de login dentro del mismo proceso — sin restart."""
        self.ping_timer.stop()
        self.tab_reserve.reset()
        # Limpiar el formulario de login
        self.inp_login_usr.clear()
        self.inp_login_pwd.clear()
        self.lbl_auth_err.setText("")
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Iniciar Sesión")
        self.btn_register.setEnabled(True)
        self.btn_register.setText("Crear Cuenta")
        self._stack.setCurrentIndex(0)

    def _enter_main_page(self):
        """Activa la página principal y reanuda timers al hacer login."""
        self._stack.setCurrentIndex(1)
        if not self.ping_timer.isActive():
            self.ping_timer.start(8000)
        # Reanudar TTL sync en ReserveTab para re-login dentro del mismo proceso
        self.tab_reserve._sync_ttl_from_server()

    def closeEvent(self, event):
        """
        Al cerrar la ventana con la X, solo liberamos el tracking de sesión activa.
        Los holds (SELECTED) y reservas (RESERVED) permanecen en el servidor
        con su TTL intacto — el usuario los verá al reingresar.
        """
        try:
            release_session(SESSION_ID)
        except Exception:
            pass  # Si el servidor no responde, el TTL liberará los asientos
        event.accept()



def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    # ── Manejador global de excepciones no capturadas ─────────────────────────
    # En el exe --noconsole, las excepciones en slots Qt matan el proceso
    # silenciosamente. Este hook las muestra en un cuadro de diálogo.
    def _qt_exception_hook(exc_type, exc_value, exc_tb):
        import traceback
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        try:
            from PyQt6.QtWidgets import QMessageBox
            box = QMessageBox()
            box.setWindowTitle("Error inesperado")
            box.setText(str(exc_value))
            box.setDetailedText(msg)
            box.setIcon(QMessageBox.Icon.Critical)
            box.exec()
        except Exception:
            pass
    sys.excepthook = _qt_exception_hook

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG_DEEP))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRI))
    palette.setColor(QPalette.ColorRole.Base, QColor(BG_CARD))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRI))
    app.setPalette(palette)

    window = MainWindow()   # abre directo, sin ventana separada
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

