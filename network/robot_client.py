# ─────────────────────────────────────────────
#  network/robot_client.py
#  Koneksi MQTT ke broker HiveMQ cloud
#  Publish command gerak, speed, dan forklift
# ─────────────────────────────────────────────

from __future__ import annotations
import threading
import paho.mqtt.client as mqtt
from config import (
    MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD,
    MQTT_CLIENT_ID, MQTT_KEEPALIVE,
    TOPIC_MOVE, TOPIC_SPEED, TOPIC_FORKLIFT,
)

# mapping key → topic dan payload
_MOVE_KEYS = {"w", "a", "s", "d", "stop"}
_FORK_KEYS = {"lift_up", "lift_down", "lift_stop"}
_FORK_PAYLOAD = {
    "lift_up":   "up",
    "lift_down": "down",
    "lift_stop": "stop",
}


class RobotClient:
    """
    Mengelola koneksi MQTT ke HiveMQ cloud.
    Publish command ke topic robot/move, robot/speed, robot/forklift.

    Contoh:
        client = RobotClient(on_disconnect=callback)
        client.connect()
        client.send_command("w")
        client.send_speed(200)
        client.send_command("lift_up")
    """

    def __init__(self, on_disconnect=None, on_connect=None):
        """
        on_disconnect : callback() — dipanggil saat koneksi terputus
        on_connect    : callback(success: bool, msg: str) — hasil connect
        """
        self.connected      = False
        self._on_disconnect = on_disconnect
        self._on_connect    = on_connect
        self._lock          = threading.Lock()

        # setup MQTT client dengan TLS
        self._client = mqtt.Client(
            client_id=MQTT_CLIENT_ID,
            protocol=mqtt.MQTTv5,
        )
        self._client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self._client.tls_set()  # TLS wajib untuk HiveMQ cloud port 8883

        # bind callback internal
        self._client.on_connect    = self._on_mqtt_connect
        self._client.on_disconnect = self._on_mqtt_disconnect

    # ── CONNECT / DISCONNECT ──────────────────

    def connect(self) -> None:
        """
        Mulai koneksi ke broker MQTT (non-blocking).
        Hasil koneksi diterima via callback on_connect.
        """
        try:
            self._client.connect(
                MQTT_HOST,
                port=MQTT_PORT,
                keepalive=MQTT_KEEPALIVE,
            )
            self._client.loop_start()   # network loop di background thread
        except Exception as e:
            if self._on_connect:
                self._on_connect(False, f"Gagal konek: {e}")

    def disconnect(self) -> None:
        """Putuskan koneksi dari broker."""
        self._client.loop_stop()
        self._client.disconnect()
        with self._lock:
            self.connected = False

    # ── PUBLISH ───────────────────────────────

    def send_command(self, key: str) -> bool:
        """
        Kirim command gerak atau forklift.
        key: 'w'|'a'|'s'|'d'|'stop'|'lift_up'|'lift_down'|'lift_stop'
        Return True jika berhasil publish.
        """
        if not self.connected:
            return False

        if key in _MOVE_KEYS:
            return self._publish(TOPIC_MOVE, key)

        if key in _FORK_KEYS:
            payload = _FORK_PAYLOAD.get(key, "stop")
            return self._publish(TOPIC_FORKLIFT, payload)

        return False

    def send_speed(self, value: int) -> bool:
        """Publish nilai kecepatan (0-255) ke topic robot/speed."""
        if not self.connected:
            return False
        value = max(0, min(255, int(value)))
        return self._publish(TOPIC_SPEED, str(value))

    def _publish(self, topic: str, payload: str) -> bool:
        """Internal: publish ke broker dengan QoS 1."""
        try:
            result = self._client.publish(topic, payload, qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception:
            return False

    # ── MQTT CALLBACKS ────────────────────────

    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Dipanggil oleh paho saat koneksi berhasil atau gagal."""
        if rc == 0:
            with self._lock:
                self.connected = True
            if self._on_connect:
                self._on_connect(True, f"Terhubung ke {MQTT_HOST}")
        else:
            reason = _RC_MESSAGES.get(rc, f"Error code {rc}")
            if self._on_connect:
                self._on_connect(False, f"Gagal: {reason}")

    def _on_mqtt_disconnect(self, client, userdata, rc, properties=None):
        """Dipanggil oleh paho saat koneksi terputus."""
        with self._lock:
            self.connected = False
        if rc != 0 and self._on_disconnect:
            self._on_disconnect()

    # ── STATUS ────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self.connected

    def __repr__(self):
        state = "connected" if self.connected else "disconnected"
        return f"<RobotClient MQTT {state}>"


# ── MQTT RETURN CODE MESSAGES ─────────────────
_RC_MESSAGES = {
    1: "Versi protokol tidak didukung",
    2: "Client ID tidak valid",
    3: "Broker tidak tersedia",
    4: "Username atau password salah",
    5: "Tidak diizinkan",
}