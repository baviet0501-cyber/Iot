#ifndef CONFIG_EXAMPLE_H
#define CONFIG_EXAMPLE_H

/*
  Copy file nay thanh config.h va dien thong tin that.
  Khong commit config.h len GitHub neu co WiFi/API key rieng.
*/

#include <DHT.h>

// Cau hinh WiFi
const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Dia chi server Flask.
// Neu chay Flask tren laptop: python backend/app.py
// Dung IP LAN cua laptop, khong dung 127.0.0.1 tren ESP.
const char* SERVER_URL = "http://192.168.1.10:5000/api/sensor-data";

// Phai trung voi DEVICE_API_KEY va DEVICE_SECRET trong backend/.env
const char* DEVICE_API_KEY = "change-this-device-api-key";
const char* DEVICE_SECRET = "classroom-demo-device-secret";
#define ENABLE_HMAC_SIGNATURE 1

// Demo co the de 1. Khi dung HTTPS that, doi thanh 0 va dien CA certificate.
#define ALLOW_INSECURE_TLS 1
#define SERVER_ROOT_CA ""

// Can co Internet de dong bo thoi gian khi ky HMAC.
const char* NTP_SERVER = "pool.ntp.org";
const long GMT_OFFSET_SECONDS = 0;
const int DAYLIGHT_OFFSET_SECONDS = 0;

// Thong tin thiet bi
const char* DEVICE_ID = "CLASSROOM_01";

// Cau hinh cam bien va canh bao
#define DHT_PIN 4
#define DHT_TYPE DHT11
#define ALERT_PIN 2

const unsigned long SEND_INTERVAL_MS = 5000;
const float TEMP_LOW_ALERT_THRESHOLD = 10.0;
const float TEMP_HIGH_ALERT_THRESHOLD = 35.0;
const float HUMIDITY_LOW_ALERT_THRESHOLD = 30.0;
const float HUMIDITY_HIGH_ALERT_THRESHOLD = 85.0;

#endif
