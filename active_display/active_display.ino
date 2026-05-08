#include <SPI.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include "display_functions.h"

// --- KONFIGURACE ---
const char* ssid = "Maty";//"GKREN_STUDENT";
const char* password = "Pm369258";//"g.stud.123";

// ZDE DOPLŇ SVOJE URL ADRESY
const char* url_black = "http://192.168.0.188:5000/download/black_binary.bin";//"http://10.1.198.124:5000/download/black_binary.bin";
const char* url_red   = "http://192.168.0.188:5000/download/red_binary.bin";//"http://10.1.198.124:5000/download/red_binary.bin";


// --- GLOBÁLNÍ PROMĚNNÉ ---
// Definujeme paměť pro obrázky a velikost
#ifndef REQUIRED_SIZE
  #define REQUIRED_SIZE 15000  // 480x800 px / 8
#endif

//uint8_t* image_black = NULL;
//uint8_t* image_red   = NULL;

// --- POMOCNÉ FUNKCE ---

// Funkce pro stažení binárních dat přímo do alokovaného bufferu
/*
bool downloadToBuffer(const char* url, uint8_t* buffer, size_t size) {
  if (WiFi.status() != WL_CONNECTED) return false;

  WiFiClient client; // Vytvořit lokálního klienta
  HTTPClient http;
  http.begin(client, url);
  http.setTimeout(15000); // 15 sekund timeout pro pomalejší servery
  
  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK) {
    int len = http.getSize();
    if (len > 0 && len != size) {
      Serial.printf("Varovani: Velikost na webu (%d) neodpovida ocekavani (%d)\n", len, size);
    }
    
    WiFiClient* stream = http.getStreamPtr();
    // Čtení dat přímo do naší RAM
    int readLen = stream->readBytes(buffer, size);
    
    http.end();
    Serial.printf("Stazeno %d bajtu z URL.\n", readLen);
    return (readLen > 0);
  } else {
    Serial.printf("HTTP Chyba (%d): %s\n", httpCode, http.errorToString(httpCode).c_str());
    http.end();
    return false;
  }
}
*/

// Pomocná funkce pro streamování dat přímo do displeje
bool streamToDisplay(const char* url, uint8_t command, bool invert) {
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

      while (http.connected() && totalRead < REQUIRED_SIZE) {
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
/*
// Funkce pro odeslání dat do displeje
void vykresliObrazek(const uint8_t* blackData, const uint8_t* redData) {
  uint8_t duw[]   = { 0x00, 0x3b, 0x00, 0x00, 0x1f, 0x03 };
  uint8_t drfw[]  = { 0x00, 0x3b, 0x00, 0xc9 };
  uint8_t ram_rw[] = { 0x3b, 0x00, 0x14 };

  Serial.println("Posilam data do RAM displeje...");
  
  sendIndexData(0x13, duw, 6);
  sendIndexData(0x90, drfw, 4);

  // Černá vrstva
  sendIndexData(0x12, ram_rw, 3);
  sendIndexData(0x10, blackData, REQUIRED_SIZE);

  // Červená vrstva
  sendIndexData(0x12, ram_rw, 3);
  sendIndexData(0x11, redData, REQUIRED_SIZE);

  Serial.println("Aktivuji prekresleni (Refresh)...");
  initCOG();
  refreshDisplay();
  //powerOffCOG(); 
  Serial.println("Displej aktualizovan.");
}
*/

void vykresliObrazek(const char* urlBlack, const char* urlRed) {
  // 1. Černá data (Registr 0x24)
  // Většinou: 1 = Bílá, 0 = Černá. Zkusíme nejdřív bez inverze (false)
  Serial.println("Posilam cerna data...");
  streamToDisplay(urlBlack, 0x24, true); 

  // 2. Červená data (Registr 0x26)
  // Tady je tvůj hlavní problém. Musíme ji invertovat (true), 
  // aby pozadí nebylo červené.
  Serial.println("Posilam cervena data...");
  streamToDisplay(urlRed, 0x26, false);

  // 3. Aktivace refresh
  Serial.println("Refresh...");
  uint8_t refreshSeq[] = { 0xF7 }; 
  sendIndexData(0x22, refreshSeq, 1);
  sendIndexData(0x20, NULL, 0); 
  
  waitBusy();
}

// --- HLAVNÍ PROGRAM ---

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // 2. Připojení k WiFi
  WiFi.begin(ssid, password);
  Serial.print("Pripojuji WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi OK!");

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
  /*
  Serial.println("\n--- Kontrola aktualizace ---");
 
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    


    // Stáhneme data ze serveru
    bool successBlack = downloadToBuffer(url_black, image_black, REQUIRED_SIZE);
    bool successRed   = downloadToBuffer(url_red, image_red, REQUIRED_SIZE);

    if (successBlack && successRed) {
      // Pokud se stažení povedlo, probudíme displej a vykreslíme
      digitalWrite(POWER, HIGH);
      delay(50);
      resetDisplay();
      
      vykresliObrazek(image_black, image_red);
      
      // Po vykreslení můžeme (volitelně) vypnout napájení pro šetření
      // digitalWrite(POWER, LOW); 
    } else {
      Serial.println("Chyba stahovani, zkusim to v dalsim cyklu.");
    }
  } else {
    Serial.println("WiFi ztraceno, pripojuji znovu...");
    WiFi.begin(ssid, password);
  }

  // Čekání 30 sekund
  Serial.println("Cekam 30 sekund na dalsi kontrolu...");
  delay(30000); 
  */
  Serial.println("\n--- Kontrola aktualizace ---");

  if (WiFi.status() == WL_CONNECTED) {
    // Probudíme displej z hlubokého spánku
    resetDisplay();
    initCOG(); 

    // Spustíme streamování a vykreslení
    vykresliObrazek(url_black, url_red);

    // Uspíme displej (šetří energii a hardware)
    powerOffCOG(); 
  }

  Serial.println("Cekam 5 minut...");
  delay(300000);
}