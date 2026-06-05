#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <PubSubClient.h>

// =========================
// User Config
// =========================
const char* WIFI_SSID     = "Summonfauzan";
const char* WIFI_PASSWORD = "yesking123";

const char* MQTT_HOST      = "10.210.189.32";
const int   MQTT_PORT      = 1883;
const char* MQTT_CLIENT_ID = "robot_gateway_esp32_1";

const char* MQTT_USERNAME = "";
const char* MQTT_PASSWORD = "";

// Topics
const char* TOPIC_MOVE     = "robot/move";
const char* TOPIC_SPEED    = "robot/speed";
const char* TOPIC_FORKLIFT = "robot/forklift";

// UART (ESP1 <-> ESP2 Motor)
static const int UART_RX = 16;
static const int UART_TX = 17;
static const int UART_BAUD = 115200;

// =========================
// Tunables (Brownout mitigation)
// =========================
static const bool DEBUG_LOG = true;

// Delay before ANY WiFi activity (rail settle after boot + UART)
static const uint32_t BOOT_SOFTSTART_MS = 5000;

// Once WiFi connects, wait before first MQTT connect attempt
static const uint32_t WIFI_SETTLE_BEFORE_MQTT_MS = 3000;

// Backoff between attempts
static const uint32_t WIFI_RETRY_MS = 2000;
static const uint32_t MQTT_RETRY_MS = 2000;

// If your link is strong, lowering TX power helps current spikes.
// Try: WIFI_POWER_2dBm / 5dBm / 8_5dBm / 11dBm ...
static const wifi_power_t WIFI_TX_POWER = WIFI_POWER_8_5dBm;

// Reduce peak draw; 80 MHz is usually enough for gateway duties.
static const uint32_t CPU_FREQ_MHZ = 80;

// =========================
// Globals
// =========================
HardwareSerial MotorSerial(2);

WiFiClient netClient;
PubSubClient mqtt(netClient);

static bool wifiWasConnected = false;
static uint32_t wifiConnectedAtMs = 0;

// =========================
// UART helpers (low allocation)
// =========================
static void uartSendLine(const char* s) {
  MotorSerial.print(s);
  MotorSerial.print('\n');
  if (DEBUG_LOG) {
    Serial.print("UART->MOTOR: ");
    Serial.println(s);
  }
}

static void uartSendKeyVal3(const char* key3, const byte* payload, unsigned int length) {
  MotorSerial.write((const uint8_t*)key3, 3);
  MotorSerial.write(':');
  MotorSerial.write(payload, length);
  MotorSerial.write('\n');

  if (DEBUG_LOG) {
    Serial.print("UART->MOTOR: ");
    Serial.write((const uint8_t*)key3, 3);
    Serial.print(":");
    Serial.write(payload, length);
    Serial.println();
  }
}

// =========================
// MQTT callback
// =========================
static void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Trim trailing whitespace
  while (length > 0) {
    byte c = payload[length - 1];
    if (c == '\r' || c == '\n' || c == ' ' || c == '\t') length--;
    else break;
  }

  if (strcmp(topic, TOPIC_SPEED) == 0) {
    uartSendKeyVal3("SPD", payload, length);
  } else if (strcmp(topic, TOPIC_MOVE) == 0) {
    uartSendKeyVal3("MOV", payload, length);
  } else if (strcmp(topic, TOPIC_FORKLIFT) == 0) {
    uartSendKeyVal3("FRK", payload, length);
  }
}

// =========================
// Connectivity (non-blocking attempts)
// =========================
static void ensureWiFiOnce() {
  static uint32_t lastAttemptMs = 0;
  const uint32_t now = millis();

  if (WiFi.status() == WL_CONNECTED) return;
  if ((uint32_t)(now - lastAttemptMs) < WIFI_RETRY_MS) return;
  lastAttemptMs = now;

  if (DEBUG_LOG) Serial.println("WiFi: begin()");

  WiFi.mode(WIFI_STA);

  // Reduce current spikes (trade-offs: latency / throughput)
  WiFi.setSleep(true);
  WiFi.setTxPower(WIFI_TX_POWER);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

static void onWiFiStateTick() {
  wl_status_t st = WiFi.status();

  if (st == WL_CONNECTED) {
    if (!wifiWasConnected) {
      wifiWasConnected = true;
      wifiConnectedAtMs = millis();
      if (DEBUG_LOG) {
        Serial.print("WiFi: connected, IP=");
        Serial.println(WiFi.localIP());
        Serial.println("WiFi: settling before MQTT...");
      }
    }
  } else {
    wifiWasConnected = false;
  }
}

static void ensureMQTTOnce() {
  static uint32_t lastAttemptMs = 0;
  const uint32_t now = millis();

  if (WiFi.status() != WL_CONNECTED) return;
  if (!wifiWasConnected) return;

  // Wait a bit after WiFi connects before first MQTT connect
  if ((uint32_t)(now - wifiConnectedAtMs) < WIFI_SETTLE_BEFORE_MQTT_MS) return;

  if (mqtt.connected()) return;
  if ((uint32_t)(now - lastAttemptMs) < MQTT_RETRY_MS) return;
  lastAttemptMs = now;

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(mqttCallback);

  if (DEBUG_LOG) {
    Serial.print("MQTT: connect ");
    Serial.print(MQTT_HOST);
    Serial.print(":");
    Serial.println(MQTT_PORT);
  }

  bool ok;
  if (strlen(MQTT_USERNAME) > 0) ok = mqtt.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD);
  else ok = mqtt.connect(MQTT_CLIENT_ID);

  if (!ok) {
    if (DEBUG_LOG) {
      Serial.print("MQTT: failed rc=");
      Serial.println(mqtt.state());
    }
    return;
  }

  if (DEBUG_LOG) Serial.println("MQTT: connected");

  // Spread the work slightly
  delay(200);

  mqtt.subscribe(TOPIC_MOVE, 1);
  delay(50);
  mqtt.subscribe(TOPIC_SPEED, 1);
  delay(50);
  mqtt.subscribe(TOPIC_FORKLIFT, 1);

  uartSendLine("MOV:stop");
}

// =========================
// Setup / Loop
// =========================
void setup() {
  Serial.begin(115200);
  delay(50);

  // Lower CPU freq early (helps peak draw)
  setCpuFrequencyMhz(CPU_FREQ_MHZ);

  // UART to motor ESP
  MotorSerial.begin(UART_BAUD, SERIAL_8N1, UART_RX, UART_TX);
  delay(200);
  uartSendLine("HELLO");

  // Soft-start before any WiFi activity
  if (DEBUG_LOG) {
    Serial.print("Soft-start delay ms=");
    Serial.println(BOOT_SOFTSTART_MS);
  }
  delay(BOOT_SOFTSTART_MS);

  // Kick off first WiFi attempt (non-blocking)
  ensureWiFiOnce();
}

void loop() {
  ensureWiFiOnce();
  onWiFiStateTick();
  ensureMQTTOnce();

  if (mqtt.connected()) {
    mqtt.loop();
  }

  // Optional: read anything from motor ESP (keep it light)
  while (MotorSerial.available()) {
    String line = MotorSerial.readStringUntil('\n');
    line.trim();
    if (line.length() && DEBUG_LOG) {
      Serial.print("MOTOR->UART: ");
      Serial.println(line);
    }
  }

  delay(5);
}