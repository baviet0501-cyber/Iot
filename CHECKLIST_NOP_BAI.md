# Checklist nop bai va demo

## Truoc khi nop file zip

- Khong nen nen ca thu muc project hien tai vi co the kem file bi mat hoac file nang.
- Khong nop cac file/thu muc: `backend/.env`, `backend/*.db`, `.venv/`, `backend/.venv/`, `__pycache__/`, `firmware/wokwi/build/`, `firmware/wokwi/wokwi_sketch/build/`, `tools/`, `server.out.log`, `server.err.log`.
- Nen nop source chinh: `backend/app.py`, `backend/models.py`, `backend/requirements.txt`, `backend/templates/`, `backend/static/`, `firmware/esp_sensor.ino`, cac file example config, `firmware/wokwi/diagram.json`, `firmware/wokwi/sketch.ino`, `wokwi.toml`, `README.md`, `WOKWI.md`, slide PowerPoint.
- Neu can gui config, chi gui `.env.example` va `config_example.h`, khong gui file chua Wi-Fi/password/secret that.

## Truoc khi demo

- Chay backend: `.ackend\.venv\Scripts\activate; python backend\app.py`.
- Mo dashboard: `http://127.0.0.1:5000`.
- Kiem tra `firmware/wokwi/config_wokwi.h` dung `SERVER_URL=http://host.wokwi.internal:5000/api/sensor-data`.
- Neu muon noi ve HMAC nghiem tuc, dat `ALLOW_LEGACY_API_KEY=false` trong `backend/.env` va dam bao ESP32/Wokwi da dong bo NTP.
- Neu demo Wokwi de on dinh, co the de `ALLOW_LEGACY_API_KEY=true` lam fallback khi NTP chua san sang.

## Diem nen noi ro khi bi hoi bao mat

- HMAC-SHA256 dung de xac thuc request den tu thiet bi co chung secret.
- `X-Timestamp` gioi han request cu; backend da them cache chu ky de chan dung lai cung mot request trong cua so replay.
- API key fallback la che do tuong thich/demo, co the tat bang `ALLOW_LEGACY_API_KEY=false`.
- HTTPS demo co tuy chon insecure TLS; khi trien khai that can CA certificate hoac certificate pinning.
- `FLASK_DEBUG=false` nen dung khi mo server qua LAN/tunnel.
