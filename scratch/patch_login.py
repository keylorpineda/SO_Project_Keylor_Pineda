import sys, io

filepath = r'c:\Users\Keylo\Documents\UNA\I CICLO 2026\Sistemas Operativos\Pineda_Keylor_Calderon_Allan\Pineda_Keylor_Calderon_Allan\client\gui.pyw'
content = open(filepath, 'r', encoding='utf-8-sig').read()

NEW_LOGIN = '''    # \u2500\u2500 P\u00e1gina 0: pantalla de login/registro \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    def _build_name_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background: {BG_DEEP};")

        outer = QVBoxLayout(page)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setFixedWidth(440)
        card.setStyleSheet(f"""
            .QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(36, 32, 36, 28)
        cl.setSpacing(0)

        icon_lbl = QLabel("\U0001f3ab")
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

        sub = QLabel("Conciertos \u2014 Entradas en l\u00ednea")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        cl.addWidget(sub)
        cl.addSpacing(24)

        lbl_login_usr = QLabel("USUARIO")
        lbl_login_usr.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; "
            "background: transparent; border: none; letter-spacing: 1px;"
        )
        self.inp_login_usr = QLineEdit()
        self.inp_login_usr.setPlaceholderText("Ingresa tu usuario")
        self._style_auth_input(self.inp_login_usr)

        lbl_login_pwd = QLabel("CONTRASE\u00d1A")
        lbl_login_pwd.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; "
            "background: transparent; border: none; letter-spacing: 1px;"
        )
        self.inp_login_pwd = QLineEdit()
        self.inp_login_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_login_pwd.setPlaceholderText("\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022")
        self._style_auth_input(self.inp_login_pwd)

        self.btn_login = QPushButton("Iniciar Sesi\u00f3n")
        self._style_auth_btn(self.btn_login)
        self.btn_login.clicked.connect(self._do_login)
        self.inp_login_pwd.returnPressed.connect(self._do_login)

        cl.addWidget(lbl_login_usr)
        cl.addSpacing(4)
        cl.addWidget(self.inp_login_usr)
        cl.addSpacing(12)
        cl.addWidget(lbl_login_pwd)
        cl.addSpacing(4)
        cl.addWidget(self.inp_login_pwd)
        cl.addSpacing(16)
        cl.addWidget(self.btn_login)

        cl.addSpacing(20)
        div_row = QHBoxLayout()
        div_left = QFrame()
        div_left.setFrameShape(QFrame.Shape.HLine)
        div_left.setStyleSheet(f"border: none; border-top: 1px solid {BORDER};")
        div_right = QFrame()
        div_right.setFrameShape(QFrame.Shape.HLine)
        div_right.setStyleSheet(f"border: none; border-top: 1px solid {BORDER};")
        div_lbl = QLabel("\u00bfNo tienes cuenta?")
        div_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; background: transparent; border: none; padding: 0 8px;"
        )
        div_row.addWidget(div_left, 1)
        div_row.addWidget(div_lbl)
        div_row.addWidget(div_right, 1)
        cl.addLayout(div_row)
        cl.addSpacing(10)

        self.btn_toggle_reg = QPushButton("Crear una cuenta  \u2192")
        self.btn_toggle_reg.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {ACCENT2}; border: none;
                font-size: 13px; font-weight: 700; padding: 6px;
            }}
            QPushButton:hover {{ color: #93c5fd; }}
        """)
        self.btn_toggle_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_reg.clicked.connect(self._toggle_register_panel)
        cl.addWidget(self.btn_toggle_reg, alignment=Qt.AlignmentFlag.AlignCenter)

        self._reg_panel = QFrame()
        self._reg_panel.setVisible(False)
        self._reg_panel.setStyleSheet(f"""
            .QFrame {{
                background: {BG_PANEL};
                border-radius: 12px;
                border: 1px solid {BORDER};
            }}
        """)
        reg_inner = QVBoxLayout(self._reg_panel)
        reg_inner.setContentsMargins(16, 14, 16, 14)
        reg_inner.setSpacing(8)

        lbl_reg_usr = QLabel("NUEVO USUARIO")
        lbl_reg_usr.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; "
            "background: transparent; border: none; letter-spacing: 1px;"
        )
        self.inp_reg_usr = QLineEdit()
        self.inp_reg_usr.setPlaceholderText("m\u00edn. 3 caracteres")
        self._style_auth_input(self.inp_reg_usr)

        lbl_reg_pwd = QLabel("CONTRASE\u00d1A NUEVA")
        lbl_reg_pwd.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; "
            "background: transparent; border: none; letter-spacing: 1px;"
        )
        self.inp_reg_pwd = QLineEdit()
        self.inp_reg_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_reg_pwd.setPlaceholderText("m\u00edn. 4 caracteres")
        self._style_auth_input(self.inp_reg_pwd)

        self.btn_register = QPushButton("Crear Cuenta")
        self.btn_register.setMinimumHeight(44)
        self.btn_register.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c3aed,stop:1 #6d28d9);
                color: white; border: none; border-radius: 10px;
                font-size: 14px; font-weight: 800;
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #a78bfa,stop:1 #7c3aed); }}
            QPushButton:pressed {{ background: #5b21b6; }}
            QPushButton:disabled {{ background: #27272a; color: #64748b; }}
        """)
        self.btn_register.clicked.connect(self._do_register)
        self.inp_reg_pwd.returnPressed.connect(self._do_register)

        reg_inner.addWidget(lbl_reg_usr)
        reg_inner.addWidget(self.inp_reg_usr)
        reg_inner.addWidget(lbl_reg_pwd)
        reg_inner.addWidget(self.inp_reg_pwd)
        reg_inner.addSpacing(4)
        reg_inner.addWidget(self.btn_register)
        cl.addWidget(self._reg_panel)

        cl.addSpacing(8)
        self.btn_toggle_net = QPushButton("\u2699  Configurar servidor")
        self.btn_toggle_net.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_MUTED}; border: none;
                font-size: 11px; font-weight: 600; padding: 4px;
            }}
            QPushButton:hover {{ color: {TEXT_SEC}; }}
        """)
        self.btn_toggle_net.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_net.clicked.connect(self._toggle_net_panel)
        cl.addWidget(self.btn_toggle_net, alignment=Qt.AlignmentFlag.AlignCenter)

        self._net_panel = QFrame()
        self._net_panel.setVisible(False)
        self._net_panel.setStyleSheet(
            f".QFrame {{ background: {BG_PANEL}; border-radius: 10px; border: 1px solid {BORDER}; }}"
        )
        net_inner = QHBoxLayout(self._net_panel)
        net_inner.setContentsMargins(12, 10, 12, 10)
        net_inner.setSpacing(8)
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
        net_inner.addWidget(self.inp_net_ip, 1)
        net_inner.addWidget(self.inp_net_port)
        net_inner.addWidget(self.btn_net)
        cl.addWidget(self._net_panel)

        cl.addSpacing(12)
        self.lbl_auth_err = QLabel("")
        self.lbl_auth_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_auth_err.setStyleSheet(
            f"color: {RED}; font-size: 12px; background: transparent; min-height: 16px; border: none;"
        )
        self.lbl_auth_err.setWordWrap(True)
        cl.addWidget(self.lbl_auth_err)

        nota = QLabel(f"Sesi\u00f3n: {SESSION_ID[:8].upper()}")
        nota.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nota.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; background: transparent; border: none;")
        cl.addWidget(nota)

        outer.addWidget(card)
        return page

    def _toggle_register_panel(self):
        visible = self._reg_panel.isVisible()
        self._reg_panel.setVisible(not visible)
        self.btn_toggle_reg.setText("\u2715 Cancelar" if not visible else "Crear una cuenta  \u2192")

    def _toggle_net_panel(self):
        self._net_panel.setVisible(not self._net_panel.isVisible())

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

'''

start_marker = '    # \u2500\u2500 P\u00e1gina 0: pantalla de login/registro'
end_marker = '    def _do_login(self):'
start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx < 0 or end_idx < 0:
    print(f"ERROR: start={start_idx}, end={end_idx}")
    sys.exit(1)

new_content = content[:start_idx] + NEW_LOGIN + content[end_idx:]
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f"Done. start={start_idx}, end={end_idx}, new_len={len(NEW_LOGIN)}")
