# ─────────────────────────────────────────────
#  gui/panel_control.py
#  Widget kontrol gerak robot:
#  - Tombol WASD (klik mouse & keyboard)
#  - Slider + scroll wheel untuk kecepatan
# ─────────────────────────────────────────────

import tkinter as tk
from config import (
    PANEL, BORDER, ACCENT, ACCENT2, GREEN, YELLOW,
    TEXTDIM, BG, WHITE, FONT_FAMILY
)


class PanelControl(tk.Frame):
    """
    Widget panel kontrol gerak robot.

    Callback:
        on_command(key: str)   — dipanggil saat tombol gerak ditekan/dilepas
                                 key: 'w' | 'a' | 's' | 'd' | 'stop'
        on_speed(value: int)   — dipanggil saat kecepatan berubah (0-255)
    """

    def __init__(self, parent, on_command=None, on_speed=None, **kwargs):
        super().__init__(parent, bg=PANEL, bd=0,
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         **kwargs)
        self._on_command  = on_command
        self._on_speed    = on_speed
        self._active_keys = set()
        self._speed       = tk.IntVar(value=128)

        self._build()
        self._bind_keyboard()

    # ── BUILD ─────────────────────────────────

    def _build(self):
        # ── header ──
        tk.Label(self, text="── KONTROL GERAK  ( W A S D )",
                 bg=PANEL, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8),
                 padx=10, pady=8).pack(anchor="w")

        # ── D-Pad ──
        dpad_frame = tk.Frame(self, bg=PANEL)
        dpad_frame.pack(pady=(0, 8))
        self._build_dpad(dpad_frame)

        # ── separator ──
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=10, pady=4)

        # ── Forklift ──
        tk.Label(self, text="── FORKLIFT  ( Q / E )",
                 bg=PANEL, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8),
                 padx=10, pady=6).pack(anchor="w")

        fork_frame = tk.Frame(self, bg=PANEL)
        fork_frame.pack(pady=(0, 6))
        self._build_forklift(fork_frame)

        # ── separator ──
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=10, pady=4)

        # ── Speed ──
        tk.Label(self, text="── AKSELERASI  ( SCROLL WHEEL )",
                 bg=PANEL, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8),
                 padx=10, pady=6).pack(anchor="w")

        speed_frame = tk.Frame(self, bg=PANEL, padx=12)
        speed_frame.pack(fill="x", pady=(0, 10))
        self._build_speed(speed_frame)

    def _build_dpad(self, parent):
        btn_cfg = dict(
            bg=BORDER, fg=WHITE,
            font=(FONT_FAMILY, 9),
            bd=0, relief="flat",
            activebackground=ACCENT,
            activeforeground=BG,
            width=5, height=2,
            cursor="hand2",
        )

        # baris 0 — maju
        self._btn_w = tk.Button(parent, text="▲\nW", **btn_cfg)
        self._btn_w.grid(row=0, column=1, padx=4, pady=4)

        # baris 1 — kiri, stop, kanan
        self._btn_a = tk.Button(parent, text="◀ A", **btn_cfg)
        self._btn_a.grid(row=1, column=0, padx=4, pady=4)

        self._btn_stop = tk.Button(
            parent, text="■\nSTOP",
            bg="#1a0a0a", fg=ACCENT2,
            font=(FONT_FAMILY, 9),
            bd=0, relief="flat",
            activebackground=ACCENT2,
            activeforeground=BG,
            width=5, height=2,
            cursor="hand2",
            command=self._on_stop_click,
        )
        self._btn_stop.grid(row=1, column=1, padx=4, pady=4)

        self._btn_d = tk.Button(parent, text="D ▶", **btn_cfg)
        self._btn_d.grid(row=1, column=2, padx=4, pady=4)

        # baris 2 — mundur
        self._btn_s = tk.Button(parent, text="▼\nS", **btn_cfg)
        self._btn_s.grid(row=2, column=1, padx=4, pady=4)

        # bind klik mouse ke tiap tombol
        self._dpad_map = {
            "w": self._btn_w,
            "a": self._btn_a,
            "s": self._btn_s,
            "d": self._btn_d,
        }
        for key, btn in self._dpad_map.items():
            btn.bind("<ButtonPress-1>",   lambda e, k=key: self._on_btn_press(k))
            btn.bind("<ButtonRelease-1>", lambda e, k=key: self._on_btn_release(k))

    def _build_forklift(self, parent):
        fork_cfg = dict(
            bg=BORDER, fg=WHITE,
            font=(FONT_FAMILY, 9),
            bd=0, relief="flat",
            activebackground=YELLOW,
            activeforeground=BG,
            width=8, height=2,
            cursor="hand2",
        )

        # tombol naik
        self._btn_lift_up = tk.Button(parent, text="▲  UP\n( Q )", **fork_cfg)
        self._btn_lift_up.grid(row=0, column=0, padx=6, pady=4)

        # tombol stop forklift
        self._btn_lift_stop = tk.Button(
            parent, text="■\nHOLD",
            bg="#0a0a1a", fg=YELLOW,
            font=(FONT_FAMILY, 9),
            bd=0, relief="flat",
            activebackground=YELLOW,
            activeforeground=BG,
            width=5, height=2,
            cursor="hand2",
            command=lambda: self._fire_command("lift_stop"),
        )
        self._btn_lift_stop.grid(row=0, column=1, padx=6, pady=4)

        # tombol turun
        self._btn_lift_down = tk.Button(parent, text="▼  DOWN\n( E )", **fork_cfg)
        self._btn_lift_down.grid(row=0, column=2, padx=6, pady=4)

        # map forklift
        self._fork_map = {
            "lift_up":   self._btn_lift_up,
            "lift_down": self._btn_lift_down,
        }
        for key, btn in self._fork_map.items():
            btn.bind("<ButtonPress-1>",   lambda e, k=key: self._on_fork_press(k))
            btn.bind("<ButtonRelease-1>", lambda e, k=key: self._on_fork_release(k))

    def _build_speed(self, parent):
        # angka kecepatan besar
        top = tk.Frame(parent, bg=PANEL)
        top.pack(fill="x")

        self._speed_lbl = tk.Label(
            top, text="128",
            bg=PANEL, fg=ACCENT,
            font=(FONT_FAMILY, 26, "bold"),
        )
        self._speed_lbl.pack(side="left", padx=(0, 12))

        info = tk.Frame(top, bg=PANEL)
        info.pack(side="left", fill="x", expand=True)

        tk.Label(info, text="SPEED  (0 – 255)",
                 bg=PANEL, fg=TEXTDIM,
                 font=(FONT_FAMILY, 7)).pack(anchor="w")

        # bar visual
        self._bar_canvas = tk.Canvas(
            info, height=18, bg=BORDER,
            highlightthickness=0
        )
        self._bar_canvas.pack(fill="x", pady=(4, 6))

        # slider
        tk.Scale(
            info,
            from_=0, to=255,
            orient="horizontal",
            variable=self._speed,
            bg=PANEL, fg=TEXTDIM,
            troughcolor=BORDER,
            activebackground=ACCENT,
            highlightthickness=0,
            bd=0, showvalue=0,
            command=self._on_speed_change,
        ).pack(fill="x")

        # bind scroll wheel ke seluruh panel
        self.bind_all("<MouseWheel>", self._on_scroll)
        self.bind_all("<Button-4>",   self._on_scroll)   # Linux scroll up
        self.bind_all("<Button-5>",   self._on_scroll)   # Linux scroll down

        # gambar bar awal
        self.after(100, lambda: self._draw_bar(128))

    # ── KEYBOARD ──────────────────────────────

    def _bind_keyboard(self):
        # bind ke root window agar bisa tangkap dari mana saja
        self.winfo_toplevel().bind("<KeyPress>",   self._on_key_press)
        self.winfo_toplevel().bind("<KeyRelease>", self._on_key_release)

    def _on_key_press(self, event):
        key = event.keysym.lower()
        if key in ("w", "a", "s", "d") and key not in self._active_keys:
            self._active_keys.add(key)
            self._highlight(key, True)
            self._fire_command(key)
        elif key == "q" and "lift_up" not in self._active_keys:
            self._active_keys.add("lift_up")
            self._highlight_fork("lift_up", True)
            self._fire_command("lift_up")
        elif key == "e" and "lift_down" not in self._active_keys:
            self._active_keys.add("lift_down")
            self._highlight_fork("lift_down", True)
            self._fire_command("lift_down")

    def _on_key_release(self, event):
        key = event.keysym.lower()
        if key in self._active_keys:
            self._active_keys.discard(key)
            self._highlight(key, False)
            if not self._active_keys:
                self._fire_command("stop")
        elif key == "q" and "lift_up" in self._active_keys:
            self._active_keys.discard("lift_up")
            self._highlight_fork("lift_up", False)
            self._fire_command("lift_stop")
        elif key == "e" and "lift_down" in self._active_keys:
            self._active_keys.discard("lift_down")
            self._highlight_fork("lift_down", False)
            self._fire_command("lift_stop")

    # ── MOUSE CLICK ───────────────────────────

    def _on_btn_press(self, key: str):
        self._active_keys.add(key)
        self._highlight(key, True)
        self._fire_command(key)

    def _on_btn_release(self, key: str):
        self._active_keys.discard(key)
        self._highlight(key, False)
        if not self._active_keys:
            self._fire_command("stop")

    def _on_stop_click(self):
        self._active_keys.clear()
        for key in self._dpad_map:
            self._highlight(key, False)
        self._fire_command("stop")

    def _on_fork_press(self, key: str):
        self._active_keys.add(key)
        self._highlight_fork(key, True)
        self._fire_command(key)

    def _on_fork_release(self, key: str):
        self._active_keys.discard(key)
        self._highlight_fork(key, False)
        self._fire_command("lift_stop")

    # ── SCROLL WHEEL ──────────────────────────

    def _on_scroll(self, event):
        if event.num == 4 or (hasattr(event, "delta") and event.delta > 0):
            new_val = min(255, self._speed.get() + 10)
        else:
            new_val = max(0, self._speed.get() - 10)
        self._speed.set(new_val)
        self._on_speed_change(new_val)

    def _on_speed_change(self, val=None):
        v = self._speed.get()
        self._speed_lbl.configure(text=str(v))
        self._draw_bar(v)
        if self._on_speed:
            self._on_speed(v)

    # ── VISUAL HELPERS ────────────────────────

    def _highlight(self, key: str, active: bool):
        btn = self._dpad_map.get(key)
        if btn:
            btn.configure(
                bg=ACCENT if active else BORDER,
                fg=BG     if active else WHITE,
            )

    def _highlight_fork(self, key: str, active: bool):
        btn = self._fork_map.get(key)
        if btn:
            btn.configure(
                bg=YELLOW if active else BORDER,
                fg=BG     if active else WHITE,
            )

    def _draw_bar(self, value: int):
        self._bar_canvas.update_idletasks()
        w = self._bar_canvas.winfo_width()
        h = 18
        self._bar_canvas.delete("all")

        pct   = value / 255
        color = GREEN if pct < 0.5 else YELLOW if pct < 0.8 else ACCENT2
        fill  = int(w * pct)

        # background strip
        self._bar_canvas.create_rectangle(0, 0, w, h, fill=BORDER, outline="")
        # isi bar dengan efek strip
        for i in range(0, fill, 8):
            self._bar_canvas.create_rectangle(
                i, 1, min(i + 5, fill), h - 1,
                fill=color, outline=""
            )

    # ── PUBLIC ────────────────────────────────

    def _fire_command(self, key: str):
        if self._on_command:
            self._on_command(key)

    def set_speed(self, value: int):
        """Set kecepatan dari luar (misal saat load config)."""
        self._speed.set(value)
        self._on_speed_change()

    def get_speed(self) -> int:
        return self._speed.get()

    def disable(self):
        """Nonaktifkan semua tombol (saat tidak terhubung)."""
        for btn in self._dpad_map.values():
            btn.configure(state="disabled", bg="#0d0f12", fg=TEXTDIM)
        self._btn_stop.configure(state="disabled")
        for btn in self._fork_map.values():
            btn.configure(state="disabled", bg="#0d0f12", fg=TEXTDIM)
        self._btn_lift_stop.configure(state="disabled")

    def enable(self):
        """Aktifkan kembali semua tombol."""
        for btn in self._dpad_map.values():
            btn.configure(state="normal", bg=BORDER, fg=WHITE)
        self._btn_stop.configure(state="normal")
        for btn in self._fork_map.values():
            btn.configure(state="normal", bg=BORDER, fg=WHITE)
        self._btn_lift_stop.configure(state="normal")