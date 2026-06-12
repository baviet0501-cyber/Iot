# Hệ Thống Giám Sát Nhiệt Độ Và Độ Ẩm Phòng Học Có Bảo Mật Thiết Bị IoT

Project cá nhân môn **IoT Và An Toàn**. Hệ thống dùng ESP32 hoặc ESP8266 đọc nhiệt độ, độ ẩm từ cảm biến DHT11/DHT22, gửi dữ liệu lên backend Flask, lưu vào SQLite và hiển thị trên dashboard có đăng nhập.

Điểm nhấn an toàn thông tin của project là thiết bị IoT được xác thực bằng HMAC-SHA256, có chống replay attack bằng timestamp, dashboard có đăng nhập, mật khẩu được hash, có CSRF token, rate limit, security headers và nhật ký an toàn.

## 1. Kiến Trúc Hệ Thống

```text
DHT11/DHT22 -> ESP32/ESP8266 -> HTTP POST + HMAC -> Flask API -> SQLite
                                                       |
                                                       v
                                               Web Dashboard
```

- ESP đọc cảm biến mỗi 5 giây.
- Nếu nhiệt độ hoặc độ ẩm thay đổi, backend lưu ngay một dòng mới.
- Nếu cả hai thông số giữ nguyên, backend không tích trữ dữ liệu lặp mỗi 5 giây mà chỉ thêm một mốc lịch sử sau mỗi 1 phút.
- Thiết bị vẫn được xem là online nếu ESP vẫn gửi dữ liệu đều, kể cả khi backend skip lưu dòng trùng.
- Nếu quá 30 giây không có dữ liệu mới từ thiết bị thì dashboard hiển thị offline.

## 2. Linh Kiện Cần Dùng

- ESP32 DevKit hoặc ESP8266/NodeMCU.
- Cảm biến DHT11 hoặc DHT22.
- LED hoặc buzzer để cảnh báo.
- Điện trở 220 ohm nếu dùng LED.
- Breadboard và dây jumper.
- Laptop chạy Flask backend.

Project có sẵn cấu hình Wokwi để mô phỏng linh kiện, nên có thể làm báo cáo mà không cần phần cứng thật.

## 3. Sơ Đồ Kết Nối Chân

Mặc định project dùng ESP32 và cảm biến nối như sau:

| Linh kiện | Chân ESP32 |
| --- | --- |
| DHT VCC | 3V3 |
| DHT GND | GND |
| DHT DATA | GPIO 4 |
| LED anode | GPIO 2 qua điện trở 220 ohm |
| LED cathode | GND |

Ngưỡng cảnh báo:

| Thông số | Quá thấp | An toàn | Cảnh báo nhẹ | Quá cao |
| --- | --- | --- | --- | --- |
| Nhiệt độ | `< 10°C` | `10°C..26°C` | `26°C..35°C` | `> 35°C` |
| Độ ẩm | `< 30%` | `30%..70%` | `70%..85%` | `> 85%` |

LED/buzzer bật khi nhiệt độ `<10°C` hoặc `>35°C`, hoặc độ ẩm `<30%` hoặc `>85%`.

## 4. Cấu Trúc Thư Mục

```text
.
├── backend/
│   ├── app.py
│   ├── models.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── templates/
│   └── static/
├── firmware/
│   ├── esp_sensor.ino
│   ├── config_example.h
│   ├── config_wokwi_example.h
│   └── wokwi/
│       ├── wokwi.toml
│       ├── diagram.json
│       ├── config_wokwi.h
│       ├── sketch.ino
│       └── build/
├── wokwi.toml
└── README.md
```

File cấu hình thật như `backend/.env`, `firmware/config.h` và `firmware/wokwi/config_wokwi.h` không nên đưa lên GitHub.

## 5. Chạy Backend Flask Trên Windows

Mở PowerShell tại thư mục project:

```powershell
cd "E:\Kỳ 2 năm 4\IoT"
```

