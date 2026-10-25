# Activity Event Generator

Aplicación en Python con interfaz gráfica que genera eventos de actividad en la posición actual del cursor según un intervalo configurable.

## Requisitos

- Python 3.10 o posterior
- Tkinter (incluido con la distribución oficial de Python)
- [pyautogui](https://pyautogui.readthedocs.io/)

```bash
pip install pyautogui
# o si usas python3 explícitamente:
pip3 install pyautogui
```

## Ejecutar

```bash
python app.py
# o
python3 app.py
```

## Uso

1. Define el **intervalo** en segundos entre cada evento.
2. Selecciona la **acción al disparar**:
   - **Generar evento**: ejecuta un evento real en la posición actual del cursor.
   - **Solo registrar (sin acción)**: registra el evento sin interactuar con el sistema.
3. Elige el **tipo de evento**: izquierdo, derecho o central.
4. Elige la **cantidad** de eventos por disparo (1–10).
5. Pulsa **Iniciar generador**. Cada vez que se cumpla el intervalo se ejecutará la acción configurada.
6. Pulsa **Detener** cuando termines.
7. Usa **Exportar…** para guardar el historial de eventos como JSON.

## Seguridad (failsafe)

Lleva el cursor a la **esquina superior-izquierda** de la pantalla para abortar la generación de eventos. Es el mecanismo de emergencia de pyautogui.

## Estructura

- `app.py`: interfaz y lógica del generador.
- `README.md`: este archivo.
