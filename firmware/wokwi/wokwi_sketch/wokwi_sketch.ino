/*
  HỆ THỐNG GIÁM SÁT NHIỆT ĐỘ VÀ ĐỘ ẨM PHÒNG HỌC
  Firmware mẫu cho ESP32/ESP8266 + DHT11/DHT22.

  Cách dùng:
  1. Copy config_example.h thành config.h.
  2. Điền WiFi, SERVER_URL và DEVICE_API_KEY trong config.h.
  3. Cài thư viện "DHT sensor library" trong Arduino IDE.
*/

#if __has_include("config.h")
#include "config.h"
#elif __has_include("config_wokwi.h")
#include "config_wokwi.h"
#else
#error "Vui long copy firmware/config_example.h thanh firmware/config.h, hoac dung config_wokwi.h khi chay Wokwi."
#endif

#ifndef ALLOW_INSECURE_TLS
#define ALLOW_INSECURE_TLS 1
#endif

#ifndef SERVER_ROOT_CA
#define SERVER_ROOT_CA ""
#endif

#include <DHT.h>

#if defined(ESP32)
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <mbedtls/md.h>
#include <time.h>
#elif defined(ESP8266)
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#else
#error "Sketch nay chi ho tro ESP32 hoac ESP8266."
#endif

DHT dht(DHT_PIN, DHT_TYPE);

unsigned long lastSendTime = 0;

bool connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  Serial.print("Dang ket noi WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startedAt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startedAt < 15000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println();
    Serial.println("Chua ket noi duoc WiFi. Van tiep tuc doc cam bien, se thu lai lan sau.");
    return false;
  }

  Serial.println();
  Serial.print("Da ket noi WiFi. IP: ");
  Serial.println(WiFi.localIP());
  return true;
}

#if defined(ESP32)
void syncTimeForSignature() {
  if (!ENABLE_HMAC_SIGNATURE) {
    return;
  }

  configTime(GMT_OFFSET_SECONDS, DAYLIGHT_OFFSET_SECONDS, NTP_SERVER);
  Serial.print("Dang dong bo thoi gian NTP");
  unsigned long startedAt = millis();
  while (time(nullptr) < 1700000000 && millis() - startedAt < 10000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (time(nullptr) < 1700000000) {
    Serial.println("Chua dong bo duoc NTP, se gui bang API key tuong thich.");
  } else {
    Serial.println("Da dong bo NTP, san sang ky HMAC.");
  }
}

String hmacSha256(String message, const char* secret) {
  byte hmacResult[32];
  mbedtls_md_context_t ctx;
  const mbedtls_md_info_t* info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);

  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, info, 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char*)secret, strlen(secret));
  mbedtls_md_hmac_update(&ctx, (const unsigned char*)message.c_str(), message.length());
  mbedtls_md_hmac_finish(&ctx, hmacResult);
  mbedtls_md_free(&ctx);

  String hex = "";
  for (int i = 0; i < 32; i++) {
    if (hmacResult[i] < 16) {
      hex += "0";
    }
    hex += String(hmacResult[i], HEX);
  }
  return hex;
}
#endif

void setAlertOutput(bool active) {
  digitalWrite(ALERT_PIN, active ? HIGH : LOW);
}

bool isAlertCondition(float temperature, float humidity) {
  return temperature <= TEMP_LOW_ALERT_THRESHOLD ||
         temperature >= TEMP_HIGH_ALERT_THRESHOLD ||
         humidity <= HUMIDITY_LOW_ALERT_THRESHOLD ||
         humidity >= HUMIDITY_HIGH_ALERT_THRESHOLD;
}

void printAlertReason(float temperature, float humidity) {
  if (temperature <= TEMP_LOW_ALERT_THRESHOLD) {
    Serial.println("CANH BAO: Nhiet do qua thap.");
  }
  if (temperature >= TEMP_HIGH_ALERT_THRESHOLD) {
    Serial.println("CANH BAO: Nhiet do qua cao.");
  }
  if (humidity <= HUMIDITY_LOW_ALERT_THRESHOLD) {
    Serial.println("CANH BAO: Do am qua thap.");
  }
  if (humidity >= HUMIDITY_HIGH_ALERT_THRESHOLD) {
    Serial.println("CANH BAO: Do am qua cao.");
  }
}

String buildJsonBody(float temperature, float humidity) {
  String body = "{";
  body += "\"device_id\":\"";
  body += DEVICE_ID;
  body += "\",\"temperature\":";
  body += String(temperature, 1);
  body += ",\"humidity\":";
  body += String(humidity, 1);
  body += "}";
  return body;
}

void sendSensorData(float temperature, float humidity) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi mat ket noi, dang ket noi lai...");
    if (!connectWiFi()) {
      Serial.println("Bo qua lan gui HTTP nay vi chua co WiFi.");
      return;
    }
  }

  String jsonBody = buildJsonBody(temperature, humidity);

#if defined(ESP32)
  HTTPClient http;
  WiFiClientSecure secureClient;
  WiFiClient plainClient;

  if (String(SERVER_URL).startsWith("https://")) {
#if ALLOW_INSECURE_TLS
    secureClient.setInsecure();
#else
    if (strlen(SERVER_ROOT_CA) == 0) {
      Serial.println("HTTPS dang bat nhung chua cau hinh SERVER_ROOT_CA.");
      return;
    }
    secureClient.setCACert(SERVER_ROOT_CA);
#endif
    http.begin(secureClient, SERVER_URL);
  } else {
    http.begin(plainClient, SERVER_URL);
  }
#else
  WiFiClient client;
  HTTPClient http;
  http.begin(client, SERVER_URL);
#endif

  http.addHeader("Content-Type", "application/json");

#if defined(ESP32)
  if (ENABLE_HMAC_SIGNATURE && time(nullptr) >= 1700000000) {
    String timestamp = String((long)time(nullptr));
    String signaturePayload = String(DEVICE_ID) + timestamp + jsonBody;
    String signature = hmacSha256(signaturePayload, DEVICE_SECRET);
    http.addHeader("X-Device-Id", DEVICE_ID);
    http.addHeader("X-Timestamp", timestamp);
    http.addHeader("X-Signature", signature);
  } else {
    http.addHeader("X-API-Key", DEVICE_API_KEY);
  }
#else
  http.addHeader("X-API-Key", DEVICE_API_KEY);
#endif

  int httpCode = http.POST(jsonBody);
  String response = http.getString();

  if (httpCode > 0) {
    Serial.print("HTTP ");
    Serial.print(httpCode);
    Serial.print(" - ");
    Serial.println(response);
  } else {
    Serial.print("Gui du lieu that bai. Loi: ");
    Serial.println(http.errorToString(httpCode));
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(ALERT_PIN, OUTPUT);
  setAlertOutput(false);

  dht.begin();
  connectWiFi();
#if defined(ESP32)
  syncTimeForSignature();
#endif
}

void loop() {
  unsigned long now = millis();
  if (now - lastSendTime < SEND_INTERVAL_MS) {
    return;
  }
  lastSendTime = now;

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Khong doc duoc du lieu tu cam bien DHT.");
    return;
  }

  Serial.print("Nhiet do: ");
  Serial.print(temperature);
  Serial.print(" C | Do am: ");
  Serial.print(humidity);
  Serial.println(" %");

  bool isDanger = isAlertCondition(temperature, humidity);
  setAlertOutput(isDanger);
  if (isDanger) {
    printAlertReason(temperature, humidity);
  }

  sendSensorData(temperature, humidity);
}
