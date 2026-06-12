#ifndef CONFIG_WOKWI_EXAMPLE_H
#define CONFIG_WOKWI_EXAMPLE_H

/*
  Cau hinh mau de chay ESP32 tren Wokwi.

  Neu backend Flask chay tren may local:
  - Cai Wokwi Private IoT Gateway.
  - Dung host.wokwi.internal de ESP32 ao goi ve may tinh.
  - Hoac thay SERVER_URL bang URL public tam thoi tu ngrok/cloudflared.
*/

#include <DHT.h>

const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

const char* SERVER_URL = "http://host.wokwi.internal:5000/api/sensor-data";
const char* DEVICE_API_KEY = "change-this-device-api-key";
const char* DEVICE_SECRET = "classroom-demo-device-secret";
#define ENABLE_HMAC_SIGNATURE 1

// Wokwi demo dung HTTP local nen gia tri nay khong anh huong.
#define ALLOW_INSECURE_TLS 1
#define SERVER_ROOT_CA ""

const char* NTP_SERVER = "pool.ntp.org";
const long GMT_OFFSET_SECONDS = 0;
const int DAYLIGHT_OFFSET_SECONDS = 0;

const char* DEVICE_ID = "CLASSROOM_01";

#define DHT_PIN 4
#define DHT_TYPE DHT22
#define ALERT_PIN 2

const unsigned long SEND_INTERVAL_MS = 5000;
const float TEMP_LOW_ALERT_THRESHOLD = 10.0;
const float TEMP_HIGH_ALERT_THRESHOLD = 35.0;
const float HUMIDITY_LOW_ALERT_THRESHOLD = 30.0;
const float HUMIDITY_HIGH_ALERT_THRESHOLD = 85.0;

#endif
