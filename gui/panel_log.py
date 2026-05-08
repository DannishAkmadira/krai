# ─────────────────────────────────────────────
#  gui/panel_log.py
#  Widget log komunikasi — menampilkan semua
#  event, command TX, dan status koneksi
#  + auto-save ke file logs/log_YYYYMMDD.txt
# ─────────────────────────────────────────────

import tkinter as tk
import time
import os
import subprocess
import platform
from config import PANEL, BORDER, ACCENT, ACCENT2, GREEN, YELLOW, TEXTDIM, BG, FONT_FAMILY


# ── TAG / LEVEL ───────────────────────────────
LEVELS = {
    "ok"  : GREEN,
    "err" : ACCENT2,
    "cmd" : ACCENT,
    "warn": YELLOW,
    "dim" : TEXTDIM,
}

MAX_LINES  = 200
LOGS_DIR   = "logs"   # folder tempat file log disimpan


class PanelLog(tk.Frame):
    """
    Widget panel log komunikasi.
    Pakai: panel_log.log("pesan", "ok" | "err" | "cmd" | "warn" | "dim")
    Setiap baris otomatis disimpan ke logs/log_YYYYMMDD.txt
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=PANEL, bd=0,
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         **kwargs)
        self._log_file = None
        self._init_log_file()
        self._build()

    # ── LOG FILE ──────────────────────────────

    def _init_log_file(self):
        """Buat folder logs/ dan buka file log hari ini."""
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
            filename = time.strftime("log_%Y%m%d.txt")
            filepath = os.path.join(LOGS_DIR, filename)
            self._log_file = open(filepath, "a", encoding="utf-8")
            self._log_filepath = filepath
            # tulis header sesi baru
            self._log_file.write(
                f"\n{'='*50}\n"
                f"  Sesi dimulai: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{'='*50}\n"
            )
            self._log_file.flush()
        except Exception as e:
            self._log_file = None
            print(f"[panel_log] Gagal buka file log: {e}")

    def _write_to_file(self, ts: str, message: str, level: str):
        """Tulis satu baris ke file log."""
        if self._log_file:
            try:
                self._log_file.write(f"[{ts}] [{level.upper():4}] {message}\n")
                self._log_file.flush()
            except Exception:
                pass

    # ── BUILD ─────────────────────────────────

    def _build(self):
        # ── header ──
        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x", padx=10, pady=(8, 0))

        tk.Label(header, text="── LOG KOMUNIKASI",
                 bg=PANEL, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8)).pack(side="left")

        # tombol export
        tk.Button(
            header, text="[ EXPORT ]",
            bg=PANEL, fg=YELLOW,
            font=(FONT_FAMILY, 7),
            bd=0, relief="flat",
            activebackground=BORDER,
            activeforeground=YELLOW,
            cursor="hand2",
            command=self._open_log_folder,
        ).pack(side="right", padx=(6, 0))

        # tombol clear
        tk.Button(
            header, text="[ CLEAR ]",
            bg=PANEL, fg=TEXTDIM,
            font=(FONT_FAMILY, 7),
            bd=0, relief="flat",
            activebackground=BORDER,
            activeforeground=ACCENT,
            cursor="hand2",
            command=self.clear,
        ).pack(side="right")

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
        self._textbox.tag_config("ts", foreground="#2d3748")

        # info file log
        if self._log_file:
            info = tk.Label(
                self,
                text=f"💾 {self._log_filepath}",
                bg=PANEL, fg="#2d3748",
                font=(FONT_FAMILY, 7),
                padx=8, pady=3,
                anchor="w",
            )
            info.pack(fill="x")

    # ── PUBLIC API ────────────────────────────

    def log(self, message: str, level: str = "dim"):
        """
        Tambah baris log baru.
        level: 'ok' | 'err' | 'cmd' | 'warn' | 'dim'
        """
        if level not in LEVELS:
            level = "dim"

        ts = time.strftime("%H:%M:%S")

        # ── tampil di GUI ──
        self._textbox.configure(state="normal")
        self._textbox.insert("end", f"[{ts}] ", "ts")
        self._textbox.insert("end", f"{message}\n", level)
        self._textbox.see("end")

        total_lines = int(self._textbox.index("end-1c").split(".")[0])
        if total_lines > MAX_LINES:
            self._textbox.delete("1.0", f"{MAX_LINES // 2}.0")

        self._textbox.configure(state="disabled")

        # ── simpan ke file ──
        self._write_to_file(ts, message, level)

    def clear(self):
        """Bersihkan tampilan log di GUI (file log tetap tersimpan)."""
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
        self.log("Log GUI dibersihkan. File log tetap tersimpan.", "dim")

    def _open_log_folder(self):
        """Buka folder logs/ di file explorer."""
        try:
            folder = os.path.abspath(LOGS_DIR)
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":   # macOS
                subprocess.Popen(["open", folder])
            else:                                  # Linux
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            self.log(f"Gagal buka folder: {e}", "err")

    # ── SHORTCUT METHODS ──────────────────────

    def log_tx(self, key: str, raw: bytes):
        self.log(f"TX → {key.upper()}  [{raw.hex().upper()}]", "cmd")

    def log_ok(self, msg: str):
        self.log(msg, "ok")

    def log_err(self, msg: str):
        self.log(msg, "err")

    def log_warn(self, msg: str):
        self.log(msg, "warn")

    # ── CLEANUP ───────────────────────────────

    def destroy(self):
        """Tutup file log saat widget dihancurkan."""
        if self._log_file:
            try:
                self._log_file.write(
                    f"{'='*50}\n"
                    f"  Sesi selesai: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"{'='*50}\n"
                )
                self._log_file.close()
            except Exception:
                pass
        super().destroy()