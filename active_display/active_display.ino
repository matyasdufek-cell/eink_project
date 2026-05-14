#include <SPI.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <WiFiManager.h>
#include "display_functions.h"


// ZDE DOPLŇ SVOJE URL ADRESY
String url_black_str = "";
String url_red_str = "";

int required_size = 0;

// Pomocná funkce pro streamování dat přímo do displeje
bool streamToDisplay(const char* url, uint8_t command, bool invert, int requiredSize) {
  if (WiFi.status() != WL_CONNECTED) return false;

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(20000);

  if (http.begin(client, url)) {
    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
      WiFiClient* stream = http.getStreamPtr();

      digitalWrite(CS_PIN, LOW);
      digitalWrite(DC_PIN, LOW);
      hardwareSpi(command); 
      digitalWrite(DC_PIN, HIGH);

      uint8_t buffer[128];
      int totalRead = 0;

      while (http.connected() && totalRead < requiredSize) {
        size_t size = stream->available();
        if (size) {
          int c = stream->readBytes(buffer, ((size > sizeof(buffer)) ? sizeof(buffer) : size));
          for (int i = 0; i < c; i++) {
            // TADY PROBÍHÁ MAGIE:
            uint8_t data = buffer[i];
            if (invert) data = ~data; // Překlopí bity (0->1, 1->0)
            hardwareSpi(data);
          }
          totalRead += c;
        }
        yield();
      }

      digitalWrite(CS_PIN, HIGH);
      http.end();
      return true;
    }
  }
  return false;
}


void vykresliObrazek(const char* urlBlack, const char* urlRed) {
  // 1. Černá data (Registr 0x24)
  // Většinou: 1 = Bílá, 0 = Černá. Zkusíme nejdřív bez inverze (false)
  Serial.println("Posilam cerna data...");
  streamToDisplay(urlBlack, 0x24, true, required_size); 

  // 2. Červená data (Registr 0x26)
  // Tady je tvůj hlavní problém. Musíme ji invertovat (true), 
  // aby pozadí nebylo červené.
  Serial.println("Posilam cervena data...");
  streamToDisplay(urlRed, 0x26, false, required_size);

  // 3. Aktivace refresh
  Serial.println("Refresh...");
  uint8_t refreshSeq[] = { 0xF7 }; 
  sendIndexData(0x22, refreshSeq, 1);
  sendIndexData(0x20, NULL, 0); 
  
  waitBusy();
}

// --- HLAVNÍ PROGRAM ---

void setup() {
  WiFi.mode(WIFI_STA);
  Serial.begin(115200);
  delay(1000);

  WiFiManager wfm;
  WiFiManagerParameter room_id_box("room_id", "room ID", "20", 4);
  wfm.addParameter(&room_id_box);

  WiFiManagerParameter display_width("display_width", "display width", "400", 4);
  wfm.addParameter(&display_width);

  WiFiManagerParameter display_height("display_height", "display height", "300", 4);
  wfm.addParameter(&display_height);

  bool res;
    res = wfm.autoConnect("eink_display");
    if(!res) {
      Serial.println("\nFailed to connect.");
    }
  
  String roomID = String(room_id_box.getValue());
  int battery = 50;
  Serial.print("room ID: ");
  Serial.println(roomID);

  url_black_str = "http://192.168.0.188:5000/download/" + roomID + "/" + battery + "/black_binary.bin";//"http://10.1.198.124:5000/download/" + roomID + "/black_binary.bin";
  url_red_str = "http://192.168.0.188:5000/download/" + roomID + "/" + battery + "/red_binary.bin";//"http://10.1.198.124:5000/download/" + roomID + "/red_binary.bin";

  int width = atoi(display_width.getValue());
  int height = atoi(display_height.getValue());
  required_size = width * height / 8;

  // 3. Inicializace HW pinů a SPI
  pinMode(POWER, OUTPUT);
  digitalWrite(POWER, HIGH);
  delay(100);

  SPI.begin();
  SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE0));

  pinMode(CS_PIN, OUTPUT);
  pinMode(DC_PIN, OUTPUT);
  pinMode(RESET_PIN, OUTPUT);
  pinMode(BUSY_PIN, INPUT);
  
  Serial.println("Setup dokoncen.");
}

void loop() {
  Serial.println("\n--- Kontrola aktualizace ---");

  if (WiFi.status() == WL_CONNECTED) {
    // Probudíme displej z hlubokého spánku
    resetDisplay();
    initCOG(); 

    // Spustíme streamování a vykreslení
    vykresliObrazek(url_black_str.c_str(), url_red_str.c_str());

    // Uspíme displej (šetří energii a hardware)
    powerOffCOG(); 
  }
  else {
    WiFiManager wfm;
    WiFiManagerParameter room_id_box("room_id", "room ID", "", 4);
    wfm.addParameter(&room_id_box);

    bool res;
      res = wfm.autoConnect("eink_display");
      if(!res) {
        Serial.println("\nFailed to connect.");
      }
    
    Serial.print("room ID:");
    Serial.println(room_id_box.getValue());
  }

  Serial.println("Cekam 5 minut...");
  delay(60000);
}