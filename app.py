#!/usr/bin/env python3
"""Activity Event Generator: genera eventos de actividad según el intervalo configurado."""
from __future__ import annotations

import json
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, filedialog, ttk

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

APP_NAME   = "Activity Event Generator"
EVENT_OPTS = ["izquierdo", "derecho", "central"]   # sin "mouse" ni "click"

# ── Paleta ───────────────────────────────────────────────────────────────────
BG       = "#0f1117"
CARD     = "#1a1d27"
CARD2    = "#22263a"
BORDER   = "#2e3250"
ACCENT   = "#6c63ff"
ACCENT2  = "#00d4aa"
ACCENT3  = "#ff6b6b"
TEXT     = "#e8eaf6"
TEXT_DIM = "#7b82b0"
GREEN    = "#4caf8a"
YELLOW   = "#f5c842"


# ── Componentes ──────────────────────────────────────────────────────────────

class FlatButton(tk.Canvas):
    """Botón con fondo redondeado y efecto hover."""

    def __init__(self, parent, text, command=None, bg=ACCENT, fg=TEXT,
                 hover=None, btn_width=160, btn_height=36, radius=8,
                 font_size=10, **kw):
        parent_bg = BG
        try:
            parent_bg = parent["bg"]
        except Exception:
            pass
        super().__init__(parent, highlightthickness=0,
                         background=parent_bg, **kw)
        self._bw      = btn_width
        self._bh      = btn_height
        self._text    = text
        self._command = command
        self._bg      = bg
        self._fg      = fg
        self._hover   = hover or self._lighten(bg)
        self._radius  = radius
        self._enabled = True
        self._font    = ("Helvetica", font_size, "bold")
        # tamaño fijo: usar tk.Canvas.configure directamente para no llamar al override
        tk.Canvas.configure(self, width=btn_width, height=btn_height,
                            cursor="hand2")
        self._draw(self._bg)
        self.bind("<Enter>",           lambda e: self._on_enter())
        self.bind("<Leave>",           lambda e: self._on_leave())
        self.bind("<ButtonRelease-1>", self._on_click_event)

    def _lighten(self, h: str) -> str:
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        return "#{:02x}{:02x}{:02x}".format(
            min(255, r + 28), min(255, g + 28), min(255, b + 28))

    def _draw(self, fill):
        self.delete("all")
        r, w, h = self._radius, self._bw, self._bh
        for x1, y1, x2, y2, start in [
            (0,     0,     2*r,   2*r,   90),
            (w-2*r, 0,     w,     2*r,   0),
            (0,     h-2*r, 2*r,   h,     180),
            (w-2*r, h-2*r, w,     h,     270),
        ]:
            self.create_arc(x1, y1, x2, y2, start=start, extent=90,
                            fill=fill, outline=fill)
        self.create_rectangle(r, 0,   w-r, h,   fill=fill, outline=fill)
        self.create_rectangle(0, r,   w,   h-r, fill=fill, outline=fill)
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=TEXT_DIM if not self._enabled else self._fg,
                         font=self._font, anchor="center")

    def _on_enter(self):
        if self._enabled:
            self._draw(self._hover)

    def _on_leave(self):
        self._draw(self._bg if self._enabled else BORDER)

    def _on_click_event(self, event):
        """Solo dispara si el cursor está dentro del área visual del botón."""
        if not self._enabled:
            return
        # verificar que el clic cayó dentro del rectángulo del botón
        if 0 <= event.x <= self._bw and 0 <= event.y <= self._bh:
            if self._command:
                self._command()

    def set_state(self, state: str):
        if state == "disabled":
            self._enabled = False
            self._draw(BORDER)
            tk.Canvas.configure(self, cursor="")
        elif state == "normal":
            self._enabled = True
            self._draw(self._bg)
            tk.Canvas.configure(self, cursor="hand2")

    # override configure/config para manejar state= sin romper Canvas
    def configure(self, state=None, **kw):
        if state is not None:
            self.set_state(state)
        if kw:
            tk.Canvas.configure(self, **kw)

    config = configure


