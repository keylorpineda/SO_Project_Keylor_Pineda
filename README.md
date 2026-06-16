## 🚀 Cómo Ejecutar el Proyecto

Este proyecto está construido en Python y requiere algunas librerías externas para la interfaz gráfica. Asegúrate de tener instalado Python 3.8 o superior.

### 0. Instalar Dependencias
Antes de ejecutar el programa por primera vez, instala las dependencias necesarias mediante `pip` abriendo una terminal en la raíz del proyecto, esto es para abrir la interfaz luego:

```bash
pip install -r requirements.txt
```

### 1. Iniciar el Servidor (Backend)
Primero, debes iniciar el servidor central que controla los recursos y la concurrencia.Ejecuta el .exe en la carpeta dist

*(El servidor comenzará a escuchar conexiones en el puerto 9090).*

### 2. Iniciar el Cliente Gráfico (Frontend)
Para usar el programa con la interfaz gráfica (la aplicación para los clientes), puedes **hacer doble clic directamente sobre el archivo `gui.pyw`** ubicado dentro de la carpeta `client`, o bien abrir **otra pestaña de terminal** y ejecutar:

```bash
python client/gui.pyw
```
*(Puedes abrir tantas instancias de la interfaz como desees para probar la concurrencia entre varios clientes).*

### 3. Ejecutar las Pruebas de Estrés (Load Generator)
Para observar el comportamiento del sistema bajo condiciones de alta carga y verificar la prevención de interbloqueos (deadlocks) ante múltiples reservas simultáneas, puedes utilizar el simulador de tráfico de dos formas:

- **Desde la Interfaz Gráfica:** Puedes ir a la pestaña específica de pruebas ("Pruebas" o "Tests") dentro de la ventana del cliente, donde podrás lanzar los escenarios conflictivos y de carga con un solo clic.
- **Desde la terminal (opcional):** También puedes ejecutar el script por separado abriendo otra terminal:

```bash
python client/prueba_concurrente.py
```
*(Los resultados de la prueba se guardarán automáticamente en el archivo `logs_prueba_concurrente.txt`).*

---4

> **Nota para la revisión:** La interfaz gráfica ha sido diseñada permitiendo la acumulación de asientos de diferentes zonas en una misma reserva. El motor backend (`reserve_multiple` en `recursos.py`) garantizará la prevención de *deadlocks* ordenando los bloqueos por jerarquía de zona de acuerdo a la teoría de Coffman.
