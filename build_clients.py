"""
build_clients.py  -  Genera los tres ejecutables:
    Windows:  dist/Servidor.exe  |  GUI_Concierto.exe  |  Generador_Carga.exe
    macOS:    dist/Servidor      |  GUI_Concierto.app   |  Generador_Carga.app
    Linux:    dist/Servidor      |  GUI_Concierto       |  Generador_Carga

Uso:
    python build_clients.py
"""

import subprocess
import sys
import os
import platform
import shutil

ROOT  = os.path.dirname(os.path.abspath(__file__))
DIST  = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build_tmp")

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS   = platform.system() == "Darwin"


def exe(name):
    """Devuelve el nombre del binario con extension segun el SO."""
    return f"{name}.exe" if IS_WINDOWS else name


def run(cmd):
    print(f"\n>>> {' '.join(str(c) for c in cmd)}\n")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"\n[ERROR] El comando fallo con codigo {result.returncode}.")
        sys.exit(result.returncode)


def build_exe(name, script, extra_imports=None, console=True):
    """Compila un ejecutable con PyInstaller (Windows / macOS / Linux)."""
    server_dir = os.path.join(ROOT, "server")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", name,
        "--distpath", DIST,
        "--workpath", BUILD,
        "--specpath", BUILD,
        "--paths", ROOT,
        "--paths", server_dir,
        "--hidden-import", "client",
        "--hidden-import", "client.cliente_lib",
        "--hidden-import", "PyQt6",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
    ]

    if console:
        cmd.append("--console")
    else:
        if IS_MACOS:
            cmd.append("--windowed")
        else:
            cmd.append("--noconsole")

    if extra_imports:
        for imp in extra_imports:
            cmd += ["--hidden-import", imp]

    cmd.append(script)
    run(cmd)


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller no encontrado. Instalando...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    os.makedirs(DIST, exist_ok=True)
    os.makedirs(BUILD, exist_ok=True)

    platform_tag = f"({platform.system()} {platform.machine()})"

    # 1. Servidor
    print(f"\n{'='*60}")
    print(f"  Compilando: Servidor  {platform_tag}")
    print(f"{'='*60}")
    build_exe(
        name    = "Servidor",
        script  = os.path.join(ROOT, "server", "servidor.py"),
        extra_imports = [
            "recursos", "gestor_ttl", "auth",
            "json", "threading", "socket", "uuid", "time",
        ],
        console = True,
    )

    users_src = os.path.join(ROOT, "server", "usuarios.json")
    users_dst = os.path.join(DIST, "usuarios.json")
    if os.path.exists(users_src) and not os.path.exists(users_dst):
        shutil.copy2(users_src, users_dst)
        print(f"\n  [INFO] usuarios.json copiado a dist/")
    elif os.path.exists(users_src):
        print(f"\n  [INFO] usuarios.json ya existe en dist/ - no se sobreescribe")

    # 2. GUI cliente
    print(f"\n{'='*60}")
    print(f"  Compilando: GUI_Concierto  {platform_tag}")
    print(f"{'='*60}")
    build_exe(
        name    = "GUI_Concierto",
        script  = os.path.join(ROOT, "client", "gui.pyw"),
        console = False,
    )

    # 3. Generador de carga
    print(f"\n{'='*60}")
    print(f"  Compilando: Generador_Carga  {platform_tag}")
    print(f"{'='*60}")
    build_exe(
        name    = "Generador_Carga",
        script  = os.path.join(ROOT, "client", "generador_carga_gui.pyw"),
        extra_imports = ["fpdf", "fpdf.fpdf"],
        console = False,
    )

    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
        print(f"\nCarpeta temporal eliminada.")

    print(f"\n{'='*60}")
    for name in ["Servidor", "GUI_Concierto", "Generador_Carga"]:
        candidates = [
            os.path.join(DIST, exe(name)),
            os.path.join(DIST, f"{name}.app"),
            os.path.join(DIST, name),
        ]
        found = next((p for p in candidates if os.path.exists(p)), None)
        if found:
            if os.path.isdir(found):
                size_bytes = sum(
                    os.path.getsize(os.path.join(dp, f))
                    for dp, _, files in os.walk(found) for f in files
                )
            else:
                size_bytes = os.path.getsize(found)
            size_mb = size_bytes / (1024 * 1024)
            print(f"  [OK] {os.path.basename(found):<30} {size_mb:.1f} MB")
        else:
            print(f"  [!!] {name} - NO GENERADO")
    print(f"{'='*60}\n")
    print(f"  Ejecutables en: {DIST}")
    print()
    print("  NOTA: Servidor busca 'usuarios.json' y 'server_state.json'")
    print("  en la misma carpeta donde se ejecuta (dist/).")
    if IS_MACOS:
        print()
        print("  macOS: GUI_Concierto.app y Generador_Carga.app son bundles.")
        print("  Para ejecutarlos: open dist/GUI_Concierto.app")
    print()


if __name__ == "__main__":
    main()
