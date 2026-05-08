# ─────────────────────────────────────────────
#  config.py
#  Semua konstanta global untuk Robot Control App
# ─────────────────────────────────────────────

# ── NETWORK ───────────────────────────────────
ESP32_IP        = "192.168.4.1"   # IP ESP32 (mode AP) atau sesuaikan
ESP32_PORT      = 8080            # Port TCP untuk command
CAMERA_URL      = "http://192.168.4.1:81/stream"  # URL MJPEG stream ESP32-CAM
SOCKET_TIMEOUT  = 3               # detik

# ── COMMAND BYTES (gerak) ─────────────────────
CMD = {
    "stop": b"\x00",
    "w":    b"\x01",   # maju
    "s":    b"\x02",   # mundur
    "a":    b"\x03",   # kiri
    "d":    b"\x04",   # kanan
}
CMD_SPEED_HEADER = 0xFF           # prefix byte untuk paket kecepatan

# ── BATTERY ───────────────────────────────────
BATTERY_MAX_VOLT  = 12.6
BATTERY_MIN_VOLT  = 9.0
BATTERY_WARN_PCT  = 0.3           # kuning di bawah 30%
BATTERY_CRIT_PCT  = 0.15          # merah di bawah 15%

# ── CAMERA ────────────────────────────────────
CAMERA_FPS_TARGET = 30            # target FPS tampilan
CAMERA_WIDTH      = 640
CAMERA_HEIGHT     = 480

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