#include <Arduino.h>

// ===== UART from Gateway ESP (ESP1) =====
static const int UART_RX = 16;     // ESP2 RX2  (from ESP1 TX GPIO17)
static const int UART_TX = 17;     // ESP2 TX2  (optional back)
static const int UART_BAUD = 115200;
HardwareSerial GatewaySerial(2);

// ===== Motor pin map =====
const int M1_PWM_PIN  = 18;
const int M1_DIR1_PIN = 19;
const int M1_DIR2_PIN = 23;
const int M1_FREQ     = 933;

const int M2_PWM_PIN  = 21;
const int M2_DIR1_PIN = 22;
const int M2_DIR2_PIN = 25;
const int M2_FREQ     = 833;

const int RESOLUTION = 8;
const int DEAD_TIME_MS = 50;

enum Dir : uint8_t { DIR_STOP = 0, DIR_FWD = 1, DIR_REV = 2 };

volatile Dir g_m1_dir = DIR_STOP;
volatile Dir g_m2_dir = DIR_STOP;
volatile uint8_t g_duty = 180;

SemaphoreHandle_t g_ctrlMutex;

// ===== Optional: scope-friendly self-test =====
static const bool SELFTEST_ENABLE = true;
static const uint32_t SELFTEST_AFTER_MS = 3000;   // if no MOV received after 3s
static const uint32_t SELFTEST_ON_MS    = 1000;   // run 1s
static const uint32_t SELFTEST_OFF_MS   = 500;    // stop 0.5s

static volatile bool g_seenMoveCmd = false;

static inline uint8_t clampDuty(int v) {
  if (v < 0) return 0;
  if (v > 255) return 255;
  return (uint8_t)v;
}

static void motorApply(int pwmPin, int dir1Pin, int dir2Pin, Dir newDir, uint8_t duty) {
  // Stop PWM first (safe switching)
  ledcWrite(pwmPin, 0);

  digitalWrite(dir1Pin, LOW);
  digitalWrite(dir2Pin, LOW);
  vTaskDelay(pdMS_TO_TICKS(DEAD_TIME_MS));

  if (newDir == DIR_STOP) {
    // Keep it stopped
    ledcWrite(pwmPin, 0);
    digitalWrite(dir1Pin, LOW);
    digitalWrite(dir2Pin, LOW);
    return;
  }

  if (newDir == DIR_FWD) {
    digitalWrite(dir1Pin, HIGH);
    digitalWrite(dir2Pin, LOW);
  } else { // DIR_REV
    digitalWrite(dir1Pin, LOW);
    digitalWrite(dir2Pin, HIGH);
  }

  vTaskDelay(pdMS_TO_TICKS(DEAD_TIME_MS));
  ledcWrite(pwmPin, duty);
}

static void motorTask1(void* pv) {
  Dir lastDir = (Dir)255;
  uint8_t lastDuty = 255;

  for (;;) {
    Dir dir;
    uint8_t duty;

    xSemaphoreTake(g_ctrlMutex, portMAX_DELAY);
    dir = g_m1_dir;
    duty = g_duty;
    xSemaphoreGive(g_ctrlMutex);

    if (dir != lastDir || duty != lastDuty) {
      motorApply(M1_PWM_PIN, M1_DIR1_PIN, M1_DIR2_PIN, dir, duty);
      lastDir = dir;
      lastDuty = duty;
    }
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

static void motorTask2(void* pv) {
  Dir lastDir = (Dir)255;
  uint8_t lastDuty = 255;

  for (;;) {
    Dir dir;
    uint8_t duty;

    xSemaphoreTake(g_ctrlMutex, portMAX_DELAY);
    dir = g_m2_dir;
    duty = g_duty;
    xSemaphoreGive(g_ctrlMutex);

    if (dir != lastDir || duty != lastDuty) {
      motorApply(M2_PWM_PIN, M2_DIR1_PIN, M2_DIR2_PIN, dir, duty);
      lastDir = dir;
      lastDuty = duty;
    }
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

static void setMove(const String& cmd) {
  xSemaphoreTake(g_ctrlMutex, portMAX_DELAY);

  if (cmd == "w") {
    g_m1_dir = DIR_FWD; g_m2_dir = DIR_FWD;
  } else if (cmd == "s") {
    g_m1_dir = DIR_REV; g_m2_dir = DIR_REV;
  } else if (cmd == "a") {
    g_m1_dir = DIR_REV; g_m2_dir = DIR_FWD;
  } else if (cmd == "d") {
    g_m1_dir = DIR_FWD; g_m2_dir = DIR_REV;
  } else {
    g_m1_dir = DIR_STOP; g_m2_dir = DIR_STOP;
  }

  g_seenMoveCmd = true;
  xSemaphoreGive(g_ctrlMutex);
}

static void setSpeed(const String& msg) {
  int v = msg.toInt();
  uint8_t duty = clampDuty(v);

  xSemaphoreTake(g_ctrlMutex, portMAX_DELAY);
  g_duty = duty;
  xSemaphoreGive(g_ctrlMutex);
}

static void handleLine(const String& line) {
  if (line.startsWith("SPD:")) {
    setSpeed(line.substring(4));
    GatewaySerial.println("ACK:SPD");
    return;
  }
  if (line.startsWith("MOV:")) {
    setMove(line.substring(4));
    GatewaySerial.println("ACK:MOV");
    return;
  }
  if (line.startsWith("FRK:")) {
    GatewaySerial.println("ACK:FRK");
    return;
  }
  if (line == "HELLO") {
    GatewaySerial.println("ACK:HELLO");
  }
}

void setup() {
  Serial.begin(115200);

  // UART from gateway
  GatewaySerial.begin(UART_BAUD, SERIAL_8N1, UART_RX, UART_TX);

  // Direction pins
  pinMode(M1_DIR1_PIN, OUTPUT);
  pinMode(M1_DIR2_PIN, OUTPUT);
  pinMode(M2_DIR1_PIN, OUTPUT);
  pinMode(M2_DIR2_PIN, OUTPUT);

  digitalWrite(M1_DIR1_PIN, LOW);
  digitalWrite(M1_DIR2_PIN, LOW);
  digitalWrite(M2_DIR1_PIN, LOW);
  digitalWrite(M2_DIR2_PIN, LOW);

  // PWM attach (Arduino-ESP32 core v3 style)
  ledcAttach(M1_PWM_PIN, M1_FREQ, RESOLUTION);
  ledcAttach(M2_PWM_PIN, M2_FREQ, RESOLUTION);
  ledcWrite(M1_PWM_PIN, 0);
  ledcWrite(M2_PWM_PIN, 0);

  g_ctrlMutex = xSemaphoreCreateMutex();

  xTaskCreatePinnedToCore(motorTask1, "Motor1_Task", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(motorTask2, "Motor2_Task", 4096, NULL, 1, NULL, 1);

  Serial.println("Motor controller ready.");
}

void loop() {
  // Read lines from gateway
  while (GatewaySerial.available()) {
    String line = GatewaySerial.readStringUntil('\n');
    line.trim();
    if (line.length()) {
      Serial.print("UART RX: ");
      Serial.println(line);
      handleLine(line);
    }
  }

  // Optional self-test so you always see PWM on scope even without ESP1
  if (SELFTEST_ENABLE && !g_seenMoveCmd && millis() > SELFTEST_AFTER_MS) {
    Serial.println("SELFTEST: no MOV received, generating PWM...");
    setSpeed(String(g_duty));
    setMove("w");
    delay(SELFTEST_ON_MS);
    setMove("stop");
    delay(SELFTEST_OFF_MS);
  }

  delay(5);
}