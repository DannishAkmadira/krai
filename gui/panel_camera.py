# ─────────────────────────────────────────────
#  gui/panel_camera.py
#  Widget tampilan feed kamera dari ESP32-CAM
#  Menerima frame dari CameraStream dan
#  menampilkannya di Canvas tkinter
# ─────────────────────────────────────────────

import tkinter as tk
import time
from config import (
    PANEL, BORDER, ACCENT, ACCENT2, GREEN, YELLOW,
    TEXTDIM, BG, WHITE, FONT_FAMILY,
    CAMERA_WIDTH, CAMERA_HEIGHT
)
from network.camera_stream import CameraStream


# interval refresh tampilan kamera (ms)
REFRESH_MS = 33   # ~30 FPS


class PanelCamera(tk.Frame):
    """
    Widget panel kamera.
    Menampilkan MJPEG stream dari ESP32-CAM secara live.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=PANEL, bd=0,
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         **kwargs)

        self._stream      = CameraStream(
            on_status=self._on_stream_status,
            on_fps=self._on_fps_update,
        )
        self._url         = tk.StringVar()
        self._status_text = tk.StringVar(value="KAMERA OFFLINE")
        self._fps_text    = tk.StringVar(value="-- FPS")
        self._recording   = False
        self._snapshot_cb = None    # callback opsional saat snapshot diambil

        self._build()
        self._start_refresh()

    # ── BUILD ─────────────────────────────────

    def _build(self):
        # ── header ──
        header = tk.Frame(self, bg=PANEL, padx=10, pady=8)
        header.pack(fill="x")

        tk.Label(header, text="── LIVE CAMERA",
                 bg=PANEL, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8)).pack(side="left")

        self._fps_lbl = tk.Label(
            header, textvariable=self._fps_text,
            bg=PANEL, fg=TEXTDIM,
            font=(FONT_FAMILY, 8)
        )
        self._fps_lbl.pack(side="right")

        # ── canvas kamera ──
        self._canvas = tk.Canvas(
            self,
            width=CAMERA_WIDTH,
            height=CAMERA_HEIGHT,
            bg="#050708",
            highlightthickness=0,
            cursor="crosshair",
        )
        self._canvas.pack(padx=8, pady=(0, 6))
        self._draw_placeholder()

        # ── status bar ──
        status_bar = tk.Frame(self, bg=PANEL, padx=10)
        status_bar.pack(fill="x", pady=(0, 6))

        self._dot = tk.Label(status_bar, text="●", bg=PANEL, fg=ACCENT2,
                             font=(FONT_FAMILY, 9))
        self._dot.pack(side="left")

        tk.Label(status_bar, textvariable=self._status_text,
                 bg=PANEL, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8)).pack(side="left", padx=4)

        # ── URL input + tombol ──
        ctrl = tk.Frame(self, bg=PANEL, padx=10, pady=6)
        ctrl.pack(fill="x")

        tk.Label(ctrl, text="URL :", bg=PANEL, fg=TEXTDIM,
                 font=(FONT_FAMILY, 8)).pack(side="left")

        tk.Entry(
            ctrl,
            textvariable=self._url,
            bg=BORDER, fg=ACCENT,
            font=(FONT_FAMILY, 8),
            bd=0, insertbackground=ACCENT,
            width=30,
        ).pack(side="left", padx=6)

        self._btn_start = self._btn(ctrl, "[ START ]", self._on_start, ACCENT)
        self._btn_start.pack(side="left")

        self._btn_stop = self._btn(ctrl, "[ STOP ]", self._on_stop, ACCENT2)
        self._btn_stop.pack(side="left", padx=6)

        self._btn_snap = self._btn(ctrl, "[ SNAPSHOT ]", self._on_snapshot, YELLOW)
        self._btn_snap.pack(side="left")

    def _btn(self, parent, text, cmd, color):
        return tk.Button(
            parent, text=text, command=cmd,
            bg=PANEL, fg=color,
            font=(FONT_FAMILY, 8),
            bd=0, relief="flat",
            activebackground=color,
            activeforeground=BG,
            cursor="hand2",
        )

    # ── PLACEHOLDER ───────────────────────────

    def _draw_placeholder(self):
        """Tampilan saat kamera belum aktif."""
        self._canvas.delete("all")
        cx = CAMERA_WIDTH  // 2
        cy = CAMERA_HEIGHT // 2

        # border garis putus-putus
        self._canvas.create_rectangle(
            20, 20, CAMERA_WIDTH - 20, CAMERA_HEIGHT - 20,
            outline=BORDER, dash=(6, 4), width=1
        )

        # ikon kamera sederhana
        self._canvas.create_rectangle(cx-40, cy-25, cx+40, cy+25,
                                       outline=TEXTDIM, width=2)
        self._canvas.create_oval(cx-15, cy-15, cx+15, cy+15,
                                  outline=TEXTDIM, width=2)
        self._canvas.create_rectangle(cx+25, cy-30, cx+42, cy-18,
                                       outline=TEXTDIM, width=2)

        self._canvas.create_text(
            cx, cy + 55,
            text="NO SIGNAL",
            fill=TEXTDIM,
            font=(FONT_FAMILY, 10, "bold"),
        )
        self._canvas.create_text(
            cx, cy + 75,
            text="Masukkan URL stream lalu tekan START",
            fill="#2d3748",
            font=(FONT_FAMILY, 8),
        )

    # ── STREAM CONTROL ────────────────────────

    def _on_start(self):
        url = self._url.get().strip()
        if not url:
            self._set_status("Masukkan URL stream terlebih dahulu!", ACCENT2)
            return
        self._stream.start(url)
        self._set_status("Menghubungkan...", YELLOW)

    def _on_stop(self):
        self._stream.stop()
        self._draw_placeholder()
        self._fps_text.set("-- FPS")

    def _on_snapshot(self):
        ts   = time.strftime("%Y%m%d_%H%M%S")
        path = f"snapshot_{ts}.jpg"
        ok   = self._stream.save_snapshot(path)
        if ok:
            self._set_status(f"Snapshot disimpan: {path}", GREEN)
            if self._snapshot_cb:
                self._snapshot_cb(path)
        else:
            self._set_status("Snapshot gagal — tidak ada frame.", ACCENT2)

    # ── REFRESH LOOP ──────────────────────────

    def _start_refresh(self):
        """Loop tkinter after() untuk update canvas setiap REFRESH_MS."""
        self._refresh()

    def _refresh(self):
        frame = self._stream.get_frame()
        if frame is not None:
            # simpan referensi agar tidak di-GC oleh Python
            self._current_frame = frame
            self._canvas.configure(width=CAMERA_WIDTH, height=CAMERA_HEIGHT)
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, anchor="nw", image=frame)

        self.after(REFRESH_MS, self._refresh)

    # ── CALLBACKS DARI STREAM ─────────────────

    def _on_stream_status(self, msg: str):
        """Dipanggil oleh CameraStream saat status berubah."""
        # tentukan warna dot berdasarkan isi pesan
        if "aktif" in msg.lower() or "✓" in msg:
            color = GREEN
        elif "gagal" in msg.lower() or "error" in msg.lower():
            color = ACCENT2
        else:
            color = YELLOW

        # update harus di main thread
        self.after(0, lambda: self._set_status(msg, color))

    def _on_fps_update(self, fps: float):
        """Dipanggil oleh CameraStream setiap detik dengan nilai FPS."""
        self.after(0, lambda: self._fps_text.set(f"{fps:.1f} FPS"))

    def _set_status(self, msg: str, color: str = TEXTDIM):
        self._status_text.set(msg)
        self._dot.configure(fg=color)

    # ── PUBLIC ────────────────────────────────

    def set_url(self, url: str):
        """Set URL dari luar (misal dari config atau panel koneksi)."""
        self._url.set(url)

    def set_snapshot_callback(self, cb):
        """Callback dipanggil dengan path file saat snapshot berhasil."""
        self._snapshot_cb = cb

    def destroy(self):
        """Pastikan stream dihentikan saat widget dihancurkan."""
        self._stream.stop()
        super().destroy()