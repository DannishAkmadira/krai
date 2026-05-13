#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <PubSubClient.h>

// ===== WiFi =====
const char* WIFI_SSID     = "Summonfauzan";
const char* WIFI_PASSWORD = "yesking123";

// ===== MQTT (Mosquitto on PC) =====
const char* MQTT_HOST      = "10.10.23.220";
const int   MQTT_PORT      = 1883;
const char* MQTT_CLIENT_ID = "robot_gateway_esp32_1";

const char* MQTT_USERNAME = "";
const char* MQTT_PASSWORD = "";

// Topics
const char* TOPIC_MOVE     = "robot/move";
const char* TOPIC_SPEED    = "robot/speed";
const char* TOPIC_FORKLIFT = "robot/forklift";

// ===== UART =====
static const int UART_RX = 16;
static const int UART_TX = 17;
static const int UART_BAUD = 115200;

HardwareSerial MotorSerial(2);

WiFiClient netClient;
PubSubClient mqtt(netClient);

// (A) Reduce prints / work
static const bool DEBUG_LOG = true;

// Simple helpers (avoid lots of String concatenations)
static void sendRawToMotor(const char* s) {
  MotorSerial.print(s);
  MotorSerial.print('\n');
  if (DEBUG_LOG) {
    Serial.print("UART->MOTOR: ");
    Serial.println(s);
  }
}

static void sendKeyValToMotor(const char* key3, const byte* payload, unsigned int length) {
  // Sends: "KEY:xxxxx\n" without building big Strings
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

static void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Trim whitespace at ends (without allocating)
  while (length > 0 && (payload[length - 1] == '\r' || payload[length - 1] == '\n' || payload[length - 1] == ' ' || payload[length - 1] == '\t')) {
    length--;
  }

  if (strcmp(topic, TOPIC_SPEED) == 0) {
    sendKeyValToMotor("SPD", payload, length);
  } else if (strcmp(topic, TOPIC_MOVE) == 0) {
    sendKeyValToMotor("MOV", payload, length);
  } else if (strcmp(topic, TOPIC_FORKLIFT) == 0) {
    sendKeyValToMotor("FRK", payload, length);
  } else {
    // ignore
  }
}

// (A) Non-blocking WiFi connect attempt
static void ensureWiFiOnce() {
  static unsigned long lastAttemptMs = 0;
  const unsigned long now = millis();

  if (WiFi.status() == WL_CONNECTED) return;
  if (now - lastAttemptMs < 2000) return;  // backoff
  lastAttemptMs = now;

  if (DEBUG_LOG) Serial.println("WiFi: begin()");
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(true);          // reduces peaks a bit (may increase latency)
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

// (A) Non-blocking MQTT connect attempt
static void ensureMQTTOnce() {
  static unsigned long lastAttemptMs = 0;
  const unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED) return;
  if (mqtt.connected()) return;
  if (now - lastAttemptMs < 2000) return;  // backoff
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

  if (ok) {
    if (DEBUG_LOG) Serial.println("MQTT: connected");
    mqtt.subscribe(TOPIC_MOVE, 1);
    mqtt.subscribe(TOPIC_SPEED, 1);
    mqtt.subscribe(TOPIC_FORKLIFT, 1);
    sendRawToMotor("MOV:stop");
  } else {
    if (DEBUG_LOG) {
      Serial.print("MQTT: failed rc=");
      Serial.println(mqtt.state());
    }
  }
}

void setup() {
  Serial.begin(115200);

  MotorSerial.begin(UART_BAUD, SERIAL_8N1, UART_RX, UART_TX);
  delay(200);
  sendRawToMotor("HELLO");

  // (B) Soft-start delay BEFORE WiFi to reduce brownout risk
  delay(5000);

  ensureWiFiOnce();
  // MQTT connect will happen after WiFi is actually up
}

void loop() {
  ensureWiFiOnce();
  ensureMQTTOnce();

  if (mqtt.connected()) mqtt.loop();

  // Optional: read motor responses (keep it cheap)
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