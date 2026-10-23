#!/usr/bin/env python3
"""Mac Activity Lab: interfaz educativa para temporizadores y registro de eventos.

Genera clics reales del mouse en la posición actual del cursor según el intervalo
configurado. Requiere pyautogui (`pip install pyautogui`).
"""
from __future__ import annotations

import json
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk, filedialog

try:
    import pyautogui
    pyautogui.FAILSAFE = True   # mover mouse a esquina superior-izquierda aborta
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

APP_NAME = "Mac Activity Lab"

# Tipos de clic disponibles para pyautogui
CLICK_BUTTONS = ["left", "right", "middle"]


class ActivityLab(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("760x520")
        self.minsize(650, 440)

        self.events: list[dict] = []
        self.messages: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.started_at: float | None = None
        self.event_count = 0

        self.interval_var = tk.StringVar(value="60")
        self.event_type_var = tk.StringVar(value="Clic real del mouse")
        self.click_button_var = tk.StringVar(value="left")
        self.click_count_var = tk.StringVar(value="1")
        self.status_var = tk.StringVar(value="Detenido")
        self.counter_var = tk.StringVar(value="Eventos registrados: 0")
        self.elapsed_var = tk.StringVar(value="Tiempo: 00:00:00")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._drain_messages)
        self.after(1000, self._update_elapsed)

    def _build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text=APP_NAME, font=("Helvetica", 20, "bold")).pack(anchor="w")
        ttk.Label(
            root,
            text="Laboratorio local de temporizadores y eventos simulados · sin integración con Teams",
            wraplength=700,
        ).pack(anchor="w", pady=(4, 14))

        settings = ttk.LabelFrame(root, text="Configuración", padding=12)
        settings.pack(fill="x")

        ttk.Label(settings, text="Intervalo (segundos):").grid(row=0, column=0, sticky="w")
        interval = ttk.Spinbox(
            settings, from_=1, to=86400, increment=1, width=10,
            textvariable=self.interval_var
        )
        interval.grid(row=0, column=1, padx=(8, 18), sticky="w")

        ttk.Label(settings, text="Acción:").grid(row=0, column=2, sticky="w")
        event_type = ttk.Combobox(
            settings,
            textvariable=self.event_type_var,
            values=[
                "Clic real del mouse",
                "Solo registrar (sin clic)",
            ],
            state="readonly",
            width=24,
        )
        event_type.grid(row=0, column=3, padx=(8, 0), sticky="w")

        # Fila 1: configuración del botón y número de clics
        ttk.Label(settings, text="Botón:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        click_button = ttk.Combobox(
            settings,
            textvariable=self.click_button_var,
            values=CLICK_BUTTONS,
            state="readonly",
            width=10,
        )
        click_button.grid(row=1, column=1, padx=(8, 18), sticky="w", pady=(8, 0))

        ttk.Label(settings, text="Nº de clics:").grid(row=1, column=2, sticky="w", pady=(8, 0))
        click_count = ttk.Spinbox(
            settings, from_=1, to=10, increment=1, width=6,
            textvariable=self.click_count_var,
        )
        click_count.grid(row=1, column=3, padx=(8, 0), sticky="w", pady=(8, 0))

        if not PYAUTOGUI_AVAILABLE:
            ttk.Label(
                settings,
                text="⚠  pyautogui no está instalado — ejecuta: pip install pyautogui",
                foreground="#cc0000",
            ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))

        controls = ttk.Frame(root)
        controls.pack(fill="x", pady=12)
        self.start_button = ttk.Button(controls, text="Iniciar", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(controls, text="Detener", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Exportar registro…", command=self.export_log).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Limpiar", command=self.clear_log).pack(side="left", padx=(8, 0))

        summary = ttk.Frame(root)
        summary.pack(fill="x", pady=(0, 8))
        ttk.Label(summary, text="Estado:").pack(side="left")
        ttk.Label(summary, textvariable=self.status_var, font=("Helvetica", 10, "bold")).pack(side="left", padx=(5, 20))
        ttk.Label(summary, textvariable=self.counter_var).pack(side="left", padx=(0, 20))
        ttk.Label(summary, textvariable=self.elapsed_var).pack(side="left")

        log_frame = ttk.LabelFrame(root, text="Registro local", padding=8)
        log_frame.pack(fill="both", expand=True)
        columns = ("time", "event", "detail")
        self.tree = ttk.Treeview(log_frame, columns=columns, show="headings", height=12)
        self.tree.heading("time", text="Hora")
        self.tree.heading("event", text="Evento")
        self.tree.heading("detail", text="Detalle")
        self.tree.column("time", width=150, stretch=False)
        self.tree.column("event", width=190, stretch=False)
        self.tree.column("detail", width=340, stretch=True)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(
            root,
            text="Seguridad: mueve el mouse a la esquina superior-izquierda de la pantalla para abortar (failsafe de pyautogui).",
            foreground="#666666",
            wraplength=700,
        ).pack(anchor="w", pady=(10, 0))

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            interval = int(self.interval_var.get())
            if not 1 <= interval <= 86400:
                raise ValueError
        except ValueError:
            messagebox.showerror("Intervalo inválido", "Introduce un número entero entre 1 y 86400 segundos.")
            return

        self.stop_event.clear()
        self.started_at = time.monotonic()
        self.status_var.set("En ejecución")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._record("Inicio", f"Temporizador configurado a {interval} s · acción: {self.event_type_var.get()}")
        self.worker = threading.Thread(target=self._run_timer, args=(interval,), daemon=True)
        self.worker.start()

    def _run_timer(self, interval: int):
        while not self.stop_event.wait(interval):
            self.messages.put(("tick", self.event_type_var.get()))

    def stop(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
        self.status_var.set("Detenido")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._record("Detención", "Temporizador detenido por el usuario")

    def _drain_messages(self):
        try:
            while True:
                kind, value = self.messages.get_nowait()
                if kind == "tick":
                    self._handle_tick(value)
        except queue.Empty:
            pass
        self.after(100, self._drain_messages)

    def _handle_tick(self, action: str):
        """Ejecuta la acción configurada y la registra."""
        if action == "Clic real del mouse" and PYAUTOGUI_AVAILABLE:
            try:
                btn = self.click_button_var.get()
                clicks = int(self.click_count_var.get())
                x, y = pyautogui.position()
                pyautogui.click(x=x, y=y, button=btn, clicks=clicks)
                detail = f"Clic {btn} ×{clicks} en ({x}, {y})"
            except Exception as exc:
                detail = f"Error al hacer clic: {exc}"
            self._record("Clic real del mouse", detail)
        elif action == "Clic real del mouse" and not PYAUTOGUI_AVAILABLE:
            self._record("Clic (sin efecto)", "pyautogui no instalado — instala con: pip install pyautogui")
        else:
            self._record(action, "Evento registrado sin acción en el sistema")

    def _record(self, event: str, detail: str):
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        item = {"timestamp": stamp, "event": event, "detail": detail}
        self.events.append(item)
        self.event_count += 1
        self.tree.insert("", "end", values=(stamp, event, detail))
        self.tree.yview_moveto(1)
        self.counter_var.set(f"Eventos registrados: {self.event_count}")

    def _update_elapsed(self):
        if self.started_at is not None and self.status_var.get() == "En ejecución":
            seconds = int(time.monotonic() - self.started_at)
            h, rem = divmod(seconds, 3600)
            m, s = divmod(rem, 60)
            self.elapsed_var.set(f"Tiempo: {h:02d}:{m:02d}:{s:02d}")
        self.after(1000, self._update_elapsed)

    def export_log(self):
        if not self.events:
            messagebox.showinfo("Sin eventos", "Todavía no hay eventos para exportar.")
            return
        path = filedialog.asksaveasfilename(
            title="Exportar registro",
            defaultextension=".json",
            filetypes=[("Archivo JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialfile="mac_activity_lab_log.json",
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.events, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Error al exportar", str(exc))
            return
        messagebox.showinfo("Exportación completada", f"Registro guardado en:\n{path}")

    def clear_log(self):
        if self.status_var.get() == "En ejecución":
            messagebox.showwarning("Temporizador activo", "Detén el temporizador antes de limpiar el registro.")
            return
        self.events.clear()
        self.event_count = 0
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.counter_var.set("Eventos registrados: 0")
        self.elapsed_var.set("Tiempo: 00:00:00")
        self.started_at = None

    def _on_close(self):
        self.stop_event.set()
        self.destroy()


if __name__ == "__main__":
    ActivityLab().mainloop()
