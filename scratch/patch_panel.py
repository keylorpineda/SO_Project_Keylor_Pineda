import sys
filepath = r'c:\Users\Keylo\Documents\UNA\I CICLO 2026\Sistemas Operativos\Pineda_Keylor_Calderon_Allan\Pineda_Keylor_Calderon_Allan\client\gui.pyw'
content = open(filepath, 'r', encoding='utf-8').read()

NEW_FN = '''    def _refresh_selection_panel(self):
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
            lbl_zprice = QLabel(f"\u20a2\u00a0{price_unit:,.0f}\u00a0c/u")
            lbl_zprice.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
            zone_hdr_lay.addWidget(lbl_zname)
            zone_hdr_lay.addStretch()
            zone_hdr_lay.addWidget(lbl_zprice)
            self._breakdown_layout.addWidget(zone_hdr)

            for r, c in sorted(seats_here):
                seat_row = QHBoxLayout()
                seat_row.setContentsMargins(6, 1, 6, 1)
                lbl_seat = QLabel(f"    Fila\u00a0{r}  \u00b7  Col\u00a0{c}")
                lbl_seat.setStyleSheet(f"color: {TEXT_SEC}; font-size: 12px; border: none;")
                lbl_seat_price = QLabel(f"\u20a2\u00a0{price_unit:,.0f}")
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
            lbl_sub_r = QLabel(f"\u20a2\u00a0{subtotal:,.0f}")
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
            self.lbl_total.setText("\u20a2\u00a00")
        else:
            self.lbl_total.setText(f"\u20a2\u00a0{total_price:,.0f}")

        self._breakdown_layout.addStretch()

        if owned_seats:
            tx_ids = ", ".join(sorted(set(owned_seats.values())))
            self.tx_input.setText(tx_ids)
        else:
            self.tx_input.clear()

'''

m1 = '    def _refresh_selection_panel(self):'
m2 = '    def _apply_server_ttl(self, resp):'
i1 = content.find(m1)
i2 = content.find(m2)

if i1 < 0 or i2 < 0:
    print(f'ERROR: i1={i1}, i2={i2}')
    sys.exit(1)

new_content = content[:i1] + NEW_FN + content[i2:]
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f'Done: replaced {i2-i1} chars with {len(NEW_FN)} chars')
