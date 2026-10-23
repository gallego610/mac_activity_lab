# Mac Activity Lab

Aplicación en Python con interfaz gráfica que genera clics reales del mouse en la posición actual del cursor según un intervalo configurable.

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

1. Define el **intervalo** en segundos entre cada clic.
2. Selecciona la **acción**:
   - **Clic real del mouse**: ejecuta un clic real en la posición actual del cursor.
   - **Solo registrar (sin clic)**: registra el evento sin tocar el mouse.
3. Elige el **botón** del mouse: `left`, `right` o `middle`.
4. Elige el **nº de clics** por disparo (1–10).
5. Pulsa **Iniciar**. Cada vez que se cumpla el intervalo, se ejecutará la acción configurada.
6. Pulsa **Detener** cuando termines.
7. Usa **Exportar registro…** para guardar el historial de eventos como JSON.

## Seguridad (failsafe)

Mueve el mouse rápidamente a la **esquina superior-izquierda** de la pantalla para abortar cualquier clic en curso. Es el mecanismo de emergencia de pyautogui.

## Estructura

- `app.py`: interfaz y lógica del temporizador.
- `README.md`: este archivo.