Lần đầu cài môi trường:

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\activate
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
python backend\app.py
```

Các lần sau chạy nhanh bằng đúng lệnh:

```powershell
.\backend\.venv\Scripts\activate; python backend\app.py
```

Mở trình duyệt:

```text
http://127.0.0.1:5000
```

Tài khoản demo mặc định:

```text
Username: admin
Password: admin123
```

Nên đổi mật khẩu ngay trên dashboard bằng menu tài khoản ở góc phải.

## 6. Cấu Hình Backend `.env`

Tạo file `backend/.env` từ `backend/.env.example`:

```env
SECRET_KEY=change-this-secret-key
DEVICE_API_KEY=change-this-device-api-key
DEVICE_SECRET=classroom-demo-device-secret
DEFAULT_DEVICE_ID=CLASSROOM_01
DEFAULT_DEVICE_NAME=Phòng học 01
DATABASE_URL=sqlite:///iot_classroom.db
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
SESSION_COOKIE_SECURE=false
DEVICE_CLOCK_SKEW_SECONDS=60
DEVICE_REPLAY_CACHE_SECONDS=120
ALLOW_LEGACY_API_KEY=true
LOGIN_MAX_ATTEMPTS=5
LOGIN_LOCK_SECONDS=60
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
```

Ý nghĩa các biến quan trọng:

- `SECRET_KEY`: khóa bí mật cho session Flask.
- `DEVICE_API_KEY`: API key tương thích cũ.
- `DEVICE_SECRET`: secret dùng để tạo chữ ký HMAC-SHA256 cho thiết bị.
- `DATABASE_URL`: đường dẫn SQLite.
- `LOGIN_LOCK_SECONDS`: thời gian khóa tạm khi đăng nhập sai nhiều lần, tối đa 60 giây trong code.
- `DEVICE_CLOCK_SKEW_SECONDS`: độ lệch timestamp cho phép để chống replay attack.
- `DEVICE_REPLAY_CACHE_SECONDS`: thời gian lưu chữ ký HMAC đã nhận để chặn gửi lại cùng một request.
- `ALLOW_LEGACY_API_KEY`: bật/tắt chế độ API key tương thích. Khi báo cáo bảo mật nghiêm túc có thể đặt `false`.
- `FLASK_DEBUG`: nên để `false` khi mở server qua LAN, tunnel hoặc mạng lớp.

## 7. Dashboard

Sau khi đăng nhập, dashboard hiển thị:

- Nhiệt độ hiện tại.
- Độ ẩm hiện tại.
- Trạng thái thiết bị online/offline.
- Cảnh báo khi nhiệt độ quá thấp, quá cao, độ ẩm quá thấp hoặc quá cao.
- Biểu đồ lịch sử bằng Chart.js.
- Bảng dữ liệu gần nhất.

Các trang chính:

```text
/login
/dashboard
/security-logs
/change-password
```

Trang `/security-logs` tự kiểm tra log mới sau mỗi 5 giây và cập nhật bảng khi có sự kiện mới phù hợp bộ lọc hiện tại.

## 8. API Thiết Bị IoT

### `POST /api/sensor-data`

Body JSON:

```json
{
  "device_id": "CLASSROOM_01",
  "temperature": 29.5,
  "humidity": 70
}
```

Validate dữ liệu:

- `device_id` không được rỗng.
- `temperature` phải là số trong khoảng `-40..100`.
- `humidity` phải là số trong khoảng `0..100`.

### Xác thực HMAC-SHA256

Backend ưu tiên xác thực bằng 3 header:

```text
X-Device-Id: CLASSROOM_01
X-Timestamp: <unix_timestamp>
X-Signature: <hmac_sha256_hex>
```

Chuỗi dùng để ký:

```text
device_id + timestamp + raw_json_body
```

Backend kiểm tra:

- Thiết bị tồn tại trong bảng `devices`.
- Thiết bị đang active.
- Timestamp không lệch quá `DEVICE_CLOCK_SKEW_SECONDS`.
- Chữ ký HMAC đúng với `DEVICE_SECRET`.
- Chữ ký HMAC chưa từng được dùng trong `DEVICE_REPLAY_CACHE_SECONDS` gần nhất.
- `device_id` trong body khớp với `X-Device-Id`.

Nếu sai chữ ký, timestamp quá lệch hoặc dùng lại cùng request đã ký, API trả `401 Unauthorized`.

### Chế độ tương thích API key

Project vẫn hỗ trợ header cũ:

```text
X-API-Key: change-this-device-api-key
```

Chế độ này chỉ nên dùng để test nhanh hoặc khi thiết bị chưa đồng bộ được thời gian NTP. Có thể tắt bằng `ALLOW_LEGACY_API_KEY=false`; khi báo cáo an toàn thông tin, nên trình bày HMAC là cơ chế chính.

## 9. Test API Bằng PowerShell

Test HMAC hợp lệ:

```powershell
.\backend\.venv\Scripts\python.exe -c "import time,hmac,hashlib,urllib.request; body='{\"device_id\":\"CLASSROOM_01\",\"temperature\":29.5,\"humidity\":70}'; ts=str(int(time.time())); secret='classroom-demo-device-secret'; sig=hmac.new(secret.encode(), ('CLASSROOM_01'+ts+body).encode(), hashlib.sha256).hexdigest(); req=urllib.request.Request('http://127.0.0.1:5000/api/sensor-data', data=body.encode(), headers={'Content-Type':'application/json','X-Device-Id':'CLASSROOM_01','X-Timestamp':ts,'X-Signature':sig}, method='POST'); res=urllib.request.urlopen(req); print(res.status, res.read().decode())"
```

Test API key tương thích:

```powershell
curl -X POST http://127.0.0.1:5000/api/sensor-data `
  -H "Content-Type: application/json" `
  -H "X-API-Key: change-this-device-api-key" `
  -d "{\"device_id\":\"CLASSROOM_01\",\"temperature\":29.5,\"humidity\":70}"
