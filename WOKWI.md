# Mo Phong Wokwi - He Thong Giam Sat Nhiet Do Va Do Am Phong Hoc

Huong dan chay ESP32 ao tren Wokwi, gui du lieu ve Flask backend chay tren may tinh qua ngrok.

## Cau Truc File

```
firmware/wokwi/
  sketch.ino          # Firmware ESP32 cho Wokwi
  config_wokwi.h      # Cau hinh WiFi, server, cam bien
  diagram.json        # So do mach (ESP32 + DHT22 + LED)
  libraries.txt       # Thu vien can thiet
```

## Yeu Cau

- Python 3.x da cai
- Flask backend chay duoc (da cai dependencies trong `backend/.venv`)
- ngrok da cai (https://ngrok.com/download)

## Buoc Thuc Hien

### 1. Khoi Dong Backend Flask

```powershell
cd backend
.\.venv\Scripts\activate
python app.py
```

Hoac dung script tu dong:

```powershell
.\start-wokwi.ps1
```

### 2. Khoi Dong ngrok

Mo PowerShell moi, chay:

```powershell
ngrok http 5000
```

Copy URL tuong duong `https://xxxx.ngrok-free.dev`

### 3. Cap Nhat Config

Trong `firmware/wokwi/config_wokwi.h`, thay `SERVER_URL`:

```cpp
const char* SERVER_URL = "https://XXXX.ngrok-free.dev/api/sensor-data";
```

**Luu y:** Moi lan restart ngrok se co URL moi. Can cap nhat lai `config_wokwi.h`.

### 4. Cau Hinh Wokwi

1. Mo https://wokwi.com -> **New Project** -> chon **ESP32**
2. Copy 4 file vao Wokwi project:
   - `firmware/wokwi/sketch.ino` -> `sketch.ino`
   - `firmware/wokwi/config_wokwi.h` -> `config_wokwi.h`
   - `firmware/wokwi/diagram.json` -> `diagram.json`
   - `firmware/wokwi/libraries.txt` -> `libraries.txt`
3. **Luu y:** Khong can F1 -> Enable Private Gateway (dung Public Gateway mien phi)

### 5. Chay Mo Phong

1. Bam **Start Simulation** tren Wokwi
2. Mo Serial Monitor de kiem tra:
   - Ket noi WiFi thanh cong
   - Doc gia tri DHT22 (nhiet do, do am)
   - GUI POST thanh cong (HTTP 201)
3. Mo dashboard tai `http://127.0.0.1:5000/dashboard`
4. Du lieu cap nhat moi 5 giay

## Kiem Tra Tinh Nang

| Tinh Nang | Cach Test |
|-----------|-----------|
| Hien thi nhiet do/do am | Xem metric cards tren dashboard |
| Bieu do thoi gian thuc | Xem Chart.js line chart |
| Canh bao nhiet do | Keo thanh nhiet do > 35C trong Wokwi DHT22 |
| Canh bao do am | Keo thanh do am > 80% trong Wokwi DHT22 |
| Trang thai Online/Offline | Dung simulation > 30 giay |
| Bao mat API key | Doi DEVICE_API_KEY sai, kiem tra log loi 401 |

## Troubleshooting

| Van De | Giai Phap |
|--------|-----------|
| HTTP 403/401 | Kiem tra `DEVICE_API_KEY` khop voi `backend/.env` |
| HTTP 0 / Khong gui duoc | Kiem tra ngrok dang chay, copy URL moi vao config |
| Dashboard khong cap nhat | Kiem tra Flask backend dang chay port 5000 |
| ngrok URL thay doi | Restart ngrok -> cap nhat lai `config_wokwi.h` |
| Wokwi loi compile | Dam bao copy day du 4 file,kiem tra ten file dung |

## Chuyen Sang Thiet Bi That

Khi co ESP32 that, dung lai `firmware/esp_sensor.ino` va copy `firmware/config_example.h` thanh `firmware/config.h`, sau do cau hinh:

- `WIFI_SSID` / `WIFI_PASSWORD` - WiFi cua ban
- `SERVER_URL` - Dia chi IP local cua Flask (vi du: `http://192.168.1.100:5000/api/sensor-data`)
- `DEVICE_API_KEY` - API key tu `backend/.env`
- `DEVICE_ID` - Ma thiet bi

Backend khong can doi vi thiet bi ao va thiet bi that gui cung JSON schema.
