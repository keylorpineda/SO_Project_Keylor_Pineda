# Sistema Concurrente de Gestión de Concierto Masivo

Sistema cliente-servidor para reserva y venta de entradas por zonas, implementado con hilos reales, exclusión mutua y semáforos. Fase III — Implementación Distribuida.

---

## Requisitos previos

- Python 3.10 o superior
- pip

---

## Opción A — Ejecutar desde código fuente (recomendado para desarrollo)

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Iniciar el servidor

```bash
python server/servidor.py
```

El servidor escucha en `0.0.0.0:9090`. Al iniciarse muestra la IP local para conexiones desde otras PCs en la misma red.

### 3. Iniciar el cliente GUI

```bash
python client/gui.pyw
```

Podés abrir múltiples instancias simultáneamente para simular varios usuarios. Cada instancia es un proceso independiente con su propio `SESSION_ID`.

### 4. Iniciar el generador de carga

```bash
python client/generador_carga_gui.pyw
```

---

## Opción B — Ejecutar desde ejecutables precompilados

Los ejecutables para Windows están en la carpeta `dist/`:

| Archivo | Descripción |
|---------|-------------|
| `dist/Servidor.exe` | Servidor central (iniciar primero) |
| `dist/GUI_Concierto.exe` | Cliente gráfico (una instancia por usuario) |
| `dist/Generador_Carga.exe` | Generador de carga concurrente |

**Orden de ejecución:**
1. Doble clic en `Servidor.exe`
2. Doble clic en `GUI_Concierto.exe` (una o más veces)
3. Doble clic en `Generador_Carga.exe` para pruebas de estrés

> El servidor crea `server_state.json` y `usuarios.json` en la misma carpeta donde se ejecuta (`dist/`). Al reiniciar el servidor, recupera el estado previo automáticamente.

---

## Opción C — Compilar ejecutables manualmente

### Windows

```bash
pip install pyinstaller fpdf2 PyQt6
python build_clients.py
```

Los ejecutables quedan en `dist/`. La primera compilación tarda ~2 minutos.

### macOS

```bash
pip install pyinstaller fpdf2 PyQt6
python build_clients.py
```

Genera `dist/Servidor`, `dist/GUI_Concierto.app` y `dist/Generador_Carga.app`.

Para ejecutar en macOS:
```bash
./dist/Servidor          # en una terminal
open dist/GUI_Concierto.app
open dist/Generador_Carga.app
```

> PyInstaller compila solo para la plataforma actual. No se puede compilar para Mac desde Windows ni viceversa.

---

## Opción D — Descargar ejecutables de macOS desde GitHub Actions

El repositorio compila automáticamente los ejecutables de macOS en cada push a `main`.

**Pasos para descargar:**

1. Ir al repositorio en GitHub
2. Clic en la pestaña **Actions**
3. En la columna izquierda, seleccionar **"Compilar para macOS"**
4. Clic en el workflow más reciente (el de arriba, con ✓ verde)
5. Bajar hasta la sección **Artifacts**
6. Clic en **`Ejecutables-MacOS`** para descargar el `.zip`
7. Extraer el `.zip` — contiene `Servidor`, `GUI_Concierto.app` y `Generador_Carga.app`

**Para ejecutar manualmente el workflow** (sin necesidad de hacer push):
1. Pestaña **Actions** → **"Compilar para macOS"**
2. Botón **"Run workflow"** (esquina derecha) → **"Run workflow"**
3. Esperar ~3 minutos → descargar artifacts

> En macOS, la primera vez puede aparecer un aviso de seguridad. Ir a **Ajustes del Sistema → Privacidad y Seguridad → Abrir de todas formas**.

---

## Configuración de red

Por defecto el cliente se conecta a `127.0.0.1:9090` (localhost).

**Para conectar desde otra PC en la misma red:**
1. En el servidor, anotar la IP que muestra al iniciar (ej. `192.168.1.5`)
2. En el cliente GUI: campo **IP** → ingresar esa IP → botón **Guardar**
3. En el generador: campo **IP** → ingresar esa IP → botón **Conectar**

**Puerto por defecto:** `9090`. Debe estar abierto en el firewall del equipo que corre el servidor.

---

## Generador de carga concurrente

El generador lanza N hilos simultáneos divididos automáticamente en dos escenarios:

| Escenario | Proporción | Propósito |
|-----------|-----------|-----------|
| Conflicto | ~20% de N | Múltiples usuarios compiten por el mismo asiento → valida exclusión mutua (safety) |
| Aleatorio | ~80% de N | Usuarios en asientos distribuidos → valida estabilidad bajo carga (liveness) |

Todos los hilos se lanzan al mismo tiempo. El reporte final muestra reservas exitosas, rechazadas, confirmadas, canceladas y errores. Con la opción PDF activada genera `Evidencia_Prueba_Concurrencia.pdf` con el log completo.

**Parámetros:**
- **Usuarios de carga:** total de hilos concurrentes (default 300, paso 50)
- **Confirmar/Cancelar aleatoriamente:** 70% confirma la compra, 30% cancela
- **Generar PDF de evidencia:** exporta el log de la prueba

---

## Zonas del concierto

| ID | Zona | Filas | Columnas | Capacidad |
|----|------|-------|----------|-----------|
| 0 | VIP | 5 | 10 | 50 |
| 1 | Preferencial Norte | 10 | 12 | 120 |
| 2 | Preferencial Sur | 10 | 12 | 120 |
| 3 | General Oeste | 15 | 10 | 150 |
| 4 | General Este | 15 | 10 | 150 |

**Total:** 590 asientos

---

## TTL y persistencia de sesión

- **TTL de selección:** 60 segundos desde la última interacción. Cualquier acción (seleccionar, deseleccionar) reinicia el contador.
- **TTL de reserva:** 60 segundos para confirmar o cancelar una reserva formal.
- **Persistencia:** al cerrar sesión, los asientos quedan guardados. Al reingresar dentro del TTL, el sistema los re-asocia al usuario automáticamente.
- **Estado del servidor:** se guarda en `server_state.json` al detectar cambios. Al reiniciar el servidor recupera reservas y holds activos.