class LabeledDropdown(tk.Frame):
    def __init__(self, parent, label, values, variable, width=180, **kw):
        super().__init__(parent, bg=CARD, **kw)
        tk.Label(self, text=label, bg=CARD, fg=TEXT_DIM,
                 font=("Helvetica", 9)).pack(anchor="w")
        btn = tk.Menubutton(
            self, textvariable=variable,
            bg=CARD2, fg=TEXT, relief="flat",
            activebackground=ACCENT, activeforeground=TEXT,
            font=("Helvetica", 10), width=width // 9,
            anchor="w", padx=8,
        )
        menu = tk.Menu(btn, tearoff=False, bg=CARD2, fg=TEXT,
                       activebackground=ACCENT, activeforeground=TEXT,
                       font=("Helvetica", 10), relief="flat", bd=0)
        for v in values:
            menu.add_command(label=v, command=lambda val=v: variable.set(val))
        btn["menu"] = menu
        btn.pack(fill="x", ipady=5)


class LabeledSpinbox(tk.Frame):
    def __init__(self, parent, label, variable, from_=1, to=86400,
                 width=10, **kw):
        super().__init__(parent, bg=CARD, **kw)
        tk.Label(self, text=label, bg=CARD, fg=TEXT_DIM,
                 font=("Helvetica", 9)).pack(anchor="w")
        tk.Spinbox(
            self, from_=from_, to=to, increment=1,
            textvariable=variable, width=width,
            bg=CARD2, fg=TEXT, insertbackground=TEXT,
            buttonbackground=BORDER, relief="flat",
            font=("Helvetica", 10),
        ).pack(fill="x", ipady=5)


class CatAnimation(tk.Label):
    """Gatito ASCII animado: activo cuando el generador corre, estático si no."""

    # Frames del gatito — cada tupla es (línea1, línea2)
    FRAMES_ACTIVE = [
        (" /\\_/\\ ", "( ^ω^ )ﾉ"),
        (" /\\_/\\ ", "( ^ω^ )~"),
        (" /\\_/\\ ", "( >ω< )ﾉ"),
        (" /\\_/\\ ", "( ^ω^ )♪"),
        (" /\\_/\\ ", "( ≧ω≦)ﾉ"),
        (" /\\_/\\ ", "( ^ω^ )~"),
    ]
    FRAME_IDLE = (" /\\_/\\ ", "( -ω- )zzz")

    INTERVAL_MS = 280   # velocidad de animación

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, fg=ACCENT2,
                         font=("Courier", 11, "bold"),
                         justify="left", **kw)
        self._active     = False
        self._frame_idx  = 0
        self._after_id: str | None = None
        self._render_idle()

    def _render(self, top: str, bot: str):
        self.configure(text=f"{top}\n{bot}")

    def _render_idle(self):
        t, b = self.FRAME_IDLE
        self._render(t, b)

    def _tick(self):
        if not self._active:
            return
        frame = self.FRAMES_ACTIVE[self._frame_idx % len(self.FRAMES_ACTIVE)]
        self._render(*frame)
        self._frame_idx += 1
        self._after_id = self.after(self.INTERVAL_MS, self._tick)

    def set_active(self, active: bool):
        self._active = active
        if active:
            self._frame_idx = 0
            self._tick()
        else:
            if self._after_id:
                self.after_cancel(self._after_id)
                self._after_id = None
            self._render_idle()


class StatBadge(tk.Frame):
    def __init__(self, parent, label, variable, value_color=TEXT, **kw):
        super().__init__(parent, bg=CARD2, padx=16, pady=8, **kw)
        tk.Label(self, text=label, bg=CARD2, fg=TEXT_DIM,
                 font=("Helvetica", 8)).pack(anchor="w")
        tk.Label(self, textvariable=variable, bg=CARD2, fg=value_color,
                 font=("Helvetica", 15, "bold")).pack(anchor="w")


# ── App principal ─────────────────────────────────────────────────────────────

