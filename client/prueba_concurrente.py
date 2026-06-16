import threading
import time
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.cliente_lib import reserve, confirm, cancel, global_state

LOG_FILE         = "logs_prueba_concurrente.txt"
results_lock     = threading.Lock()
results          = []


def log(message):
    ts    = time.strftime("%H:%M:%S.") + f"{int(time.time() * 1000) % 1000:03d}"
    entry = f"[{ts}] {message}"
    with results_lock:
        results.append(entry)
        print(entry)


def simulated_user(user_id, zone_id, row, col):
    log(f"Usuario {user_id} intenta reservar Z{zone_id} F{row}C{col}")
    try:
        resp = reserve(zone_id, row, col)
        if resp["ok"]:
            tx_id = resp["tx_id"]
            log(f"Usuario {user_id} obtuvo reserva {tx_id}")
            time.sleep(random.uniform(0.5, 3.0))
            action = random.choice(["confirm", "confirm", "cancel"])
            if action == "confirm":
                r2 = confirm(tx_id)
                if r2["ok"]:
                    log(f"Usuario {user_id} CONFIRMO compra {tx_id}")
                else:
                    log(f"Usuario {user_id} fallo al confirmar {tx_id}: {r2['error']}")
            else:
                cancel(tx_id)
                log(f"Usuario {user_id} cancelo {tx_id}")
        else:
            log(f"Usuario {user_id} RECHAZADO: {resp['error']}")
    except Exception as e:
        log(f"Usuario {user_id} error de conexion: {e}")


def scenario_conflict(n_users, zone_id, row, col):
    print(f"\n{'='*60}")
    print(f"ESCENARIO CONFLICTO: {n_users} usuarios compitiendo por Z{zone_id} F{row}C{col}")
    print(f"{'='*60}")
    threads = [
        threading.Thread(target=simulated_user, args=(f"C{i:03d}", zone_id, row, col))
        for i in range(n_users)
    ]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"Escenario completado en {time.time()-start:.2f}s")


def scenario_load(n_users):
    print(f"\n{'='*60}")
    print(f"ESCENARIO CARGA MASIVA: {n_users} usuarios aleatorios")
    print(f"{'='*60}")
    # Las zonas ahora son 0:50, 1:100, 2:100, 3:200, 4:300
    zone_dims = {
        0: (5, 10),
        1: (10, 10),
        2: (10, 10),
        3: (10, 20),
        4: (15, 20),
    }
    threads = []
    for i in range(n_users):
        zone_id      = random.randint(0, 4)
        rows, cols   = zone_dims[zone_id]
        row          = random.randint(0, rows - 1)
        col          = random.randint(0, cols - 1)
        t = threading.Thread(target=simulated_user, args=(f"R{i:03d}", zone_id, row, col))
        threads.append(t)
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"Escenario completado en {time.time()-start:.2f}s")


def verify_integrity():
    print("\n--- Verificación de integridad ---")
    resp = global_state()
    if not resp["ok"]:
        print("No se pudo obtener estado global.")
        return
    for zone_id, info in resp["state"].items():
        total    = info["total"]
        d        = info["disponibles"]
        r        = info["reservados"]
        v        = info["vendidos"]
        status   = "OK" if (d + r + v) == total else "ERROR"
        print(f"  Zona {info['nombre']}: D={d} R={r} V={v} Total={total} [{status}]")

def save_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"LOG PRUEBA CONCURRENTE — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n")
        for entry in results:
            f.write(entry + "\n")
    print(f"\nLogs guardados en {LOG_FILE}")
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Courier", size=9)
        pdf.cell(200, 10, txt="REPORTE OFICIAL: PRUEBA DE ESTRES Y CONCURRENCIA", ln=True, align='C')
        pdf.cell(200, 10, txt=f"Fecha y Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
        pdf.line(10, 30, 200, 30)
        pdf.ln(10)
        
        # We only print the first 50 and last 50 lines if it's too long, to avoid huge PDFs
        lines_to_print = results
        if len(results) > 200:
            lines_to_print = results[:100] + ["...", f"... ({len(results)-200} logs omitidos) ...", "..."] + results[-100:]
            
        for entry in lines_to_print:
            # clean latin-1
            clean = entry.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, txt=clean)
            
        pdf_path = os.path.abspath("Evidencia_Prueba_Estres.pdf")
        pdf.output(pdf_path)
        print(f"¡PDF de EVIDENCIA generado exitosamente en:\n  -> {pdf_path}")
    except Exception as e:
        print("No se pudo generar PDF:", e)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PRUEBA DE CONCURRENCIA — Sistema de Conciertos")
    parser.add_argument("--conflict", type=int, default=50, help="Número de usuarios compitiendo por un asiento")
    parser.add_argument("--load", type=int, default=200, help="Número de usuarios haciendo carga masiva")
    args = parser.parse_args()

    print("PRUEBA DE CONCURRENCIA — Sistema de Conciertos")
    print("Asegúrese de que el servidor esté corriendo\n")

    scenario_conflict(args.conflict, 0, 2, 3)
    time.sleep(2)

    scenario_load(args.load)
    time.sleep(2)

    verify_integrity()
    save_log()


if __name__ == "__main__":
    main()
