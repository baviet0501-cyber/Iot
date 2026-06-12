# Huong dan thuyet trinh 7-10 phut

## Kich ban noi theo slide

1. Slide 1 - Gioi thieu de tai trong 20 giay: he thong giam sat nhiet do, do am phong hoc va co lop bao mat cho thiet bi IoT.
2. Slide 2 - Neu van de trong 50 giay: do moi truong tu dong la phan IoT; cau hoi an toan la lam sao biet du lieu den tu thiet bi that, khong bi gia mao.
3. Slide 3 - Giai thich kien truc trong 1 phut: `DHT -> ESP32 -> HTTP POST JSON + HMAC -> Flask -> SQLite -> Dashboard`. Nhan manh doan ESP32 den Flask la diem bao mat quan trong.
4. Slide 4-5 - Noi ve linh kien va cong nghe trong 1 phut: ESP32/Wokwi, DHT22, LED GPIO2, Flask, SQLite, HTML/CSS/JS va Chart.js.
5. Slide 6 - Demo chuc nang trong 1 phut: gia tri hien tai, bieu do, bang lich su, trang thai online/offline dua tren `last_seen`, canh bao vuot nguong.
6. Slide 7-8 - Noi sau ve bao mat trong 1.5-2 phut: HMAC ky `device_id + timestamp + raw_json_body`, server tinh lai chu ky, so sanh bang `compare_digest`, kiem tra timestamp va cache chu ky da dung de chan replay.
7. Slide 9-13 - Demo live trong 1.5 phut: mo dashboard, chay Wokwi, doi nhiet do/do am, xem LED/canh bao, mo security logs.
8. Slide 14 - Ket luan trong 50 giay: da hoan thanh luong IoT tu cam bien den dashboard va bo sung dang nhap, HMAC, CSRF, rate limit, audit log; huong phat trien la HTTPS that, MQTT + TLS, nhieu thiet bi va canh bao Telegram/email.

## Thu tu demo de it loi

1. Chay Flask truoc, dang nhap dashboard va de san trang security logs o tab khac.
2. Chay Wokwi, mo Serial Monitor de thay HTTP 201/200.
3. Thay doi nhiet do tren DHT22 Wokwi len tren `35°C` hoac do am tren `85%` de kich hoat canh bao.
4. Quay lai dashboard xem gia tri, bieu do, bang lich su va trang thai online.
5. Tao mot request sai API key de security logs co su kien `invalid_api_key`.

## Cau tra loi ngan cho phan hoi dap

- Vi sao dung HMAC? Vi server khong chi tin `device_id`; request phai co chu ky tao tu secret chung, timestamp va body goc.
- Vi sao can timestamp? De request bi bat lai qua lau se bi tu choi.
- Replay trong 60 giay da xu ly chua? Da them cache chu ky da chap nhan, nen cung mot request dung lai se bi ghi log `replay_detected`.
- API key fallback co an toan khong? Khong bang HMAC; day la che do tuong thich/demo va co the tat bang `ALLOW_LEGACY_API_KEY=false`.
- Vi sao dung SQLite? Du cho demo mon hoc, gon nhe, de xem log va lich su; khi mo rong co the chuyen PostgreSQL/MySQL.
- Neu trien khai that can lam gi? Tat debug, doi secret/password, bat HTTPS/MQTT TLS, cau hinh cookie secure, quan ly nhieu thiet bi va luu nonce/replay cache ben vung hon.
