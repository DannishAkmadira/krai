# ─────────────────────────────────────────────
#  network/camera_stream.py
#  Membaca MJPEG stream dari ESP32-CAM via OpenCV
#  dan menyediakan frame terbaru untuk ditampilkan di GUI
# ─────────────────────────────────────────────

import cv2
import threading
import time
import numpy as np
from PIL import Image, ImageTk
from config import CAMERA_URL, CAMERA_FPS_TARGET, CAMERA_WIDTH, CAMERA_HEIGHT


class CameraStream:
    """
    Membaca stream MJPEG dari ESP32-CAM di background thread.
    GUI tinggal panggil get_frame() untuk ambil frame terbaru.

    Contoh pakai:
        cam = CameraStream(on_status=update_label)
        cam.start("http://192.168.4.1:81/stream")
        ...
        frame = cam.get_frame()   # ImageTk.PhotoImage atau None
        cam.stop()
    """

    def __init__(self, on_status=None, on_fps=None):
        """
        on_status : callback(str)  — dipanggil saat status berubah (connect/error/stop)
        on_fps    : callback(float) — dipanggil tiap detik dengan nilai FPS aktual
        """
        self._cap           = None
        self._thread        = None
        self._stop_event    = threading.Event()
        self._lock          = threading.Lock()

        self._latest_frame  = None      # ImageTk.PhotoImage (siap tampil)
        self._raw_frame     = None      # numpy BGR array (untuk proses lain)

        self.running        = False
        self.url            = ""

        self._on_status     = on_status
        self._on_fps        = on_fps

        self._frame_count   = 0
        self._fps_actual    = 0.0
        self._last_fps_time = time.time()

        # delay antar frame agar tidak terlalu cepat
        self._frame_delay   = 1.0 / max(1, CAMERA_FPS_TARGET)

    # ── PUBLIC API ────────────────────────────────────────

    def start(self, url: str = ""):
        """Mulai stream dari URL. Kalau kosong, pakai CAMERA_URL dari config."""
        if self.running:
            return

        self.url = url or CAMERA_URL
        self._stop_event.clear()
        self.running = True

        self._thread = threading.Thread(
            target=self._stream_loop, daemon=True, name="CameraStreamThread"
        )
        self._thread.start()
        self._status(f"Menghubungkan ke {self.url} ...")

    def stop(self):
        """Hentikan stream."""
        self._stop_event.set()
        self.running = False
        self._status("Stream dihentikan.")

        # beri waktu thread berhenti
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

        with self._lock:
            self._latest_frame = None
            self._raw_frame    = None

        if self._cap:
            self._cap.release()
            self._cap = None

    def get_frame(self) -> "ImageTk.PhotoImage | None":
        """
        Ambil frame terbaru sebagai ImageTk.PhotoImage.
        Return None jika belum ada frame.
        Thread-safe.
        """
        with self._lock:
            return self._latest_frame

    def get_raw_frame(self) -> "np.ndarray | None":
        """
        Ambil frame terbaru sebagai numpy array BGR.
        Berguna kalau mau proses lebih lanjut (deteksi objek, dsb).
        """
        with self._lock:
            return self._raw_frame.copy() if self._raw_frame is not None else None

    def save_snapshot(self, path: str) -> bool:
        """
        Simpan frame saat ini sebagai file gambar.
        path: misal 'snapshot.jpg'
        Return True jika berhasil.
        """
        raw = self.get_raw_frame()
        if raw is None:
            return False
        try:
            cv2.imwrite(path, raw)
            return True
        except Exception:
            return False

    @property
    def fps(self) -> float:
        return self._fps_actual

    # ── INTERNAL STREAM LOOP ──────────────────────────────

    def _stream_loop(self):
        retry_delay = 2     # detik antar retry
        max_retries = 5
        retries     = 0

        while not self._stop_event.is_set():
            # ── buka koneksi ──
            self._status("Membuka koneksi kamera...")
            cap = cv2.VideoCapture(self.url)

            if not cap.isOpened():
                retries += 1
                self._status(f"Gagal buka stream. Retry {retries}/{max_retries}...")
                if retries >= max_retries:
                    self._status("Stream gagal setelah beberapa percobaan. Berhenti.")
                    self.running = False
                    break
                self._stop_event.wait(retry_delay)
                continue

            self._cap = cap
            retries   = 0
            self._status("Stream aktif ✓")
            self._last_fps_time = time.time()
            self._frame_count   = 0

            # ── baca frame ──
            while not self._stop_event.is_set():
                t_start = time.time()

                ret, frame = cap.read()

                if not ret or frame is None:
                    self._status("Frame kosong — mencoba reconnect...")
                    break   # keluar ke loop luar untuk reconnect

                # resize jika perlu
                frame = self._resize(frame)

                # simpan raw (BGR)
                # konversi ke RGB untuk PIL
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                tk_img  = ImageTk.PhotoImage(image=pil_img)

                with self._lock:
                    self._latest_frame = tk_img
                    self._raw_frame    = frame

                # hitung FPS
                self._frame_count += 1
                now = time.time()
                if now - self._last_fps_time >= 1.0:
                    self._fps_actual    = self._frame_count / (now - self._last_fps_time)
                    self._frame_count   = 0
                    self._last_fps_time = now
                    if self._on_fps:
                        self._on_fps(round(self._fps_actual, 1))

                # throttle FPS
                elapsed = time.time() - t_start
                sleep   = self._frame_delay - elapsed
                if sleep > 0:
                    time.sleep(sleep)

            cap.release()
            self._cap = None

            if not self._stop_event.is_set():
                self._status(f"Reconnect dalam {retry_delay} detik...")
                self._stop_event.wait(retry_delay)

        self.running = False

    # ── HELPERS ──────────────────────────────────────────

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        """Resize frame ke ukuran target dari config jika berbeda."""
        h, w = frame.shape[:2]
        target_w, target_h = CAMERA_WIDTH, CAMERA_HEIGHT
        if w != target_w or h != target_h:
            frame = cv2.resize(frame, (target_w, target_h),
                               interpolation=cv2.INTER_LINEAR)
        return frame

    def _status(self, msg: str):
        """Panggil callback status (thread-safe karena hanya baca)."""
        if self._on_status:
            try:
                self._on_status(msg)
            except Exception:
                pass