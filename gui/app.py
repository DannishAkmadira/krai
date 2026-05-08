# ─────────────────────────────────────────────
#  gui/app.py
#  Window utama MQTT Version
# ─────────────────────────────────────────────

import tkinter as tk

from config import (
    BG, PANEL, BORDER,
    ACCENT, ACCENT2,
    GREEN, TEXTDIM,
    FONT_FAMILY,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    CAMERA_URL,
    MQTT_HOST,
)

from network.robot_client import RobotClient
from gui.panel_contol import PanelControl
from gui.panel_camera import PanelCamera
from gui.panel_log import PanelLog


class App:

    def __init__(self, root: tk.Tk):

        self.root = root

        self._setup_window()

        # status GUI
        self._status = tk.StringVar(value="OFFLINE")

        # MQTT client
        self.client = RobotClient(
            on_disconnect=self._on_robot_disconnect,
            on_connect=self._on_robot_connect
        )

        # build UI
        self._build_header()
        self._build_body()
        self._build_statusbar()

        # init
        self.panel_control.disable()

        self.panel_camera.set_url(CAMERA_URL)

        self.log.log(
            "Aplikasi siap. Hubungkan ke MQTT broker.",
            "dim"
        )

    # ─────────────────────────────────────────
    # WINDOW
    # ─────────────────────────────────────────

    def _setup_window(self):

        self.root.title(WINDOW_TITLE)

        self.root.configure(bg=BG)

        self.root.resizable(False, False)

        self.root.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self._on_close
        )

    # ─────────────────────────────────────────
    # HEADER
    # ─────────────────────────────────────────

    def _build_header(self):

        hdr = tk.Frame(
            self.root,
            bg=BG
        )

        hdr.pack(
            fill="x",
            padx=14,
            pady=(12, 0)
        )

        tk.Label(
            hdr,
            text="◈ ROBOT CONTROL PANEL",
            bg=BG,
            fg=ACCENT,
            font=(FONT_FAMILY, 11, "bold")
        ).pack(side="left")

        self._status_dot = tk.Label(
            hdr,
            text="●",
            bg=BG,
            fg=ACCENT2,
            font=(FONT_FAMILY, 11)
        )

        self._status_dot.pack(
            side="right",
            padx=(4, 0)
        )

        tk.Label(
            hdr,
            textvariable=self._status,
            bg=BG,
            fg=ACCENT2,
            font=(FONT_FAMILY, 8)
        ).pack(side="right")

        tk.Frame(
            self.root,
            bg=BORDER,
            height=1
        ).pack(
            fill="x",
            padx=14,
            pady=6
        )

        # ── MQTT INFO ──

        conn = tk.Frame(
            self.root,
            bg=BG,
            padx=14
        )

        conn.pack(
            fill="x",
            pady=(0, 6)
        )

        tk.Label(
            conn,
            text=f"MQTT : {MQTT_HOST}",
            bg=BG,
            fg=TEXTDIM,
            font=(FONT_FAMILY, 8)
        ).pack(side="left")

        self._btn_connect = self._btn(
            conn,
            "[ CONNECT ]",
            self._on_connect,
            ACCENT
        )

        self._btn_connect.pack(
            side="left",
            padx=(20, 0)
        )

        self._btn_disconnect = self._btn(
            conn,
            "[ DISCONNECT ]",
            self._on_disconnect,
            ACCENT2
        )

        self._btn_disconnect.pack(
            side="left",
            padx=8
        )

        tk.Frame(
            self.root,
            bg=BORDER,
            height=1
        ).pack(
            fill="x",
            padx=14,
            pady=(0, 8)
        )

    # ─────────────────────────────────────────
    # BODY
    # ─────────────────────────────────────────

    def _build_body(self):

        body = tk.Frame(
            self.root,
            bg=BG
        )

        body.pack(
            fill="both",
            expand=True,
            padx=14,
            pady=(0, 6)
        )

        # kiri
        left = tk.Frame(
            body,
            bg=BG
        )

        left.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.panel_camera = PanelCamera(left)

        self.panel_camera.pack(
            fill="both",
            expand=True
        )

        self.panel_camera.set_snapshot_callback(
            lambda path:
            self.log.log(
                f"Snapshot: {path}",
                "ok"
            )
        )

        # kanan
        right = tk.Frame(
            body,
            bg=BG,
            width=300
        )

        right.pack(
            side="right",
            fill="y",
            padx=(12, 0)
        )

        right.pack_propagate(False)

        self.panel_control = PanelControl(
            right,
            on_command=self._on_command,
            on_speed=self._on_speed,
        )

        self.panel_control.pack(fill="x")

        self.log = PanelLog(right)

        self.log.pack(
            fill="both",
            expand=True,
            pady=(10, 0)
        )

    # ─────────────────────────────────────────
    # STATUS BAR
    # ─────────────────────────────────────────

    def _build_statusbar(self):

        bar = tk.Frame(
            self.root,
            bg=PANEL,
            height=22,
            highlightthickness=1,
            highlightbackground=BORDER
        )

        bar.pack(
            fill="x",
            side="bottom"
        )

        bar.pack_propagate(False)

        self._bar_text = tk.Label(
            bar,
            text="Siap.",
            bg=PANEL,
            fg=TEXTDIM,
            font=(FONT_FAMILY, 7),
            padx=10,
        )

        self._bar_text.pack(
            side="left",
            fill="y"
        )

    # ─────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────

    def _btn(self, parent, text, cmd, color):

        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=BG,
            fg=color,
            font=(FONT_FAMILY, 8),
            bd=0,
            relief="flat",
            activebackground=color,
            activeforeground=BG,
            cursor="hand2",
        )

    def _set_online(self):

        self._status.set("ONLINE")

        self._status_dot.configure(
            fg=GREEN
        )

        self.panel_control.enable()

        self._bar_status(
            "Terhubung ke MQTT Broker."
        )

    def _set_offline(self):

        self._status.set("OFFLINE")

        self._status_dot.configure(
            fg=ACCENT2
        )

        self.panel_control.disable()

        self._bar_status(
            "Tidak terhubung."
        )

    def _bar_status(self, msg):

        self._bar_text.configure(
            text=msg
        )

    # ─────────────────────────────────────────
    # MQTT CALLBACK
    # ─────────────────────────────────────────

    def _on_connect(self):

        self.log.log(
            "Menghubungkan ke MQTT broker...",
            "dim"
        )

        self._bar_status(
            "Menghubungkan..."
        )

        self.client.connect()

    def _on_robot_connect(self, success, msg):

        def _update():

            if success:

                self._set_online()

                self.log.log_ok(msg)

            else:

                self._set_offline()

                self.log.log_err(msg)

        self.root.after(0, _update)

    def _on_disconnect(self):

        self.client.disconnect()

        self._set_offline()

        self.log.log(
            "Koneksi MQTT diputus.",
            "warn"
        )

    def _on_robot_disconnect(self):

        self.root.after(
            0,
            self._set_offline
        )

        self.root.after(
            0,
            lambda:
            self.log.log_err(
                "Koneksi ke broker MQTT terputus!"
            )
        )

    # ─────────────────────────────────────────
    # COMMAND
    # ─────────────────────────────────────────

    def _on_command(self, key):

        ok = self.client.send_command(key)

        if ok:

            self.log.log(
                f"CMD → {key}",
                "cmd"
            )

        elif key != "stop":

            self.log.log_err(
                "Gagal kirim command."
            )

    def _on_speed(self, value):

        ok = self.client.send_speed(value)

        if ok:

            self.log.log(
                f"SPD → {value}",
                "cmd"
            )

    # ─────────────────────────────────────────
    # CLOSE
    # ─────────────────────────────────────────

    def _on_close(self):

        self.client.disconnect()

        self.panel_camera.destroy()

        self.root.destroy()