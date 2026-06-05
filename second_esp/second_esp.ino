#include <Arduino.h>

// ===== UART from Gateway ESP (ESP1) =====
static const int UART_RX = 16;     // ESP2 RX2
static const int UART_TX = 17;     // ESP2 TX2
static const int UART_BAUD = 115200;
HardwareSerial GatewaySerial(2);

// ===== 4-Motor Pin Map =====
// KIRI ATAS (Top Left)
const int M_KA_PWM = 13;
const int M_KA_REN = 12;
const int M_KA_LEN = 33; 

// KANAN ATAS (Top Right) 
// CHANGED: Shifted from 34/35 (Input-Only) to 14/27 for safety
const int M_KNA_PWM = 14; 
const int M_KNA_REN = 27; 
const int M_KNA_LEN = 19;

// KIRI BAWAH (Bottom Left)
const int M_KB_PWM = 32;
const int M_KB_REN = 26;
const int M_KB_LEN = 25; 

// KANAN BAWAH (Bottom Right)
const int M_KNB_PWM = 5;
const int M_KNB_REN = 4;
const int M_KNB_LEN = 15;

const int MOTOR_FREQ = 900; // Unified frequency
const int RESOLUTION = 8;
const int DEAD_TIME_MS = 50;

enum Dir : uint8_t { DIR_STOP = 0, DIR_FWD = 1, DIR_REV = 2 };

// Volatile directional variables for all 4 motors
volatile Dir g_m_ka_dir  = DIR_STOP;
volatile Dir g_m_kna_dir = DIR_STOP;
volatile Dir g_m_kb_dir  = DIR_STOP;
volatile Dir g_m_knb_dir = DIR_STOP;
volatile uint8_t g_duty  = 180;

SemaphoreHandle_t g_ctrlMutex;
static volatile bool g_seenMoveCmd = false;

static inline uint8_t clampDuty(int v) {
  if (v < 0) return 0;
  if (v > 255) return 255;
  return (uint8_t)v;
}

static void motorApply(int pwmPin, int dir1Pin, int dir2Pin, Dir newDir, uint8_t duty) {
  ledcWrite(pwmPin, 0);
  digitalWrite(dir1Pin, LOW);
  digitalWrite(dir2Pin, LOW);
  vTaskDelay(pdMS_TO_TICKS(DEAD_TIME_MS));

  if (newDir == DIR_STOP) return;

  if (newDir == DIR_FWD) {
    digitalWrite(dir1Pin, HIGH);
    digitalWrite(dir2Pin, LOW);
  } else { 
    digitalWrite(dir1Pin, LOW);
    digitalWrite(dir2Pin, HIGH);
  }

  vTaskDelay(pdMS_TO_TICKS(DEAD_TIME_MS));
  ledcWrite(pwmPin, duty);
}

