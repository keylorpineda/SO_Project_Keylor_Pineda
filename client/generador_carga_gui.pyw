import sys
import os
import io
import traceback
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.cliente_lib import set_server_address

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QTextEdit, QFrame, QLineEdit,
    QMessageBox, QCheckBox, QGroupBox, QGridLayout, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# ── Paleta ─────────────────────────────────────────────────────────────────
BG_DEEP    = "#09090b"
BG_PANEL   = "#18181b"
BG_CARD    = "#1c1c22"
BORDER     = "#3f3f46"
ACCENT     = "#2563eb"
GREEN      = "#10b981"
RED        = "#ef4444"
YELLOW     = "#f59e0b"
TEXT_PRI   = "#f8fafc"
TEXT_SEC   = "#cbd5e1"
TEXT_MUTED = "#64748b"

ZONE_NAMES = {
    0: "VIP",
    1: "Preferencial Norte",
    2: "Preferencial Sur",
    3: "General Oeste",
    4: "General Este",
}

ZONE_DIMS = {
    0: (2, 10),
    1: (10, 12),
    2: (10, 12),
    3: (15, 10),
    4: (15, 10),
}


class _TestRunner(QThread):
    line_ready = pyqtSignal(str)
    test_done  = pyqtSignal(bool, str)

    def __init__(self, target_fn, parent=None):
        super().__init__(parent)
        self._target_fn = target_fn

    def run(self):
        buf = _SignalStream(self.line_ready)
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = buf
        sys.stderr = buf
        try:
            self._target_fn()
            self.test_done.emit(True, "=== Prueba completada con éxito ===")
        except SystemExit as e:
            self.test_done.emit(e.code == 0, f"=== Proceso terminó con código {e.code} ===")
        except Exception:
            self.test_done.emit(False, traceback.format_exc())
        finally:
            sys.stdout = old_out
            sys.stderr = old_err


class _SignalStream(io.RawIOBase):
    def __init__(self, signal):
        super().__init__()
        self._signal = signal

    def write(self, s):
        if isinstance(s, bytes):
            s = s.decode("utf-8", errors="replace")
        if s:
            self._signal.emit(s)
        return len(s)

    def writable(self):
        return True


class GeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generador de Carga Concurrente")
        self.resize(900, 680)
        self.setMinimumSize(800, 600)
        self._runner = None
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet(f"""
            QWidget {{ background-color: {BG_DEEP}; color: {TEXT_PRI}; font-size: 13px; }}
            QGroupBox {{ border: 1px solid {BORDER}; border-radius: 8px; margin-top: 14px;
                        font-weight: 700; color: {TEXT_SEC}; font-size: 13px; padding: 4px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {ACCENT}; }}
            QLineEdit, QSpinBox, QComboBox {{
                background: #1e1e2e; color: {TEXT_PRI}; border: 1px solid {BORDER};
                border-radius: 6px; padding: 5px 10px; font-size: 13px;
            }}
            QLineEdit:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
            QCheckBox {{ color: {TEXT_PRI}; spacing: 8px; font-size: 13px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;
                border: 1.5px solid {BORDER}; background: #1e1e2e; }}
            QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
            QPushButton {{ border-radius: 6px; padding: 7px 14px; font-weight: 700; }}
        """)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── Título ──────────────────────────────────────────────────────────
        title = QLabel("🧪  Generador de Carga Concurrente")
        title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {TEXT_PRI};")
        root.addWidget(title)

        # ── Red ─────────────────────────────────────────────────────────────
        net_grp = QGroupBox("Servidor")
        net_layout = QHBoxLayout(net_grp)
        lbl_ip = QLabel("IP:")
        lbl_ip.setStyleSheet(f"color: {TEXT_SEC}; border: none;")
        self.inp_ip = QLineEdit("127.0.0.1")
        self.inp_ip.setFixedWidth(160)
        lbl_port = QLabel("Puerto:")
        lbl_port.setStyleSheet(f"color: {TEXT_SEC}; border: none;")
        self.inp_port = QLineEdit("9090")
        self.inp_port.setFixedWidth(80)
        self.btn_save_net = QPushButton("Conectar")
        self.btn_save_net.setStyleSheet(
            f"background: {ACCENT}; color: white; border: none;"
        )
        self.btn_save_net.clicked.connect(self._save_net)
        net_layout.addWidget(lbl_ip)
        net_layout.addWidget(self.inp_ip)
        net_layout.addSpacing(10)
        net_layout.addWidget(lbl_port)
        net_layout.addWidget(self.inp_port)
        net_layout.addSpacing(10)
        net_layout.addWidget(self.btn_save_net)
        net_layout.addStretch()
        root.addWidget(net_grp)

        # ── Configuración de prueba ─────────────────────────────────────────
        cfg_row = QHBoxLayout()

        # Zonas
        zone_grp = QGroupBox("Zonas a probar")
        zone_inner = QVBoxLayout(zone_grp)
        zone_inner.setSpacing(4)
        self.chk_all_zones = QCheckBox("Todas las zonas")
        self.chk_all_zones.setChecked(True)
        self.chk_all_zones.clicked.connect(self._toggle_all)
        zone_inner.addWidget(self.chk_all_zones)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"border: 1px solid {BORDER};")
        zone_inner.addWidget(line)
        self.zone_checks = {}
        for zid, zname in ZONE_NAMES.items():
            chk = QCheckBox(f"Zona {zid}: {zname}")
            chk.setChecked(True)
            chk.clicked.connect(self._check_individual)
            self.zone_checks[zid] = chk
            zone_inner.addWidget(chk)
        cfg_row.addWidget(zone_grp)

        # Parámetros
        params_grp = QGroupBox("Parámetros de prueba")
        params_grid = QGridLayout(params_grp)
        params_grid.setSpacing(8)

        params_grid.addWidget(QLabel("Tipo de prueba:"), 0, 0)
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems([
            "Solo conflicto (mismo asiento)",
            "Solo carga masiva (asientos aleatorios)",
            "Ambas (conflicto + carga masiva)",
        ])
        self.cmb_mode.setCurrentIndex(2)
        self.cmb_mode.currentIndexChanged.connect(self._update_params_visibility)
        params_grid.addWidget(self.cmb_mode, 0, 1)

        params_grid.addWidget(QLabel("Usuarios en conflicto:"), 1, 0)
        self.spin_conflict = QSpinBox()
        self.spin_conflict.setRange(2, 500)
        self.spin_conflict.setValue(50)
        params_grid.addWidget(self.spin_conflict, 1, 1)

        params_grid.addWidget(QLabel("Usuarios carga masiva:"), 2, 0)
        self.spin_load = QSpinBox()
        self.spin_load.setRange(5, 2000)
        self.spin_load.setValue(100)
        params_grid.addWidget(self.spin_load, 2, 1)

        # Explicación de las categorías
        lbl_info_conf = QLabel("Conflicto: Simula N usuarios intentando comprar el MISMO asiento al MISMO tiempo.")
        lbl_info_conf.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        lbl_info_load = QLabel("Carga masiva: Simula N usuarios comprando asientos aleatorios para estresar el servidor.")
        lbl_info_load.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        
        params_grid.addWidget(lbl_info_conf, 3, 0, 1, 2)
        params_grid.addWidget(lbl_info_load, 4, 0, 1, 2)

        self.chk_confirm_random = QCheckBox("Confirmar/Cancelar aleatoriamente")
        self.chk_confirm_random.setChecked(True)
        params_grid.addWidget(self.chk_confirm_random, 5, 0, 1, 2)

        self.chk_gen_pdf = QCheckBox("Generar PDF de evidencia")
        self.chk_gen_pdf.setChecked(True)
        params_grid.addWidget(self.chk_gen_pdf, 6, 0, 1, 2)

        cfg_row.addWidget(params_grp, 1)
        root.addLayout(cfg_row)

        # ── Botones de acción ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.btn_run = QPushButton("▶  Ejecutar Prueba")
        self.btn_run.setStyleSheet(
            f"background: {GREEN}; color: white; border: none; font-size: 14px;"
        )
        self.btn_run.clicked.connect(self._run)

        self.btn_stop = QPushButton("■  Detener")
        self.btn_stop.setStyleSheet(
            f"background: {YELLOW}; color: #000; border: none; font-size: 14px;"
        )
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)

        self.btn_reset = QPushButton("⚠  Reiniciar Servidor (Wipe)")
        self.btn_reset.setStyleSheet(
            f"background: #7f1d1d; color: white; border: 1px solid {RED}; font-size: 13px;"
        )
        self.btn_reset.clicked.connect(self._reset_server)

        self.btn_clear = QPushButton("Limpiar consola")
        self.btn_clear.setStyleSheet(f"background: {BG_PANEL}; color: {TEXT_SEC}; border: 1px solid {BORDER};")
        self.btn_clear.clicked.connect(lambda: self.console_output.clear())

        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_reset)
        root.addLayout(btn_row)

        # ── Consola ─────────────────────────────────────────────────────────
        console_frame = QFrame()
        console_frame.setStyleSheet(
            f".QFrame {{ background: {BG_PANEL}; border: 1px solid {BORDER}; border-radius: 8px; }}"
        )
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(8, 8, 8, 8)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet(
            f"background: transparent; color: {GREEN}; "
            f"font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; border: none;"
        )
        console_layout.addWidget(self.console_output)
        root.addWidget(console_frame, 1)

    def _toggle_all(self, checked):
        for chk in self.zone_checks.values():
            chk.setChecked(checked)

    def _check_individual(self):
        all_checked = all(chk.isChecked() for chk in self.zone_checks.values())
        self.chk_all_zones.setChecked(all_checked)

    def _update_params_visibility(self, idx):
        mode = self.cmb_mode.currentIndex()
        self.spin_conflict.setEnabled(mode in (0, 2))
        self.spin_load.setEnabled(mode in (1, 2))

    def _save_net(self):
        try:
            port = int(self.inp_port.text().strip())
            set_server_address(self.inp_ip.text().strip(), port)
            self._log(f"[Red] Conectado a {self.inp_ip.text().strip()}:{port}\n")
        except ValueError:
            QMessageBox.warning(self, "Error", "Puerto inválido.")

    def _reset_server(self):
        reply = QMessageBox.question(
            self, "⚠ Peligro",
            "¿Seguro que desea reiniciar el servidor y borrar TODOS los datos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from client.cliente_lib import reset_server
            try:
                resp = reset_server()
                if resp.get("ok"):
                    self._log("[ADMIN] Servidor reiniciado correctamente.\n")
                else:
                    QMessageBox.warning(self, "Error", f"Error: {resp.get('error')}")
            except Exception as e:
                QMessageBox.critical(self, "Fallo", f"No se pudo contactar el servidor:\n{e}")

    def _get_target_zones(self):
        if self.chk_all_zones.isChecked():
            return list(ZONE_NAMES.keys())
        selected = [zid for zid, chk in self.zone_checks.items() if chk.isChecked()]
        return selected if selected else list(ZONE_NAMES.keys())

    def _run(self):
        if self._runner and self._runner.isRunning():
            return
        zones      = self._get_target_zones()
        mode       = self.cmb_mode.currentIndex()
        n_conflict = self.spin_conflict.value() if mode in (0, 2) else 0
        n_load     = self.spin_load.value()     if mode in (1, 2) else 0
        confirm_rnd = self.chk_confirm_random.isChecked()
        gen_pdf    = self.chk_gen_pdf.isChecked()

        self.console_output.clear()
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self._runner = _TestRunner(
            lambda: self._test_fn(zones, mode, n_conflict, n_load, confirm_rnd, gen_pdf),
            self
        )
        self._runner.line_ready.connect(self._log)
        self._runner.test_done.connect(self._on_done)
        self._runner.start()

    def _stop(self):
        if self._runner and self._runner.isRunning():
            self._runner.terminate()
            self._runner.wait()
            self._on_done(False, "Prueba detenida forzosamente.")

    def _log(self, line):
        self.console_output.moveCursor(self.console_output.textCursor().MoveOperation.End)
        self.console_output.insertPlainText(line)
        self.console_output.verticalScrollBar().setValue(
            self.console_output.verticalScrollBar().maximum()
        )

    def _on_done(self, ok, msg):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._log("\n" + msg + "\n")

    # ── Lógica de prueba ─────────────────────────────────────────────────────
    def _test_fn(self, zones, mode, n_conflict, n_load, confirm_rnd, gen_pdf):
        import threading, random
        from client.cliente_lib import reserve, confirm, cancel, global_state
        try:
            from fpdf import FPDF
            HAS_PDF = True
        except ImportError:
            HAS_PDF = False

        results_lock = threading.Lock()
        results      = []
        stats        = {"ok": 0, "rechazados": 0, "confirmados": 0, "cancelados": 0, "errores": 0}

        def log(msg, color=""):
            ts = time.strftime("%H:%M:%S") + f".{int(time.time()*1000)%1000:03d}"
            entry = f"[{ts}] {msg}"
            with results_lock:
                results.append(entry)
            print(entry)

        def simulated_user(uid, zone_id, row, col, do_confirm_rnd):
            try:
                resp = reserve(zone_id, row, col)
                if resp["ok"]:
                    tx_id = resp["tx_id"]
                    log(f"[OK] {uid} reservó Z{zone_id} F{row}C{col} → TX:{tx_id}")
                    with results_lock:
                        stats["ok"] += 1
                    if do_confirm_rnd:
                        action = random.choices(["confirm", "cancel"], weights=[70, 30])[0]
                    else:
                        action = "confirm"
                    if action == "confirm":
                        r2 = confirm(tx_id)
                        if r2["ok"]:
                            log(f"[✓] {uid} CONFIRMÓ TX:{tx_id}")
                            with results_lock: stats["confirmados"] += 1
                        else:
                            log(f"[!] {uid} fallo confirmar TX:{tx_id}: {r2['error']}")
                    else:
                        cancel(tx_id)
                        log(f"[x] {uid} canceló TX:{tx_id}")
                        with results_lock: stats["cancelados"] += 1
                else:
                    log(f"[✗] {uid} RECHAZADO Z{zone_id} F{row}C{col}: {resp['error']}")
                    with results_lock: stats["rechazados"] += 1
            except Exception as e:
                log(f"[ERR] {uid} error de red: {e}")
                with results_lock: stats["errores"] += 1

        def run_scenario(label, threads):
            print(f"\n{'='*60}")
            print(f"  {label}")
            print(f"{'='*60}")
            start = time.time()
            for t in threads: t.start()
            for t in threads: t.join()
            elapsed = time.time() - start
            print(f"  Completado en {elapsed:.2f}s con {len(threads)} hilos")

        # Escenario 1: Conflicto (muchos usuarios compitiendo por el mismo asiento)
        if mode in (0, 2) and n_conflict > 0:
            for zone_id in zones:
                rows, cols = ZONE_DIMS[zone_id]
                row_target = rows // 2
                col_target = cols // 2
                threads = [
                    threading.Thread(
                        target=simulated_user,
                        args=(f"C{i:03d}", zone_id, row_target, col_target, confirm_rnd),
                        daemon=True,
                    )
                    for i in range(n_conflict)
                ]
                run_scenario(
                    f"CONFLICTO | Zona {ZONE_NAMES[zone_id]} | {n_conflict} usuarios → F{row_target}C{col_target}",
                    threads,
                )
                time.sleep(1)

        # Escenario 2: Carga masiva (asientos aleatorios en zonas seleccionadas)
        if mode in (1, 2) and n_load > 0:
            load_threads = []
            for i in range(n_load):
                zone_id = random.choice(zones)
                rows, cols = ZONE_DIMS[zone_id]
                r = random.randint(0, rows - 1)
                c = random.randint(0, cols - 1)
                load_threads.append(
                    threading.Thread(
                        target=simulated_user,
                        args=(f"R{i:03d}", zone_id, r, c, confirm_rnd),
                        daemon=True,
                    )
                )
            zones_str = ", ".join(ZONE_NAMES[z] for z in zones)
            run_scenario(f"CARGA MASIVA | {n_load} usuarios | Zonas: {zones_str}", load_threads)
            time.sleep(1)

        # Reporte de integridad
        print(f"\n{'='*60}")
        print("  VERIFICACIÓN DE INTEGRIDAD")
        print(f"{'='*60}")
        try:
            resp = global_state()
            if resp["ok"]:
                total_asientos = 0
                for zone_id_str, info in resp["state"].items():
                    total = info["total"]
                    d = info["disponibles"]
                    r = info["reservados"]
                    v = info["vendidos"]
                    status = "✓ OK" if (d + r + v) == total else "✗ ERROR"
                    print(f"  Zona {info['nombre']:15s}: D={d:4d}  R={r:4d}  V={v:4d}  Total={total}  [{status}]")
                    total_asientos += total
        except Exception as e:
            print(f"  Error al consultar estado: {e}")

        print(f"\n  Resumen de operaciones:")
        print(f"  Reservas OK:     {stats['ok']}")
        print(f"  Rechazados:      {stats['rechazados']}")
        print(f"  Confirmados:     {stats['confirmados']}")
        print(f"  Cancelados:      {stats['cancelados']}")
        print(f"  Errores de red:  {stats['errores']}")

        # PDF de evidencia
        if gen_pdf and HAS_PDF:
            try:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Courier", "B", 12)
                pdf.cell(0, 10, "REPORTE: PRUEBA DE CONCURRENCIA", ln=True, align="C")
                pdf.set_font("Courier", size=9)
                pdf.cell(0, 8, f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
                pdf.cell(0, 8, f"Zonas: {', '.join(ZONE_NAMES[z] for z in zones)}", ln=True, align="C")
                pdf.ln(4)
                display = results if len(results) <= 300 else results[:150] + [f"... {len(results)-300} líneas omitidas ..."] + results[-150:]
                for entry in display:
                    clean = entry.encode("latin-1", "replace").decode("latin-1")
                    pdf.multi_cell(0, 4, txt=clean)
                pdf_path = os.path.abspath("Evidencia_Prueba_Concurrencia.pdf")
                pdf.output(pdf_path)
                print(f"\n  PDF generado: {pdf_path}")
            except Exception as e:
                print(f"\n  No se pudo generar el PDF: {e}")
        elif gen_pdf and not HAS_PDF:
            print("\n  [Aviso] fpdf2 no está instalado — PDF omitido.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = GeneratorApp()
    win.show()
    sys.exit(app.exec())
