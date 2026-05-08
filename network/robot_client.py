# ─────────────────────────────────────────────
#  network/robot_client.py
#  MQTT Client untuk Robot Control App
#  HiveMQ Cloud + TLS Support
# ─────────────────────────────────────────────

from __future__ import annotations

import ssl
import threading

import paho.mqtt.client as mqtt

from config import (
    MQTT_HOST,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_CLIENT_ID,
    MQTT_KEEPALIVE,
    TOPIC_MOVE,
    TOPIC_SPEED,
    TOPIC_FORKLIFT,
)

# ─────────────────────────────────────────────
# COMMAND MAP
# ─────────────────────────────────────────────

_MOVE_KEYS = {
    "w",
    "a",
    "s",
    "d",
    "stop",
}

_FORK_KEYS = {
    "lift_up",
    "lift_down",
    "lift_stop",
}

_FORK_PAYLOAD = {
    "lift_up": "up",
    "lift_down": "down",
    "lift_stop": "stop",
}

# ─────────────────────────────────────────────
# MQTT RETURN CODE
# ─────────────────────────────────────────────

_RC_MESSAGES = {
    1: "Versi protokol tidak didukung",
    2: "Client ID tidak valid",
    3: "Broker tidak tersedia",
    4: "Username atau password salah",
    5: "Tidak diizinkan",
}


# ─────────────────────────────────────────────
# ROBOT CLIENT
# ─────────────────────────────────────────────

class RobotClient:

    def __init__(
        self,
        on_disconnect=None,
        on_connect=None
    ):

        # status
        self.connected = False

        # callback GUI
        self._on_disconnect = on_disconnect
        self._on_connect = on_connect

        # thread safety
        self._lock = threading.Lock()

        # ─────────────────────────────────────
        # MQTT CLIENT
        # ─────────────────────────────────────

        self._client = mqtt.Client(
            client_id=MQTT_CLIENT_ID,
            protocol=mqtt.MQTTv311,
        )

        # login
        self._client.username_pw_set(
            MQTT_USERNAME,
            MQTT_PASSWORD
        )

        # TLS HiveMQ Cloud
        self._client.tls_set(
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )

        # auto reconnect
        self._client.reconnect_delay_set(
            min_delay=1,
            max_delay=5
        )

        # timeout socket
        self._client.socket_timeout = 5

        # callback MQTT
        self._client.on_connect = self._on_mqtt_connect
        self._client.on_disconnect = self._on_mqtt_disconnect

    # ─────────────────────────────────────────
    # CONNECT
    # ─────────────────────────────────────────

    def connect(self):

        try:

            self._client.connect(
                MQTT_HOST,
                port=MQTT_PORT,
                keepalive=MQTT_KEEPALIVE,
            )

            # background network thread
            self._client.loop_start()

        except Exception as e:

            if self._on_connect:

                self._on_connect(
                    False,
                    f"Gagal konek: {e}"
                )

    # ─────────────────────────────────────────
    # DISCONNECT
    # ─────────────────────────────────────────

    def disconnect(self):

        try:

            self._client.loop_stop()

            self._client.disconnect()

        except Exception:
            pass

        with self._lock:
            self.connected = False

    # ─────────────────────────────────────────
    # SEND COMMAND
    # ─────────────────────────────────────────

    def send_command(self, key: str) -> bool:

        if not self.connected:
            return False

        # gerak robot
        if key in _MOVE_KEYS:

            return self._publish(
                TOPIC_MOVE,
                key
            )

        # forklift
        if key in _FORK_KEYS:

            payload = _FORK_PAYLOAD.get(
                key,
                "stop"
            )

            return self._publish(
                TOPIC_FORKLIFT,
                payload
            )

        return False

    # ─────────────────────────────────────────
    # SEND SPEED
    # ─────────────────────────────────────────

    def send_speed(self, value: int) -> bool:

        if not self.connected:
            return False

        value = max(
            0,
            min(255, int(value))
        )

        return self._publish(
            TOPIC_SPEED,
            str(value)
        )

    # ─────────────────────────────────────────
    # INTERNAL PUBLISH
    # ─────────────────────────────────────────

    def _publish(
        self,
        topic: str,
        payload: str
    ) -> bool:

        try:

            result = self._client.publish(
                topic,
                payload,
                qos=1
            )

            return (
                result.rc
                == mqtt.MQTT_ERR_SUCCESS
            )

        except Exception:

            return False

    # ─────────────────────────────────────────
    # MQTT CALLBACK
    # ─────────────────────────────────────────

    def _on_mqtt_connect(
        self,
        client,
        userdata,
        flags,
        rc
    ):

        if rc == 0:

            with self._lock:
                self.connected = True

            if self._on_connect:

                self._on_connect(
                    True,
                    f"Terhubung ke {MQTT_HOST}"
                )

        else:

            reason = _RC_MESSAGES.get(
                rc,
                f"Error code {rc}"
            )

            if self._on_connect:

                self._on_connect(
                    False,
                    f"Gagal konek: {reason}"
                )

    def _on_mqtt_disconnect(
        self,
        client,
        userdata,
        rc
    ):

        with self._lock:
            self.connected = False

        # disconnect tak terduga
        if rc != 0:

            if self._on_disconnect:

                self._on_disconnect()

    # ─────────────────────────────────────────
    # STATUS
    # ─────────────────────────────────────────

    @property
    def is_connected(self):

        return self.connected

    def __repr__(self):

        state = (
            "connected"
            if self.connected
            else "disconnected"
        )

        return f"<RobotClient MQTT {state}>"