// Unified task tracker processing left side & right side sets 
static void leftMotorsTask(void* pv) {
  Dir last_ka = (Dir)255, last_kb = (Dir)255;
  uint8_t lastDuty = 255;

  for (;;) {
    Dir ka, kb; uint8_t duty;
    xSemaphoreTake(g_ctrlMutex, portMAX_DELAY);
    ka = g_m_ka_dir; kb = g_m_kb_dir; duty = g_duty;
    xSemaphoreGive(g_ctrlMutex);

    if (ka != last_ka || duty != lastDuty) {
      motorApply(M_KA_PWM, M_KA_REN, M_KA_LEN, ka, duty);
      last_ka = ka;
    }
    if (kb != last_kb || duty != lastDuty) {
      motorApply(M_KB_PWM, M_KB_REN, M_KB_LEN, kb, duty);
      last_kb = kb;
    }
    lastDuty = duty;
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

static void rightMotorsTask(void* pv) {
  Dir last_kna = (Dir)255, last_knb = (Dir)255;
  uint8_t lastDuty = 255;

  for (;;) {
    Dir kna, knb; uint8_t duty;
    xSemaphoreTake(g_ctrlMutex, portMAX_DELAY);
    kna = g_m_kna_dir; knb = g_m_knb_dir; duty = g_duty;
    xSemaphoreGive(g_ctrlMutex);

    if (kna != last_kna || duty != lastDuty) {
      motorApply(M_KNA_PWM, M_KNA_REN, M_KNA_LEN, kna, duty);
      last_kna = kna;
    }
    if (knb != last_knb || duty != lastDuty) {
      motorApply(M_KNB_PWM, M_KNB_REN, M_KNB_LEN, knb, duty);
      last_knb = knb;
    }
    lastDuty = duty;
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

static void setMove(const String& cmd) {
  xSemaphoreTake(g_ctrlMutex, portMAX_DELAY);

  if (cmd == "w") { // All Forward
    g_m_ka_dir = DIR_FWD; g_m_kna_dir = DIR_FWD;
    g_m_kb_dir = DIR_FWD; g_m_knb_dir = DIR_FWD;
  } else if (cmd == "s") { // All Reverse
    g_m_ka_dir = DIR_REV; g_m_kna_dir = DIR_REV;
    g_m_kb_dir = DIR_REV; g_m_knb_dir = DIR_REV;
  } else if (cmd == "a") { // Skid turn Left (Left goes backwards, Right goes forwards)
    g_m_ka_dir = DIR_REV; g_m_kna_dir = DIR_FWD;
    g_m_kb_dir = DIR_REV; g_m_knb_dir = DIR_FWD;
  } else if (cmd == "d") { // Skid turn Right (Left goes forwards, Right goes backwards)
    g_m_ka_dir = DIR_FWD; g_m_kna_dir = DIR_REV;
    g_m_kb_dir = DIR_FWD; g_m_knb_dir = DIR_REV;
  } else { // Hard Stop
    g_m_ka_dir = DIR_STOP; g_m_kna_dir = DIR_STOP;
    g_m_kb_dir = DIR_STOP; g_m_knb_dir = DIR_STOP;
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
  if (line.startsWith("SPD:")) { setSpeed(line.substring(4)); GatewaySerial.println("ACK:SPD"); return; }
  if (line.startsWith("MOV:")) { setMove(line.substring(4));  GatewaySerial.println("ACK:MOV"); return; }
  if (line == "HELLO") { GatewaySerial.println("ACK:HELLO"); }
}

void setup() {
  Serial.begin(115200);
  GatewaySerial.begin(UART_BAUD, SERIAL_8N1, UART_RX, UART_TX);

  // Set up outputs
  int outputPins[] = {M_KA_REN, M_KA_LEN, M_KNA_REN, M_KNA_LEN, M_KB_REN, M_KB_LEN, M_KNB_REN, M_KNB_LEN};
  for(int pin : outputPins) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }

  // Attach PWM channels using standard ESP32 Core v3 styles
  ledcAttach(M_KA_PWM, MOTOR_FREQ, RESOLUTION);
  ledcAttach(M_KNA_PWM, MOTOR_FREQ, RESOLUTION);
  ledcAttach(M_KB_PWM, MOTOR_FREQ, RESOLUTION);
  ledcAttach(M_KNB_PWM, MOTOR_FREQ, RESOLUTION);

  ledcWrite(M_KA_PWM, 0); ledcWrite(M_KNA_PWM, 0);
  ledcWrite(M_KB_PWM, 0); ledcWrite(M_KNB_PWM, 0);

  g_ctrlMutex = xSemaphoreCreateMutex();

  // Distribute workload onto separate FreeRTOS cores
  xTaskCreatePinnedToCore(leftMotorsTask, "LeftMotors", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(rightMotorsTask, "RightMotors", 4096, NULL, 1, NULL, 1);

  Serial.println("4-Channel Motor Controller Active.");
}

void loop() {
  while (GatewaySerial.available()) {
    String line = GatewaySerial.readStringUntil('\n');
    line.trim();
    if (line.length()) {
      handleLine(line);
    }
  }
  delay(5);
}