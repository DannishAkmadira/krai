# ─────────────────────────────────────────────
#  gui/app.py
#  Window utama — menggabungkan semua panel
#  dan menghubungkan network layer ke GUI
# ─────────────────────────────────────────────

import tkinter as tk
import threading
from config import (
    BG, PANEL, BORDER, ACCENT, ACCENT2, GREEN, YELLOW,
    TEXTDIM, WHITE, FONT_FAMILY,
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    ESP32_IP, ESP32_PORT, CAMERA_URL,
)
from network.robot_client import RobotClient
from gui.panel_contol import PanelControl
from gui.panel_camera import PanelCamera
from gui.panel_log import PanelLog


class App:
    """
    Kelas utama aplikasi.
    Inisialisasi window, semua panel, dan hubungkan
    network layer (RobotClient) ke callback GUI.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self._setup_window()

        # ── network ──
        self.client = RobotClient(on_disconnect=self._on_robot_disconnect)

        # ── state ──
        self._ip_var   = tk.StringVar(value=ESP32_IP)
        self._port_var = tk.StringVar(value=str(ESP32_PORT))
        self._status   = tk.StringVar(value="OFFLINE")

        # ── build UI ──
        self._build_header()
        self._build_body()
        self._build_statusbar()

        # ── post-init ──
        self.panel_control.disable()
        self.panel_camera.set_url(CAMERA_URL)
        self.log.log("Aplikasi siap. Hubungkan ke ESP32 untuk memulai.", "dim")

    # ── WINDOW SETUP ──────────────────────────

    def _setup_window(self):
        self.root.title(WINDOW_TITLE)
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── HEADER ────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG, pady=0)
        hdr.pack(fill="x", padx=14, pady=(12, 0))

        # judul
        tk.Label(hdr, text="◈ ROBOT CONTROL PANEL",
                 bg=BG, fg=ACCENT,
                 font=(FONT_FAMILY, 11, "bold")).pack(side="left")

        # status dot + teks
        self._status_dot = tk.Label(hdr, text="●", bg=BG, fg=ACCENT2,
                                    font=(FONT_FAMILY, 11))
        self._status_dot.pack(side="right", padx=(4, 0))

        tk.Label(hdr, textvariable=self._status,
                 bg=BG, fg=ACCENT2,
                 font=(FONT_FAMILY, 8)).pack(side="right")

        # separator
        tk.Frame(self.root, bg=BORDER, height=1).pack(
            fill="x", padx=14, pady=6
        )

        # ── baris koneksi ──
        conn = tk.Frame(self.root, bg=BG, padx=14)
        conn.pack(fill="x", pady=(0, 6))

        tk.Label(conn, text="IP :", bg=BG, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8)).pack(side="left")
        tk.Entry(conn, textvariable=self._ip_var,
                 bg=PANEL, fg=ACCENT,
                 font=(FONT_FAMILY, 9),
                 bd=0, insertbackground=ACCENT,
                 width=16).pack(side="left", padx=(4, 12))

        tk.Label(conn, text="PORT :", bg=BG, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8)).pack(side="left")
        tk.Entry(conn, textvariable=self._port_var,
                 bg=PANEL, fg=ACCENT,
                 font=(FONT_FAMILY, 9),
                 bd=0, insertbackground=ACCENT,
                 width=6).pack(side="left", padx=(4, 16))

        self._btn_connect = self._btn(conn, "[ CONNECT ]",
                                      self._on_connect, ACCENT)
        self._btn_connect.pack(side="left")

        self._btn_disconnect = self._btn(conn, "[ DISCONNECT ]",
                                         self._on_disconnect, ACCENT2)
        self._btn_disconnect.pack(side="left", padx=8)

        tk.Frame(self.root, bg=BORDER, height=1).pack(
            fill="x", padx=14, pady=(0, 8)
        )

    # ── BODY ──────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        # ── kolom kiri: kamera ──
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        self.panel_camera = PanelCamera(left)
        self.panel_camera.pack(fill="both", expand=True)
        self.panel_camera.set_snapshot_callback(
            lambda path: self.log.log(f"Snapshot: {path}", "ok")
        )

        # ── kolom kanan: kontrol + log ──
        right = tk.Frame(body, bg=BG, width=300)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        self.panel_control = PanelControl(
            right,
            on_command=self._on_command,
            on_speed=self._on_speed,
        )
        self.panel_control.pack(fill="x")

        self.log = PanelLog(right)
        self.log.pack(fill="both", expand=True, pady=(10, 0))

    # ── STATUS BAR ────────────────────────────

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg=PANEL, height=22,
                       highlightthickness=1,
                       highlightbackground=BORDER)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._bar_text = tk.Label(
            bar, text="Siap.",
            bg=PANEL, fg=TEXTDIM,
            font=(FONT_FAMILY, 7),
            padx=10,
        )
        self._bar_text.pack(side="left", fill="y")

        tk.Label(bar, text=f"v1.0  |  Robot Control Panel",
                 bg=PANEL, fg="#1e2535",
                 font=(FONT_FAMILY, 7),
                 padx=10).pack(side="right", fill="y")

    # ── HELPERS ───────────────────────────────

    def _btn(self, parent, text, cmd, color):
        return tk.Button(
            parent, text=text, command=cmd,
            bg=BG, fg=color,
            font=(FONT_FAMILY, 8),
            bd=0, relief="flat",
            activebackground=color,
            activeforeground=BG,
            cursor="hand2",
        )

    def _set_online(self):
        self._status.set("ONLINE")
        self._status_dot.configure(fg=GREEN)
        self.root.nametowidget(self._status_dot.winfo_parent()).nametowidget(
            self._status_dot.winfo_parent()
        )
        # cari label status dan ubah warnanya
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label) and child.cget("textvariable") == str(self._status):
                        child.configure(fg=GREEN)
        self._status_dot.configure(fg=GREEN)
        self.panel_control.enable()
        self._bar_status("Terhubung ke ESP32.")

    def _set_offline(self):
        self._status.set("OFFLINE")
        self._status_dot.configure(fg=ACCENT2)
        self.panel_control.disable()
        self._bar_status("Tidak terhubung.")

    def _bar_status(self, msg: str):
        self._bar_text.configure(text=msg)

    # ── NETWORK CALLBACKS ─────────────────────

    def _on_connect(self):
        ip   = self._ip_var.get().strip()
        port = self._port_var.get().strip()

        if not ip or not port:
            self.log.log_err("IP dan port tidak boleh kosong.")
            return

        self.log.log(f"Menghubungkan ke {ip}:{port}...", "dim")
        self._bar_status(f"Menghubungkan ke {ip}:{port}...")

        def _do():
            ok, msg = self.client.connect(ip, int(port))
            if ok:
                self.root.after(0, self._set_online)
                self.root.after(0, lambda: self.log.log_ok(msg))
            else:
                self.root.after(0, lambda: self.log.log_err(msg))
                self.root.after(0, lambda: self._bar_status("Koneksi gagal."))

        threading.Thread(target=_do, daemon=True).start()

    def _on_disconnect(self):
        self.client.disconnect()
        self._set_offline()
        self.log.log("Koneksi diputus.", "warn")

    def _on_robot_disconnect(self):
        """Dipanggil watchdog saat koneksi tiba-tiba terputus."""
        self.root.after(0, self._set_offline)
        self.root.after(0, lambda: self.log.log_err("Koneksi ke ESP32 terputus!"))

    # ── COMMAND CALLBACKS ─────────────────────

    def _on_command(self, key: str):
        """Dikirim dari PanelControl saat tombol gerak ditekan."""
        ok = self.client.send_command(key)
        if ok:
            from config import CMD
            raw = CMD.get(key, b"\x00")
            self.log.log_tx(key, raw)
        elif key != "stop":
            self.log.log_err("Gagal kirim command — tidak terhubung.")

    def _on_speed(self, value: int):
        """Dikirim dari PanelControl saat kecepatan berubah."""
        ok = self.client.send_speed(value)
        if ok:
            self.log.log(f"SPD → {value}", "cmd")

    # ── CLOSE ─────────────────────────────────

    def _on_close(self):
        self.client.disconnect()
        self.panel_camera.destroy()
        self.root.destroy()