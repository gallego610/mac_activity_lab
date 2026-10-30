# Activity Event Generator

Genera eventos de actividad en la posición actual del cursor según un intervalo configurable.
Disponible en tres versiones: **Python**, **JavaScript (Electron)** y **Java**.

---

## Versión Python

### Requisitos

- Python 3.10 o posterior
- Tkinter (incluido con Python)
- [pyautogui](https://pyautogui.readthedocs.io/)
- [pynput](https://pynput.readthedocs.io/) _(para inicio automático)_

```bash
cd python
pip install -r requirements.txt
# o
pip3 install -r requirements.txt
```

### Ejecutar

```bash
cd python
python app.py
# o
python3 app.py
```

### Cómo funciona

`app.py` contiene toda la lógica. Al activar el **inicio automático**, el mismo archivo
se relanza como subproceso con `--probe`, detectando actividad global con `pynput`.
Si ese subproceso falla (p.ej. permisos en macOS), la app principal no se ve afectada.

---

## Versión JavaScript (Electron)

### Requisitos

- [Node.js](https://nodejs.org/) 18 o posterior
- npm

### Instalar y ejecutar

```bash
cd electron
npm install
npm start
```

### Estructura

```
electron/
├── main.js       — lógica del generador y monitor de actividad
├── preload.js    — puente seguro contextBridge (main ↔ renderer)
├── renderer.js   — lógica de UI y estado
├── index.html    — interfaz completa
└── package.json  — dependencias y scripts
```

### Dependencias

| Paquete | Propósito |
|---|---|
| `electron` | Marco de app de escritorio |
| `@nut-tree-fork/nut-js` | Genera eventos reales del cursor |
| `uiohook-napi` | Detecta actividad global del sistema |

### Personalización

El menú de la aplicación está configurado para ocultarse automáticamente (`autoHideMenuBar: true`). Para mostrarlo temporalmente, presiona la tecla `Alt`. Para eliminarlo completamente, cambia la configuración en `main.js`.

---

## Versión Java

Una sola clase Java, sin dependencias externas. Usa únicamente la JDK estándar:
`Swing` para la UI, `Robot` para generar eventos reales y `AWTEventListener` +
polling de posición del cursor para detectar actividad.

### Requisitos

- JDK 17 o posterior (`java` y `javac` en el PATH)

### Compilar

```bash
cd java
javac ActivityEventGenerator.java
```

### Ejecutar

```bash
cd java
java ActivityEventGenerator
```

### Cómo funciona (Java)

| Componente | API Java usada | Equivalente Python |
|---|---|---|
| Interfaz gráfica | `Swing` (JFrame, JPanel, JTable…) | `tkinter` |
| Generar eventos reales | `java.awt.Robot` | `pyautogui` |
| Detectar actividad global | `AWTEventListener` + polling `MouseInfo` | `pynput` |
| Animación gatito | `javax.swing.Timer` | `after()` de tkinter |
| Hilos / tareas periódicas | `ScheduledExecutorService` | `threading.Thread` |

**Flujo del temporizador inteligente:**
1. Un `ScheduledExecutorService` corre un polling cada 500 ms comparando la posición del cursor.
2. Un `AWTEventListener` captura eventos de teclado/mouse dentro de la JVM.
3. Ambos actualizan `lastActivity` (timestamp atómico).
4. Otro hilo compara `now - lastActivity` contra el umbral configurado y dispara `startGenerator()` o `stopGenerator()` según corresponda.

**Failsafe:** antes de cada evento, se verifica si el cursor está en la esquina superior-izquierda (x ≤ 5, y ≤ 5). Si es así, el generador se detiene automáticamente.

### Estructura

```
java/
└── ActivityEventGenerator.java   — clase única, todo incluido
```

---

## Funcionalidades (todas las versiones)

| Función | Descripción |
|---|---|
| Intervalo configurable | Tiempo entre eventos (default: 120 s) |
| Tipo de evento | izquierdo / derecho / central |
| Cantidad | Eventos por disparo (1–10) |
| Solo registrar | Sin acción real en el sistema |
| Inicio automático | Se activa tras N segundos sin actividad (default: 180 s) |
| Auto-detención | Se detiene al detectar actividad del usuario |
| Failsafe | Cursor a esquina superior-izquierda aborta el generador |
| Registro de eventos | Tabla con hora, tipo y detalle |
| Exportar | Guarda el registro como JSON |
| Gatito animado | Indica si el generador está activo 😺 |

---

## Permisos en macOS

En macOS tanto `Robot` (Java) como `pynput` (Python) y `uiohook-napi` (JS) pueden
requerir permisos para controlar el sistema:

1. **Preferencias del Sistema → Privacidad → Accesibilidad** → agregar Terminal o la app.
2. **Preferencias del Sistema → Privacidad → Monitorización de entrada** → agregar Terminal.

Sin permisos, el inicio automático puede no detectar actividad fuera de la ventana,
pero el generador manual funciona siempre.

---

## Estructura del proyecto

```
mac_activity_lab/
├── python/             — versión Python
│   ├── app.py
│   └── requirements.txt
├── electron/           — versión JavaScript
│   ├── main.js
│   ├── preload.js
│   ├── renderer.js
│   ├── index.html
│   └── package.json
├── java/               — versión Java
│   └── ActivityEventGenerator.java
└── README.md           — este archivo
```
