#ifndef DISPLAY_FUNCTIONS_H
#define DISPLAY_FUNCTIONS_H

#include <Arduino.h>
#include <SPI.h>

// Definice pinů pro Lolin D1 Mini
#define SCL_PIN     D5
#define SDA_PIN     D7
#define CS_PIN      D8
#define DC_PIN      D3//D1
#define RESET_PIN   D4//D2
#define BUSY_PIN    D2//D4
#define POWER       D0

inline void hardwareSpi(uint8_t data) {
  SPI.transfer(data);
}

inline void sendIndexData(uint8_t index, const uint8_t *data, uint32_t len) {
  digitalWrite(CS_PIN, LOW);
  digitalWrite(DC_PIN, LOW);
  hardwareSpi(index);
  if (len > 0) {
    digitalWrite(DC_PIN, HIGH);
    for (uint32_t i = 0; i < len; i++) hardwareSpi(data[i]);
  }
  digitalWrite(CS_PIN, HIGH);
}

inline void waitBusy() {
  Serial.print("Cekam na Busy...");
  // WeAct Studio / SSD1683: BUSY == HIGH znamená, že displej pracuje
  while(digitalRead(BUSY_PIN) == HIGH) { 
    delay(10); 
    yield();
  }
  Serial.println(" Hotovo.");
}

inline void resetDisplay() {
  digitalWrite(RESET_PIN, LOW);  delay(10);
  digitalWrite(RESET_PIN, HIGH); delay(10);
  waitBusy();
}

inline void initCOG() {
  Serial.println("Inicializace WeAct 4.2 (SSD1683)...");
  
  resetDisplay();

  // Software Reset
  sendIndexData(0x12, NULL, 0); 
  waitBusy();

  // Driver Output control
  uint8_t driverOut[] = { 0x2B, 0x01, 0x00 }; // 299 + 1 = 300 řádků
  sendIndexData(0x01, driverOut, 3);

  // Data Entry Mode
  uint8_t dataEntry[] = { 0x03 }; // X increment, Y increment
  sendIndexData(0x11, dataEntry, 1);

  // Set Ram X address
  uint8_t ramX[] = { 0x00, 0x31 }; // 0..49 (50*8 = 400 px)
  sendIndexData(0x44, ramX, 2);

  // Set Ram Y address
  uint8_t ramY[] = { 0x00, 0x00, 0x2B, 0x01 }; // 0..299
  sendIndexData(0x45, ramY, 4);

  // Border Waveform
  uint8_t border[] = { 0x05 };
  sendIndexData(0x3C, border, 1);

  // Display Update Control 1 (Internal Sensor)
  uint8_t updateCtrl[] = { 0x00, 0x80 };
  sendIndexData(0x21, updateCtrl, 2);

  waitBusy();
}

inline void powerOffCOG() {
  // Deep sleep mode 1
  uint8_t sleep[] = { 0x01 };
  sendIndexData(0x10, sleep, 1);
  Serial.println("Displej uspan.");
}

#endif