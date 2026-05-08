# ─────────────────────────────────────────────
#  gui/panel_log.py
#  Widget log komunikasi — menampilkan semua
#  event, command TX, dan status koneksi
# ─────────────────────────────────────────────

import tkinter as tk
import time
from config import PANEL, BORDER, ACCENT, ACCENT2, GREEN, YELLOW, TEXTDIM, BG, FONT_FAMILY


# ── TAG / LEVEL ───────────────────────────────
# Setiap log punya level yang menentukan warnanya
LEVELS = {
    "ok"  : GREEN,    # koneksi sukses, operasi berhasil
    "err" : ACCENT2,  # error, koneksi gagal
    "cmd" : ACCENT,   # command TX ke ESP32
    "warn": YELLOW,   # peringatan (baterai rendah, dll)
    "dim" : TEXTDIM,  # info biasa, heartbeat, dsb
}

MAX_LINES = 200   # batas maksimal baris sebelum dibersihkan


class PanelLog(tk.Frame):
    """
    Widget panel log komunikasi.
    Pakai: panel_log.log("pesan", "ok" | "err" | "cmd" | "warn" | "dim")
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=PANEL, bd=0,
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         **kwargs)
        self._build()

    # ── BUILD ─────────────────────────────────

    def _build(self):
        # ── header ──
        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x", padx=10, pady=(8, 0))

        tk.Label(header, text="── LOG KOMUNIKASI",
                 bg=PANEL, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8)).pack(side="left")

        self._btn_clear = tk.Button(
            header, text="[ CLEAR ]",
            bg=PANEL, fg=TEXTDIM,
            font=(FONT_FAMILY, 7),
            bd=0, relief="flat",
            activebackground=BORDER,
            activeforeground=ACCENT,
            cursor="hand2",
            command=self.clear
        )
        self._btn_clear.pack(side="right")

        # ── text box + scrollbar ──
        box_frame = tk.Frame(self, bg=PANEL)
        box_frame.pack(fill="both", expand=True, padx=6, pady=(4, 6))

        scrollbar = tk.Scrollbar(box_frame, bg=BORDER,
                                 troughcolor=BG, bd=0,
                                 highlightthickness=0)
        scrollbar.pack(side="right", fill="y")

        self._textbox = tk.Text(
            box_frame,
            bg=BG, fg=TEXTDIM,
            font=(FONT_FAMILY, 8),
            bd=0, padx=6, pady=4,
            state="disabled",
            wrap="word",
            yscrollcommand=scrollbar.set,
            cursor="arrow",
        )
        self._textbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._textbox.yview)

        # daftarkan tag warna
        for tag, color in LEVELS.items():
            self._textbox.tag_config(tag, foreground=color)

        # tag khusus untuk timestamp
        self._textbox.tag_config("ts", foreground="#2d3748")

    # ── PUBLIC API ────────────────────────────

    def log(self, message: str, level: str = "dim"):
        """
        Tambah baris log baru.
        level: 'ok' | 'err' | 'cmd' | 'warn' | 'dim'
        """
        if level not in LEVELS:
            level = "dim"

        ts   = time.strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"

        self._textbox.configure(state="normal")

        # tulis timestamp dengan warna redup
        self._textbox.insert("end", f"[{ts}] ", "ts")
        # tulis pesan dengan warna level
        self._textbox.insert("end", f"{message}\n", level)

        # auto-scroll ke bawah
        self._textbox.see("end")

        # bersihkan kalau terlalu panjang
        total_lines = int(self._textbox.index("end-1c").split(".")[0])
        if total_lines > MAX_LINES:
            self._textbox.delete("1.0", f"{MAX_LINES // 2}.0")

        self._textbox.configure(state="disabled")

    def clear(self):
        """Bersihkan semua isi log."""
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
        self.log("Log dibersihkan.", "dim")

    def log_tx(self, key: str, raw: bytes):
        """Shortcut untuk log command TX ke ESP32."""
        self.log(f"TX → {key.upper()}  [{raw.hex().upper()}]", "cmd")

    def log_ok(self, msg: str):
        self.log(msg, "ok")

    def log_err(self, msg: str):
        self.log(msg, "err")

    def log_warn(self, msg: str):
        self.log(msg, "warn")