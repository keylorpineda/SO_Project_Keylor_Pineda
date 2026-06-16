import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.cliente_lib import check, reserve, reserve_multiple, confirm, cancel, global_state, get_log

ZONES = {
    0: "VIP",
    1: "Preferencial Norte",
    2: "Preferencial Sur",
    3: "General Oeste",
    4: "General Este",
}

# Códigos de color ANSI para mejorar la estética
C_GREEN = '\033[92m'
C_YELLOW = '\033[93m'
C_RED = '\033[91m'
C_BLUE = '\033[94m'
C_RESET = '\033[0m'

SYMBOLS = {
    "D": f"{C_GREEN}[ ]{C_RESET}", 
    "R": f"{C_YELLOW}[R]{C_RESET}", 
    "V": f"{C_RED}[X]{C_RESET}"
}


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def print_menu():
    print("\n" + "=" * 50)
    print("  SISTEMA DE CONCIERTOS — CLIENTE")
    print("=" * 50)
    print("  1. Consultar disponibilidad por zona")
    print("  2. Reservar asiento")
    print("  3. Reservar múltiples asientos")
    print("  4. Confirmar compra")
    print("  5. Cancelar reserva")
    print("  6. Estado global del sistema")
    print("  7. Ver bitácora")
    print("  0. Salir")
    print("=" * 50)


def print_matrix(state):
    # Imprimir encabezado de columnas
    cols = len(state[0])
    header = "      " + " ".join(f"{c:^3}" for c in range(cols))
    print(f"{C_BLUE}{header}{C_RESET}")
    
    for i, row in enumerate(state):
        line = f"{C_BLUE}  F{i:<2}{C_RESET} "
        for cell in row:
            line += SYMBOLS.get(cell, "[ ]") + " "
        print(line)


def select_zone():
    print("\nZonas disponibles:")
    for k, v in ZONES.items():
        print(f"  {k}: {v}")
    try:
        return int(input("Seleccione zona: "))
    except ValueError:
        return -1


def flow_check():
    zone_id = select_zone()
    resp = check(zone_id)
    if not resp["ok"]:
        print(f"Error: {resp['error']}")
        return
    print(f"\nMatriz zona {ZONES.get(zone_id, zone_id)}:")
    print(f"  Leyenda: {C_GREEN}[ ]=Disponible{C_RESET}  {C_YELLOW}[R]=Reservado{C_RESET}  {C_RED}[X]=Vendido{C_RESET}")
    print_matrix(resp["state"])


def flow_reserve():
    zone_id = select_zone()
    try:
        row = int(input("Fila: "))
        col = int(input("Columna: "))
    except ValueError:
        print("Entrada inválida.")
        return
    resp = reserve(zone_id, row, col)
    if not resp["ok"]:
        print(f"Error: {resp['error']}")
    else:
        print(f"Reserva exitosa. ID de transacción: {resp['tx_id']}")
        print("Tiene 30 segundos para confirmar la compra.")


def flow_reserve_multiple():
    print("Ingrese asientos (zona fila columna). Línea vacía para terminar.")
    seats = []
    while True:
        line = input(f"  Asiento {len(seats)+1}: ").strip()
        if not line:
            break
        try:
            z, r, c = map(int, line.split())
            seats.append([z, r, c])
        except ValueError:
            print("  Formato incorrecto. Use: zona fila columna")
    if not seats:
        return
    resp = reserve_multiple(seats)
    if not resp["ok"]:
        print(f"Error: {resp['error']}")
    else:
        print(f"Reserva múltiple exitosa. ID de transacción: {resp['tx_id']}")
        print("Tiene 30 segundos para confirmar la compra.")


def flow_confirm():
    tx_id = input("ID de transacción: ").strip().upper()
    resp  = confirm(tx_id)
    if not resp["ok"]:
        print(f"Error: {resp['error']}")
    else:
        print("Compra confirmada exitosamente.")


def flow_cancel():
    tx_id = input("ID de transacción: ").strip().upper()
    resp  = cancel(tx_id)
    if not resp["ok"]:
        print(f"Error: {resp['error']}")
    else:
        print("Reserva cancelada exitosamente.")


def flow_global_state():
    resp = global_state()
    if not resp["ok"]:
        print(f"Error: {resp['error']}")
        return
    print("\n--- ESTADO GLOBAL DEL SISTEMA ---")
    for zone_id, info in resp["state"].items():
        print(f"\n  Zona {info['nombre']}:")
        print(f"    Total: {info['total']}  |  Disponibles: {info['disponibles']}  |  Reservados: {info['reservados']}  |  Vendidos: {info['vendidos']}")


def flow_log():
    resp = get_log()
    if not resp["ok"]:
        print(f"Error: {resp['error']}")
        return
    entries = resp["log"]
    print(f"\n--- BITÁCORA ({len(entries)} eventos) ---")
    for entry in entries[-20:]:
        print(f"  {entry}")


def main():
    actions = {
        "1": flow_check,
        "2": flow_reserve,
        "3": flow_reserve_multiple,
        "4": flow_confirm,
        "5": flow_cancel,
        "6": flow_global_state,
        "7": flow_log,
    }
    while True:
        clear()
        print_menu()
        option = input("Opción: ").strip()
        if option == "0":
            print("Saliendo...")
            break
        action = actions.get(option)
        if action:
            try:
                action()
            except ConnectionRefusedError:
                print("No se pudo conectar al servidor. ¿Está corriendo en el puerto 9090?")
            except Exception as e:
                print(f"Error inesperado: {e}")
        else:
            print("Opción inválida.")
        input("\nPresione Enter para continuar...")


if __name__ == "__main__":
    main()