```

Test dữ liệu sai:

```powershell
curl -X POST http://127.0.0.1:5000/api/sensor-data `
  -H "Content-Type: application/json" `
  -H "X-API-Key: change-this-device-api-key" `
  -d "{\"device_id\":\"CLASSROOM_01\",\"temperature\":120,\"humidity\":70}"
```

Kết quả mong đợi: HTTP `400 Bad Request`.

## 10. Chạy Mô Phỏng Wokwi

Backend phải chạy trước:

```powershell
.\backend\.venv\Scripts\activate; python backend\app.py
```

Wokwi VS Code dùng file cấu hình:

```text
wokwi.toml
```

File này trỏ tới firmware đã build:

```text
firmware/wokwi/build/wokwi_sketch.ino.bin
firmware/wokwi/build/wokwi_sketch.ino.elf
```

Cấu hình Wokwi chính:

```text
firmware/wokwi/config_wokwi.h
```

Các giá trị cần khớp với backend:

```cpp
const char* SERVER_URL = "http://host.wokwi.internal:5000/api/sensor-data";
const char* DEVICE_API_KEY = "change-this-device-api-key";
const char* DEVICE_SECRET = "classroom-demo-device-secret";
const char* DEVICE_ID = "CLASSROOM_01";
```

Nếu dùng Wokwi trên trình duyệt hoặc môi trường không gọi được `host.wokwi.internal`, có thể thay `SERVER_URL` bằng URL public tạm thời từ Cloudflare Tunnel, ngrok hoặc dịch vụ tương tự.

### Khi Wokwi báo `firmware binary build/sketch.ino.bin not found`

Nguyên nhân thường gặp:

- `wokwi.toml` đang trỏ sai tên file `.bin`.
- Firmware chưa được build.
- Bạn đang mở sai thư mục Wokwi.

Trong project này, Wokwi đang trỏ tới:

```text
firmware/wokwi/build/wokwi_sketch.ino.bin
firmware/wokwi/build/wokwi_sketch.ino.elf
```

Nếu đã sửa code trong `firmware/wokwi/sketch.ino`, cần build lại để Wokwi dùng binary mới. Nếu không build lại, Wokwi vẫn chạy binary cũ và LED/cảnh báo có thể không đúng với code mới.

## 11. Nạp Code ESP32 Thật

1. Mở Arduino IDE.
2. Cài board ESP32 hoặc ESP8266.
3. Cài thư viện `DHT sensor library` và `Adafruit Unified Sensor`.
4. Copy `firmware/config_example.h` thành `firmware/config.h`.
5. Điền Wi-Fi, `SERVER_URL`, `DEVICE_API_KEY`, `DEVICE_SECRET`.
6. Mở `firmware/esp_sensor.ino`.
7. Chọn đúng board và cổng COM.
8. Upload code.
9. Mở Serial Monitor baud `115200`.

Lưu ý: ESP thật không gọi được `127.0.0.1` của laptop. Hãy dùng IP LAN của laptop, ví dụ:

```cpp
const char* SERVER_URL = "http://192.168.1.10:5000/api/sensor-data";
```

## 12. Tính Năng IoT

- Đọc cảm biến DHT mỗi 5 giây.
- Gửi dữ liệu lên server bằng HTTP POST JSON.
- LED/buzzer cảnh báo tại thiết bị.
- Dashboard cập nhật trạng thái online/offline.
- Biểu đồ lịch sử nhiệt độ và độ ẩm.
- Bảng dữ liệu gần nhất.
- Tối ưu lưu dữ liệu để tránh lặp một đống hàng khi thông số giữ nguyên.

## 13. Tính Năng An Toàn Thông Tin

- Xác thực thiết bị bằng HMAC-SHA256.
- Chống replay attack bằng `X-Timestamp` và cache chữ ký HMAC đã dùng.
- Kiểm tra `device_id` trong header và body.
- Từ chối thiết bị không tồn tại hoặc bị vô hiệu hóa.
- Hỗ trợ API key cũ ở chế độ tương thích, có thể tắt bằng `ALLOW_LEGACY_API_KEY=false`.
- Dashboard yêu cầu đăng nhập.
- Mật khẩu hash bằng `werkzeug.security`, không lưu plain text.
- CSRF token cho đăng nhập, đăng xuất và đổi mật khẩu.
- Khóa đăng nhập tạm thời khi sai quá nhiều lần.
- Rate limit cho login và API sensor.
- Session cookie bật `HttpOnly`, `SameSite=Lax`, có tùy chọn `Secure`.
- Security headers: CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`.
- Audit log lưu các sự kiện bảo mật vào SQLite.
- `.env` và file cấu hình thật được đưa vào `.gitignore`.

