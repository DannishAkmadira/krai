# ─────────────────────────────────────────────
#  config.py
#  Semua konstanta global untuk Robot Control App
# ─────────────────────────────────────────────

# ── MQTT ──────────────────────────────────────
MQTT_HOST      = "10.90.50.32"  # ganti dengan host HiveMQ
MQTT_PORT      = 1883                        # port TLS HiveMQ cloud
MQTT_USERNAME  = "DanishAkmadira"                  # ganti dengan username HiveMQ
MQTT_PASSWORD  = "@November24"                  # ganti dengan password HiveMQ
MQTT_CLIENT_ID = "robot_control_laptop"
MQTT_KEEPALIVE = 60                          # detik

# ── MQTT TOPICS ───────────────────────────────
TOPIC_MOVE     = "robot/move"       # payload: w | s | a | d | stop
TOPIC_SPEED    = "robot/speed"      # payload: 0-255
TOPIC_FORKLIFT = "robot/forklift"   # payload: up | down | stop

# ── CAMERA ────────────────────────────────────
CAMERA_URL        = "http://192.168.4.1:81/stream"
CAMERA_FPS_TARGET = 30
CAMERA_WIDTH      = 640
CAMERA_HEIGHT     = 480

# ── COMMAND BYTES (gerak) ─────────────────────
CMD = {
    "stop":      b"\x00",
    "w":         b"\x01",   # maju
    "s":         b"\x02",   # mundur
    "a":         b"\x03",   # kiri
    "d":         b"\x04",   # kanan
    "lift_up":   b"\x05",   # forklift naik  (Q)
    "lift_down": b"\x06",   # forklift turun (E)
    "lift_stop": b"\x07",   # forklift stop
}

# ── COLORS ────────────────────────────────────
BG       = "#0d0f12"
PANEL    = "#141720"
BORDER   = "#1e2535"
ACCENT   = "#00e5ff"
ACCENT2  = "#ff3d71"
GREEN    = "#00ff9d"
YELLOW   = "#ffd600"
TEXT     = "#c8d6e5"
TEXTDIM  = "#4a5568"
WHITE    = "#e8f0fe"

# ── FONTS ─────────────────────────────────────
FONT_FAMILY = "Courier New"

# ── WINDOW ────────────────────────────────────
WINDOW_TITLE  = "ROBOT CONTROL PANEL"
WINDOW_WIDTH  = 1100
WINDOW_HEIGHT = 680