class ActivityLab(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("860x620")
        self.minsize(720, 520)
        self.configure(bg=BG)

        # estado
        self.events: list[dict]           = []
        self.messages: queue.Queue        = queue.Queue()
        self.stop_event                   = threading.Event()
        self.worker: threading.Thread | None = None
        self.started_at: float | None     = None
        self.last_tick_at: float | None   = None
        self.current_interval: int        = 60
        self.event_count                  = 0

        # variables UI
        self.interval_var   = tk.StringVar(value="60")
        self.event_type_var = tk.StringVar(value="Generar evento")
        self.event_opt_var  = tk.StringVar(value="izquierdo")
        self.quantity_var   = tk.StringVar(value="1")
        self.status_var     = tk.StringVar(value="Inactivo")
        self.counter_var    = tk.StringVar(value="0")
        self.elapsed_var    = tk.StringVar(value="00:00:00")
        self.countdown_var  = tk.StringVar(value="--:--")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100,  self._drain_messages)
        self.after(1000, self._update_elapsed)

    # ── construcción UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        outer = tk.Frame(self, bg=BG, padx=22, pady=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)   # fila del log crece

        # ── Encabezado ────────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg=BG)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 16))

        dot = tk.Canvas(hdr, width=12, height=12, bg=BG, highlightthickness=0)
        dot.create_oval(1, 1, 11, 11, fill=ACCENT, outline="")
        dot.pack(side="left", padx=(0, 10), pady=4)

        tk.Label(hdr, text=APP_NAME, bg=BG, fg=TEXT,
                 font=("Helvetica", 20, "bold")).pack(side="left")
        self._cat = CatAnimation(hdr)
        self._cat.pack(side="left", padx=(16, 0))

        # ── Tarjeta de configuración ──────────────────────────────────────────
        card = tk.Frame(outer, bg=CARD, padx=18, pady=14)
        card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for i in range(4):
            card.columnconfigure(i, weight=1)

        tk.Label(card, text="Configuración del evento", bg=CARD, fg=ACCENT,
                 font=("Helvetica", 10, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

        LabeledSpinbox(card, "Intervalo (segundos)", self.interval_var,
                       from_=1, to=86400, width=10).grid(
            row=1, column=0, sticky="ew", padx=(0, 14))

        LabeledDropdown(card, "Acción al disparar",
                        ["Generar evento", "Solo registrar (sin acción)"],
                        self.event_type_var, width=200).grid(
            row=1, column=1, sticky="ew", padx=(0, 14))

        LabeledDropdown(card, "Tipo de evento", EVENT_OPTS,
                        self.event_opt_var, width=130).grid(
            row=1, column=2, sticky="ew", padx=(0, 14))

        LabeledSpinbox(card, "Cantidad", self.quantity_var,
                       from_=1, to=10, width=6).grid(
            row=1, column=3, sticky="ew")

        if not PYAUTOGUI_AVAILABLE:
            tk.Label(card,
                     text="⚠  pyautogui no instalado — ejecuta: pip install pyautogui",
                     bg=CARD, fg=YELLOW, font=("Helvetica", 9)).grid(
                row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))

        # ── Botones ───────────────────────────────────────────────────────────
        btn_row = tk.Frame(outer, bg=BG)
        btn_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))

        self.start_button = FlatButton(
            btn_row, "▶  Iniciar generador",
            command=self.start, bg=ACCENT, btn_width=190, btn_height=38)
        self.start_button.pack(side="left")

        self.stop_button = FlatButton(
            btn_row, "⏹  Detener",
            command=self.stop, bg=ACCENT3, btn_width=130, btn_height=38)
        self.stop_button.pack(side="left", padx=(10, 0))
        self.stop_button.configure(state="disabled")

        FlatButton(btn_row, "Exportar…", command=self.export_log,
                   bg=BORDER, btn_width=110, btn_height=38).pack(
            side="left", padx=(10, 0))

        FlatButton(btn_row, "Limpiar", command=self.clear_log,
                   bg=BORDER, btn_width=100, btn_height=38).pack(
            side="left", padx=(10, 0))

        # ── Badges de estado ──────────────────────────────────────────────────
        badges = tk.Frame(outer, bg=BG)
        badges.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        badges.columnconfigure((0, 1, 2, 3), weight=1)

        self._status_badge = tk.Label(
            badges, textvariable=self.status_var,
            bg=BORDER, fg=TEXT_DIM,
            font=("Helvetica", 10, "bold"),
            padx=16, pady=8, anchor="center",
        )
        self._status_badge.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        StatBadge(badges, "Eventos generados", self.counter_var,
                  value_color=ACCENT).grid(row=0, column=1, sticky="ew", padx=(0, 8))

        StatBadge(badges, "Tiempo transcurrido", self.elapsed_var,
                  value_color=TEXT).grid(row=0, column=2, sticky="ew", padx=(0, 8))

        StatBadge(badges, "Próximo evento en", self.countdown_var,
                  value_color=ACCENT2).grid(row=0, column=3, sticky="ew")

        # ── Registro (Treeview estilizado) ────────────────────────────────────
        log_card = tk.Frame(outer, bg=CARD)
        log_card.grid(row=4, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

        tk.Label(log_card, text="Registro de eventos generados",
                 bg=CARD, fg=ACCENT,
                 font=("Helvetica", 10, "bold"),
                 padx=14, pady=10, anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="ew")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Log.Treeview",
                        background=CARD,
                        foreground=TEXT,
                        fieldbackground=CARD,
                        rowheight=26,
                        font=("Helvetica", 9),
                        borderwidth=0)
        style.configure("Log.Treeview.Heading",
                        background=BORDER,
                        foreground=TEXT_DIM,
                        font=("Helvetica", 9, "bold"),
                        relief="flat")
        style.map("Log.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", TEXT)])
        style.map("Log.Treeview.Heading",
                  background=[("active", BORDER)])

        self._tree = ttk.Treeview(
            log_card, style="Log.Treeview",
            columns=("hora", "evento", "detalle"),
            show="headings", selectmode="browse",
        )
        self._tree.heading("hora",    text="Hora")
        self._tree.heading("evento",  text="Evento generado")
        self._tree.heading("detalle", text="Detalle")
        self._tree.column("hora",    width=165, stretch=False, anchor="w")
        self._tree.column("evento",  width=185, stretch=False, anchor="w")
        self._tree.column("detalle", width=100, stretch=True,  anchor="w")
        self._tree.tag_configure("alt", background=CARD2)
        self._tree.tag_configure("acc", foreground=ACCENT2)

        vsb = ttk.Scrollbar(log_card, orient="vertical",
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        style.configure("Vertical.TScrollbar",
                        background=CARD2, troughcolor=CARD,
                        arrowcolor=TEXT_DIM, borderwidth=0)

        self._tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        self._row_index = 0

        # ── Pie ───────────────────────────────────────────────────────────────
        tk.Label(outer,
                 text="⚡ Failsafe: lleva el cursor a la esquina superior-izquierda para abortar.",
                 bg=BG, fg=TEXT_DIM, font=("Helvetica", 8)).grid(
            row=5, column=0, sticky="w", pady=(8, 0))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _add_log_row(self, stamp: str, event: str, detail: str):
        tags = []
        if self._row_index % 2 == 1:
            tags.append("alt")
        if "generado" in event.lower():
            tags.append("acc")
        self._tree.insert("", "end", values=(stamp, event, detail),
                          tags=tuple(tags))
        self._tree.yview_moveto(1)
        self._row_index += 1

    # ── lógica ────────────────────────────────────────────────────────────────

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            interval = int(self.interval_var.get())
            if not 1 <= interval <= 86400:
                raise ValueError
        except ValueError:
            messagebox.showerror("Intervalo inválido",
                                 "Introduce un número entero entre 1 y 86400 segundos.")
            return

        self.stop_event.clear()
        self.started_at       = time.monotonic()
        self.last_tick_at     = time.monotonic()
        self.current_interval = interval
        self.status_var.set("Generando eventos")
        self._status_badge.configure(bg=GREEN, fg=BG)
        self._cat.set_active(True)
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._record("Generador iniciado",
                     f"Intervalo: {interval} s · acción: {self.event_type_var.get()}")
        self.worker = threading.Thread(
            target=self._run_timer, args=(interval,), daemon=True)
        self.worker.start()

    def _run_timer(self, interval: int):
        while not self.stop_event.wait(interval):
            self.last_tick_at = time.monotonic()
            self.messages.put(("tick", self.event_type_var.get()))

    def stop(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
        self.status_var.set("Inactivo")
        self._status_badge.configure(bg=BORDER, fg=TEXT_DIM)
        self._cat.set_active(False)
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.countdown_var.set("--:--")
        self._record("Generador detenido", "Detenido por el usuario")

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
        if action == "Generar evento" and PYAUTOGUI_AVAILABLE:
            try:
                btn_map = {"izquierdo": "left", "derecho": "right", "central": "middle"}
                btn     = btn_map.get(self.event_opt_var.get(), "left")
                qty     = int(self.quantity_var.get())
                x, y    = pyautogui.position()
                pyautogui.click(x=x, y=y, button=btn, clicks=qty)
                detail = f"Tipo: {self.event_opt_var.get()} · cantidad: {qty} · posición: ({x}, {y})"
            except pyautogui.FailSafeException:
                self._record("⚡ Failsafe activado", "Generador detenido por failsafe")
                self.stop()
                return
            except Exception as exc:
                detail = f"Error al generar evento: {exc}"
            self._record("Evento generado", detail)
        elif action == "Generar evento" and not PYAUTOGUI_AVAILABLE:
            self._record("Evento (sin efecto)",
                         "pyautogui no instalado — pip install pyautogui")
        else:
            self._record("Evento registrado", "Sin acción en el sistema")

    def _record(self, event: str, detail: str):
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        self.events.append({"timestamp": stamp, "event": event, "detail": detail})
        self.event_count += 1
        self.counter_var.set(str(self.event_count))
        self._add_log_row(stamp, event, detail)

    def _update_elapsed(self):
        if self.started_at is not None and self.status_var.get() == "Generando eventos":
            secs = int(time.monotonic() - self.started_at)
            h, rem = divmod(secs, 3600)
            m, s   = divmod(rem, 60)
            self.elapsed_var.set(f"{h:02d}:{m:02d}:{s:02d}")

            if self.last_tick_at is not None:
                rem2 = max(0, int(self.current_interval -
                                  (time.monotonic() - self.last_tick_at)))
                rm, rs = divmod(rem2, 60)
                self.countdown_var.set(f"{rm:02d}:{rs:02d}")
        self.after(1000, self._update_elapsed)

    def export_log(self):
        if not self.events:
            messagebox.showinfo("Sin eventos", "Todavía no hay eventos para exportar.")
            return
        path = filedialog.asksaveasfilename(
            title="Exportar registro de eventos",
            defaultextension=".json",
            filetypes=[("Archivo JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialfile="activity_event_generator_log.json",
        )
        if not path:
            return
        try:
            Path(path).write_text(
                json.dumps(self.events, indent=2, ensure_ascii=False),
                encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Error al exportar", str(exc))
            return
        messagebox.showinfo("Exportación completada", f"Registro guardado en:\n{path}")

    def clear_log(self):
        if self.status_var.get() == "Generando eventos":
            messagebox.showwarning("Generador activo",
                                   "Detén el generador antes de limpiar el registro.")
            return
        self.events.clear()
        self.event_count  = 0
        self._row_index   = 0
        self.counter_var.set("0")
        self.elapsed_var.set("00:00:00")
        self.countdown_var.set("--:--")
        self.started_at   = None
        self.last_tick_at = None
        self._tree.delete(*self._tree.get_children())

    def _on_close(self):
        self.stop_event.set()
        self.destroy()


if __name__ == "__main__":
    ActivityLab().mainloop()