## 14. Nhật Ký An Toàn

Truy cập:

```text
http://127.0.0.1:5000/security-logs
```

Các sự kiện tiêu biểu:

- `login_success`
- `login_failed`
- `login_locked`
- `csrf_failed`
- `invalid_signature`
- `replay_detected`
- `invalid_api_key`
- `invalid_payload`
- `threshold_warning`
- `legacy_api_key_used`
- `password_changed`

Thời gian trên trang nhật ký được hiển thị theo giờ Việt Nam UTC+7.

## 15. Troubleshooting

### Dashboard không có dữ liệu

- Kiểm tra Flask đang chạy ở `http://127.0.0.1:5000`.
- Kiểm tra ESP/Wokwi gửi đúng `SERVER_URL`.
- Kiểm tra `DEVICE_SECRET` hoặc `DEVICE_API_KEY` trùng với `backend/.env`.
- Xem log trong terminal Flask hoặc trang `/security-logs`.

### Thiết bị offline dù ESP vẫn chạy

- Nếu ESP không gửi được HTTP, dashboard sẽ offline sau 30 giây.
- Với Wokwi, kiểm tra `host.wokwi.internal` và Wokwi Private IoT Gateway nếu môi trường yêu cầu.
- Nếu dùng HMAC, ESP cần đồng bộ NTP để timestamp hợp lệ.

### Sai chữ ký HMAC

- `DEVICE_SECRET` trong firmware phải giống `DEVICE_SECRET` trong backend.
- `DEVICE_ID` phải là `CLASSROOM_01` hoặc đúng với thiết bị trong database.
- Body JSON ký phải giống hệt body gửi đi.
- Timestamp không được lệch quá 60 giây.
- Nếu gửi lại y nguyên một request HMAC đã được server nhận, backend sẽ ghi `replay_detected` và trả `401`.

### LED Wokwi không sáng đúng ngưỡng

- Kiểm tra `TEMP_LOW_ALERT_THRESHOLD`, `TEMP_HIGH_ALERT_THRESHOLD`, `HUMIDITY_LOW_ALERT_THRESHOLD`, `HUMIDITY_HIGH_ALERT_THRESHOLD`.
- Build lại Wokwi sau khi sửa code.
- Kiểm tra LED nối đúng GPIO 2 và GND trong `diagram.json`.

### Dữ liệu bị lặp nhiều hàng

Backend đã có logic nén dữ liệu lặp:

- Thay đổi nhiệt độ hoặc độ ẩm: lưu ngay.
- Giữ nguyên cả hai thông số: chỉ thêm một dòng mới sau 60 giây.
- Vẫn cập nhật `last_seen` để trạng thái thiết bị online.

### Font tiếng Việt bị lỗi

- Các file HTML, JS, Python và README dùng UTF-8.
- Nếu PowerShell hiển thị lỗi dấu, chạy:

```powershell
chcp 65001
```

## 16. Chuẩn Bị Nộp Bài

- Có thể chạy `.\prepare-submission.ps1` để tạo file `iot-classroom-submission.zip` sạch.
- File nén sạch sẽ không bao gồm `.env`, database, virtualenv, build Wokwi, tools và log.

## 17. Hướng Phát Triển

- Bật HTTPS thật bằng Cloudflare Tunnel, Nginx hoặc reverse proxy.
- Quản lý nhiều thiết bị và nhiều phòng học.
- Thêm vai trò người dùng.
- Export CSV/PDF cho báo cáo.
- Gửi cảnh báo Telegram hoặc email khi vượt ngưỡng.
- Thêm biểu đồ thống kê theo ngày, tuần, tháng.
