/*
  ESP32 + HiveMQ Cloud (MQTT over TLS 8883) + PWM (LEDC)
  Subscribes:
    - robot/move      payload: w|a|s|d|stop
    - robot/speed     payload: 0-255
    - robot/forklift  payload: up|down|stop

  Library:
    - PubSubClient (by Nick O'Leary)
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// ====== WiFi ======
const char* WIFI_SSID     = "Summonfauzan";
const char* WIFI_PASSWORD = "yesking123";

// ====== HiveMQ Cloud MQTT (same as your Python config) ======
const char* MQTT_HOST     = "19040673f194410aa8d14e110b14a8bd.s1.eu.hivemq.cloud";
const int   MQTT_PORT     = 8883;  // TLS
const char* MQTT_USERNAME = "Fauzan1";
const char* MQTT_PASSWORD = "Hello123";
const char* MQTT_CLIENT_ID = "robot_control_esp32"; // must be UNIQUE vs laptop

// ====== Topics (same as your Python config) ======
const char* TOPIC_MOVE     = "robot/move";
const char* TOPIC_SPEED    = "robot/speed";
const char* TOPIC_FORKLIFT = "robot/forklift";

// ====== TLS ======
// For quick testing without CA cert (NOT recommended for production)
#define USE_INSECURE_TLS 1

WiFiClientSecure tlsClient;
PubSubClient mqtt(tlsClient);

// ====== Motor / PWM pins (EDIT to match your wiring) ======
const int PIN_PWM_SPEED = 25;   // PWM output to motor driver ENA/ENB
const int PIN_DIR1      = 26;   // direction pin 1
const int PIN_DIR2      = 27;   // direction pin 2

// Optional forklift pins (edit or remove if unused)
const int PIN_LIFT_UP   = 32;
const int PIN_LIFT_DOWN = 33;

// ====== LEDC PWM settings ======
const int PWM_CH   = 0;
const int PWM_FREQ = 20000;     // 20kHz typical for DC motor drivers
const int PWM_RES  = 8;         // 8-bit => duty 0..255

volatile int g_speed = 0;       // 0..255

void setMotorStop() {
  digitalWrite(PIN_DIR1, LOW);
  digitalWrite(PIN_DIR2, LOW);
  ledcWrite(PWM_CH, 0);
}

void setMotorForward() {
  digitalWrite(PIN_DIR1, HIGH);
  digitalWrite(PIN_DIR2, LOW);
  ledcWrite(PWM_CH, g_speed);
}

void setMotorBackward() {
  digitalWrite(PIN_DIR1, LOW);
  digitalWrite(PIN_DIR2, HIGH);
  ledcWrite(PWM_CH, g_speed);
}

// If you have differential drive (left/right), you’ll want TWO PWM channels + 4 dir pins.
// For now this keeps it simple: only forward/back/stop.
void handleMove(const String& cmd) {
  if (cmd == "stop") setMotorStop();
  else if (cmd == "w") setMotorForward();
  else if (cmd == "s") setMotorBackward();
  else if (cmd == "a") {
    // placeholder: implement your steering (e.g., left motor slower)
    // for single motor demo, just stop
    setMotorStop();
  }
  else if (cmd == "d") {
    // placeholder
    setMotorStop();
  }
}

void handleForklift(const String& cmd) {
  if (cmd == "up") {
    digitalWrite(PIN_LIFT_UP, HIGH);
    digitalWrite(PIN_LIFT_DOWN, LOW);
  } else if (cmd == "down") {
    digitalWrite(PIN_LIFT_UP, LOW);
    digitalWrite(PIN_LIFT_DOWN, HIGH);
  } else { // "stop"
    digitalWrite(PIN_LIFT_UP, LOW);
    digitalWrite(PIN_LIFT_DOWN, LOW);
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String t(topic);
  String msg;
  msg.reserve(length);
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  msg.trim();

  if (t == TOPIC_SPEED) {
    int v = msg.toInt();
    if (v < 0) v = 0;
    if (v > 255) v = 255;
    g_speed = v;

    // Update PWM immediately (keeps current direction)
    ledcWrite(PWM_CH, g_speed);
  }
  else if (t == TOPIC_MOVE) {
    handleMove(msg);
  }
  else if (t == TOPIC_FORKLIFT) {
    handleForklift(msg);
  }
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
  }
}

void connectMQTT() {
#if USE_INSECURE_TLS
  tlsClient.setInsecure(); // skips certificate verification
#endif

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(mqttCallback);

  while (!mqtt.connected()) {
    // connect(clientID, username, password)
    if (mqtt.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
      mqtt.subscribe(TOPIC_MOVE, 1);
      mqtt.subscribe(TOPIC_SPEED, 1);
      mqtt.subscribe(TOPIC_FORKLIFT, 1);
    } else {
      delay(2000);
    }
  }
}

void setup() {
  pinMode(PIN_DIR1, OUTPUT);
  pinMode(PIN_DIR2, OUTPUT);

  pinMode(PIN_LIFT_UP, OUTPUT);
  pinMode(PIN_LIFT_DOWN, OUTPUT);

  // Setup PWM
  ledcSetup(PWM_CH, PWM_FREQ, PWM_RES);
  ledcAttachPin(PIN_PWM_SPEED, PWM_CH);
  ledcWrite(PWM_CH, 0);

  setMotorStop();
  handleForklift("stop");

  connectWiFi();
  connectMQTT();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }
  if (!mqtt.connected()) {
    connectMQTT();
  }
  mqtt.loop();
}