# Guía de Despliegue y Conexión Remota (Fase 3)

Esta guía explica cómo ejecutar el servidor en una máquina remota y cómo conectar múltiples clientes reales hacia él, cumpliendo con los requisitos de la **Fase 3: Implementación Distribuida**.

## 1. Despliegue del Servidor (Máquina Host)

Para que el sistema sea accesible por otras computadoras, debes ejecutar el servidor en una máquina y asegurarte de que el puerto TCP `9090` esté abierto en su firewall.

### Opción A: Red Local (LAN - Wi-Fi de la Universidad/Casa)
Esta es la opción más sencilla para la presentación:
1. En la computadora que será el Servidor, abre tu terminal y obtén tu Dirección IP local:
   - **Windows**: Ejecuta `ipconfig` y busca "Dirección IPv4" (ej. `192.168.1.15`).
   - **Mac/Linux**: Ejecuta `ifconfig` o `ip a`.
2. Ejecuta el servidor:
   ```bash
   python server/servidor.py
   ```
3. **Importante**: Asegúrate de que el Firewall de Windows permita conexiones entrantes al puerto 9090, o simplemente desactívalo temporalmente durante la presentación.

### Opción B: Uso de Ngrok (A través de Internet sin configurar routers)
Si las máquinas no están en la misma red Wi-Fi, puedes usar Ngrok para exponer el servidor al internet público.
1. Ejecuta el servidor localmente: `python server/servidor.py`
2. Descarga [Ngrok](https://ngrok.com/) y ejecuta en otra terminal:
   ```bash
   ngrok tcp 9090
   ```
3. Ngrok te dará una dirección pública similar a: `tcp://0.tcp.ngrok.io:12345`
   - **IP del Servidor**: `0.tcp.ngrok.io`
   - **Puerto**: `12345`

### Opción C: Máquina Virtual en la Nube (AWS, Azure, GCP)
1. Lanza una instancia Linux (ej. Ubuntu EC2).
2. Clona tu repositorio y ejecuta `python3 server/servidor.py`.
3. En las reglas de seguridad (Security Groups) de tu nube, abre el puerto TCP `9090` (Custom TCP Rule -> Inbound).
4. Anota la IP Pública de la instancia.

---

## 2. Conexión desde los Clientes

En las computadoras de los clientes, no necesitas ejecutar el servidor, solo abrir la interfaz gráfica (`GUI_Concierto.exe`).

1. Abre el cliente gráfico.
2. Ve a la pestaña **"Red 🌍"**.
3. **Dirección IP del Servidor Remoto**:
   - Si usaste Opción A: Escribe la IP local (ej. `192.168.1.15`).
   - Si usaste Opción B: Escribe el dominio de ngrok (ej. `0.tcp.ngrok.io`).
   - Si usaste Opción C: Escribe la IP pública de AWS.
4. **Puerto TCP**:
   - Escribe `9090` (o el puerto que te dio ngrok si usaste la Opción B).
5. Haz clic en **💾 Guardar Configuración Red**.
6. Ve a la pestaña **"Iniciar Sesión"** y conéctate normalmente. ¡Todos los clientes ahora estarán viendo la misma matriz en la nube en tiempo real!

## 3. Demostración de Carga Concurrente Parametrizable

Una vez conectados al servidor remoto, la profesora puede solicitar verificar la carga concurrente.

1. Dentro de la aplicación, abre el panel lateral y selecciona **"Pruebas Automatizadas"**.
2. Modifica los parámetros según lo que la profesora exija:
   - **Usuarios en Conflicto**: Ej. `100` (100 peticiones peleando simultáneamente por la fila 2, columna 3).
   - **Carga Masiva**: Ej. `500` (500 solicitudes aleatorias bombardeando todo el recinto).
3. Haz clic en **⚡ Prueba Concurrente**.
4. El sistema atacará al servidor remoto con los hilos parametrizados y, al finalizar, generará automáticamente un PDF (`Evidencia_Prueba_Estres.pdf`) en el mismo directorio donde se encuentre el cliente para ser entregado.
