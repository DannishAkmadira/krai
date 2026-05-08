# ─────────────────────────────────────────────
#  network/robot_client.py
#  Handles TCP connection dan pengiriman command ke ESP32
# ─────────────────────────────────────────────

from __future__ import annotations
import socket
import threading
import time
from config import SOCKET_TIMEOUT, CMD, CMD_SPEED_HEADER


class RobotClient:
    """
    Mengelola koneksi TCP ke ESP32.
    Thread-safe: semua akses socket dilindungi lock.
    """

    def __init__(self, on_disconnect=None):
        self.sock             = None
        self.connected        = False
        self._lock            = threading.Lock()
        self._on_disconnect   = on_disconnect
        self._watchdog_thread = None
        self._stop_watchdog   = threading.Event()

    # ── CONNECT / DISCONNECT ──────────────────

    def connect(self, ip: str, port: int) -> tuple[bool, str]:
        if self.connected:
            return False, "Sudah terhubung."
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SOCKET_TIMEOUT)
            s.connect((ip, int(port)))
            s.settimeout(None)
            with self._lock:
                self.sock      = s
                self.connected = True
            self._start_watchdog()
            return True, f"Terhubung ke {ip}:{port}"
        except socket.timeout:
            return False, "Timeout — ESP32 tidak merespons."
        except ConnectionRefusedError:
            return False, "Koneksi ditolak — cek IP/port ESP32."
        except OSError as e:
            return False, f"Error jaringan: {e}"

    def disconnect(self):
        self._stop_watchdog.set()
        with self._lock:
            self._close_socket()

    def _close_socket(self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock      = None
        self.connected = False

    # ── SEND ─────────────────────────────────

    def send_command(self, key: str) -> bool:
        data = CMD.get(key)
        if data is None:
            return False
        return self._send(data)

    def send_speed(self, value: int) -> bool:
        value = max(0, min(255, int(value)))
        data  = bytes([CMD_SPEED_HEADER, value])
        return self._send(data)

    def _send(self, data: bytes) -> bool:
        with self._lock:
            if not self.connected or self.sock is None:
                return False
            try:
                self.sock.sendall(data)
                return True
            except (BrokenPipeError, ConnectionResetError, OSError):
                self._close_socket()
        self._fire_disconnect()
        return False

    # ── WATCHDOG ─────────────────────────────

    def _start_watchdog(self):
        self._stop_watchdog.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True, name="WatchdogThread"
        )
        self._watchdog_thread.start()

    def _watchdog_loop(self):
        HEARTBEAT = b"\xFE"
        disconnected = False

        while not self._stop_watchdog.wait(2):
            with self._lock:
                if not self.connected:
                    disconnected = True
                    break
                try:
                    self.sock.sendall(HEARTBEAT)
                except Exception:
                    self._close_socket()
                    disconnected = True
                    break

        if disconnected:
            self._fire_disconnect()

    def _fire_disconnect(self):
        if self._on_disconnect:
            try:
                self._on_disconnect()
            except Exception:
                pass

    # ── STATUS ────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self.connected

    def __repr__(self):
        state = "connected" if self.connected else "disconnected"
        return f"<RobotClient {state}>"